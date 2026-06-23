"""
系统状态和Worker管理API路由
"""

from fastapi import APIRouter
from typing import Dict, Any

from core.config import settings
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
