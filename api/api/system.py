"""
系统状态和Worker管理API路由
"""

from fastapi import APIRouter
from typing import Dict, Any

from core.response import ok
from core.logging import logger

router = APIRouter()


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
        return ok(data={"status": "error", "version": "unknown", "error": str(e)})


@router.get("/workers")
async def get_workers():
    """获取所有Worker/组件状态"""
    try:
        svc = _get_system_service()
        return ok(data=svc.get_workers_status())
    except Exception as e:
        logger.error(f"Failed to get workers status: {e}")
        return ok(data={"data": [], "components": {}})
