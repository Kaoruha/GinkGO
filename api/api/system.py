"""
系统状态和Worker管理API路由
"""

from fastapi import APIRouter, HTTPException, Request
from typing import Dict, Any

from core.config import settings
from core.response import ok
from core.logging import logger
from api.settings import _require_admin  # #6175: 单一权威 admin 权限源，不在本模块重写

router = APIRouter()

# #5878 Worker Management 切片：前端期望的分类端点路径 → 后端 worker.type（system_service.py:107-153）
WORKER_TYPE_MAP: Dict[str, str] = {
    "backtest": "backtest_worker",
    "data": "data_worker",
    "execution": "execution_node",
    "scheduler": "scheduler",
    "timer": "task_timer",
}


def _get_system_service():
    from ginkgo.core.services.system_service import SystemService
    return SystemService()


@router.get("/status")
async def get_system_status():
    """获取系统整体状态"""
    try:
        svc = _get_system_service()
        return ok(data=svc.get_system_status())
    except Exception as e:
        logger.error(f"Failed to get system status: {e}")
        # #5481: 生产环境 error 字段不泄露内部异常细节；DEBUG 才附 str(e)
        _err = str(e) if settings.DEBUG else "internal error (see server logs)"
        return ok(data={"status": "error", "version": "unknown", "error": _err})


@router.get("/workers")
async def get_workers():
    """获取所有Worker/组件状态"""
    try:
        svc = _get_system_service()
        return ok(data=svc.get_workers_status())
    except Exception as e:
        logger.error(f"Failed to get workers status: {e}")
        return ok(data={"data": [], "components": {}})


@router.get("/workers/{worker_type}")
async def get_workers_by_type(worker_type: str):
    """#5878: 按类型获取 Worker 状态（前端 /workers/backtest|data|execution|scheduler|timer 分类端点）。"""
    target = WORKER_TYPE_MAP.get(worker_type)
    if target is None:
        raise HTTPException(
            status_code=404,
            detail=f"Unknown worker type: {worker_type}. Valid: {list(WORKER_TYPE_MAP)}",
        )
    try:
        svc = _get_system_service()
        result = svc.get_workers_status()
        workers = result.get("data", []) if isinstance(result, dict) else []
        filtered = [w for w in workers if w.get("type") == target]
        return ok(data={"type": target, "workers": filtered, "count": len(filtered)})
    except Exception as e:
        logger.error(f"Failed to get workers by type {worker_type}: {e}")
        return ok(data={"type": target, "workers": [], "count": 0})


@router.get("/workers/{worker_id}/tasks")
async def get_worker_tasks(worker_id: str):
    """Worker 管理页行内下钻：回测 Worker 活跃任务明细（心跳 task_uuids → MySQL）。"""
    try:
        svc = _get_system_service()
        return ok(data=svc.get_worker_tasks(worker_id))
    except Exception as e:
        logger.error(f"Failed to get worker tasks for {worker_id}: {e}")
        return ok(data={"worker_id": worker_id, "found": False, "tasks": []})


@router.get("/error-stats")
async def get_error_stats(req: Request):
    """#6785: 查询当前 API 进程累计的错误热点（管理员）。

    走 SystemService → GLOG.get_error_stats（分层 API→Service→GLOG，不直访 GLOG）。
    """
    _require_admin(req)
    svc = _get_system_service()
    return ok(data=svc.get_error_stats())


@router.post("/error-stats/reset")
async def reset_error_stats(req: Request):
    """#6785: 清零进程内错误统计（管理员），便于排障后观察新一轮错误分布。"""
    _require_admin(req)
    svc = _get_system_service()
    return ok(data=svc.reset_error_stats())


@router.get("/cleanup")
async def system_cleanup(
    dry_run: bool = True,
    include_backtests: bool = False,
    request: Request = None,
):
    """孤儿数据清理(管理员工具,2026-08-17)。

    聚合各域清理方法,Web 端入口(对齐 CLI `ginkgo cleanup`):
    - 映射: cleanup_orphaned_mappings(6 规则:pfm/engine/handler 双向)
    - 参数: cleanup_orphaned_params(mapping_id 悬空)
    - 孤儿回测(需 include_backtests=True): 引用断 portfolio 的任务 + CH 指向
      已删任务的流水(signal/order_record/position_record/analyzer_record/日志)
      ——量大且不可逆,默认不并入
    - 僵尸引擎: cleanup_stale_engines(dry_run 透传)

    dry_run=True 仅统计(默认);执行需 admin 权限 + 显式 dry_run=false。
    """
    _require_admin(request)
    from ginkgo.data.containers import container

    result: Dict[str, Any] = {"dry_run": dry_run, "domains": {}, "errors": []}

    try:
        ms = container.mapping_service()
        r = ms.cleanup_orphaned_mappings(dry_run=dry_run)
        result["domains"]["mappings"] = r.data if r.is_success() else {"error": r.error}
        if not r.is_success():
            result["errors"].append(f"mappings: {r.error}")
    except Exception as e:
        result["errors"].append(f"mappings: {e}")

    try:
        ps = container.param_service()
        r = ps.cleanup_orphaned_params(dry_run=dry_run)
        result["domains"]["params"] = r.data if r.is_success() else {"error": r.error}
        if not r.is_success():
            result["errors"].append(f"params: {r.error}")
    except Exception as e:
        result["errors"].append(f"params: {e}")

    try:
        es = container.engine_service()
        r = es.cleanup_stale_engines(is_live=None, dry_run=dry_run)
        result["domains"]["engines"] = r.data if r.is_success() else {"error": r.error}
        if not r.is_success():
            result["errors"].append(f"engines: {r.error}")
    except Exception as e:
        result["errors"].append(f"engines: {e}")

    if include_backtests:
        try:
            bts = container.backtest_task_service()
            r = bts.cleanup_orphan_backtests(dry_run=dry_run)
            result["domains"]["orphan_backtests"] = r.data if r.is_success() else {"error": r.error}
            if not r.is_success():
                result["errors"].append(f"orphan_backtests: {r.error}")
        except Exception as e:
            result["errors"].append(f"orphan_backtests: {e}")

    return ok(data=result, message=f"清理{'预览' if dry_run else '执行'}完成"
            + (f",{len(result['errors'])} 项出错" if result["errors"] else ""))
