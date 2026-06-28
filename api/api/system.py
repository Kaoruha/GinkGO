"""
系统状态和Worker管理API路由
"""

from fastapi import APIRouter, HTTPException
from typing import Dict, Any

from core.config import settings
from core.response import ok
from core.logging import logger

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
