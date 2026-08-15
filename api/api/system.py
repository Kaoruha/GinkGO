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
