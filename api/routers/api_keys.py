"""
API Gateway - API Key Router

提供 API Key 管理 API 接口:
- API Key CRUD 操作
- API Key 验证
- 权限检查

使用FastAPI实现RESTful API接口
"""

from fastapi import APIRouter, HTTPException, Query, Header, Body, Depends
from typing import Dict, List, Optional
from datetime import datetime
from pydantic import BaseModel
import logging


class CreateApiKeyRequest(BaseModel):
    """创建 API Key 请求"""
    name: str
    permissions: List[str] = ["read"]
    description: Optional[str] = None
    expires_days: Optional[int] = None
    auto_generate: bool = True


class UpdateApiKeyRequest(BaseModel):
    """更新 API Key 请求"""
    name: Optional[str] = None
    permissions: Optional[List[str]] = None
    is_active: Optional[bool] = None
    description: Optional[str] = None
    expires_days: Optional[int] = None

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/api/v1/api-keys",
    tags=["api-keys"]
)


# ============================================================================
# API Key CRUD接口
# ============================================================================

@router.get("/")
async def list_api_keys(
    user_id: Optional[str] = Query(None, description="过滤用户ID")
) -> Dict:
    """
    获取 API Key 列表

    Args:
        user_id: 可选，过滤指定用户的 API Keys

    Returns:
        Dict: API Key 列表
    """
    try:
        from ginkgo.data.containers import container

        service = container.api_key_service()
        result = service.list_api_keys(user_id=user_id)

        if result["success"]:
            return {
                "code": 0,
                "message": "success",
                "data": result["data"]["api_keys"]
            }
        else:
            raise HTTPException(status_code=400, detail=result["message"])

    except Exception as e:
        logger.error(f"Failed to list API keys: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/")
async def create_api_key(
    request: CreateApiKeyRequest
) -> Dict:
    """
    创建 API Key

    Args:
        request: 创建请求

    Returns:
        Dict: 创建的 API Key 信息（key_value 仅在创建时返回一次）
    """
    try:
        from ginkgo.data.containers import container

        service = container.api_key_service()
        result = service.create_api_key(
            name=request.name,
            permissions=request.permissions,
            description=request.description,
            expires_days=request.expires_days,
            auto_generate=request.auto_generate
        )

        if result["success"]:
            return {
                "code": 0,
                "message": "success",
                "data": result["data"]
            }
        else:
            raise HTTPException(status_code=400, detail=result["message"])

    except Exception as e:
        logger.error(f"Failed to create API key: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{uuid}")
async def get_api_key(uuid: str) -> Dict:
    """
    获取 API Key 详情

    Args:
        uuid: API Key UUID

    Returns:
        Dict: API Key 详情（不包含原始 key_value）
    """
    try:
        from ginkgo.data.containers import container

        service = container.api_key_service()
        result = service.get_api_key(uuid)

        if result["success"]:
            return {
                "code": 0,
                "message": "success",
                "data": result["data"]
            }
        else:
            raise HTTPException(status_code=404, detail=result["message"])

    except Exception as e:
        logger.error(f"Failed to get API key: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/{uuid}")
async def update_api_key(
    uuid: str,
    request: UpdateApiKeyRequest
) -> Dict:
    """
    更新 API Key

    Args:
        uuid: API Key UUID
        request: 更新请求

    Returns:
        Dict: 更新结果
    """
    try:
        from ginkgo.data.containers import container

        service = container.api_key_service()
        result = service.update_api_key(
            uuid=uuid,
            name=request.name,
            permissions=request.permissions,
            is_active=request.is_active,
            description=request.description,
            expires_days=request.expires_days
        )

        if result["success"]:
            return {
                "code": 0,
                "message": "success",
                "data": {"uuid": uuid}
            }
        else:
            raise HTTPException(status_code=400, detail=result["message"])

    except Exception as e:
        logger.error(f"Failed to update API key: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/{uuid}")
async def delete_api_key(uuid: str) -> Dict:
    """
    删除 API Key

    Args:
        uuid: API Key UUID

    Returns:
        Dict: 删除结果
    """
    try:
        from ginkgo.data.containers import container

        service = container.api_key_service()
        result = service.delete_api_key(uuid)

        if result["success"]:
            return {
                "code": 0,
                "message": "success",
                "data": {"uuid": uuid}
            }
        else:
            raise HTTPException(status_code=404, detail=result["message"])

    except Exception as e:
        logger.error(f"Failed to delete API key: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/verify")
async def verify_api_key(
    x_api_key: str = Header(..., description="API Key"),
    required_permission: Optional[str] = Query(None, description="需要的权限")
) -> Dict:
    """
    验证 API Key

    Args:
        x_api_key: API Key (从 Header 中获取)
        required_permission: 需要的权限 (read/trade/admin)

    Returns:
        Dict: 验证结果
    """
    try:
        from ginkgo.data.containers import container

        service = container.api_key_service()
        api_key = service.verify_api_key(x_api_key, required_permission)

        if api_key:
            # 更新最后使用时间
            from ginkgo.data.crud.api_key_crud import ApiKeyCRUD
            crud = ApiKeyCRUD()
            crud.update_last_used(api_key.uuid)

            return {
                "code": 0,
                "message": "success",
                "data": {
                    "uuid": api_key.uuid,
                    "name": api_key.name,
                    "key_prefix": api_key.key_prefix,
                    "permissions": api_key.permissions,
                    "account_uuid": api_key.account_uuid
                }
            }
        else:
            return {
                "code": 401,
                "message": "Invalid API Key or insufficient permissions",
                "data": None
            }

    except Exception as e:
        logger.error(f"Failed to verify API key: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/check-permission")
async def check_permission(
    x_api_key: str = Header(..., description="API Key"),
    permission: str = Query(..., description="需要检查的权限")
) -> Dict:
    """
    检查 API Key 是否有指定权限

    Args:
        x_api_key: API Key (从 Header 中获取)
        permission: 需要的权限 (read/trade/admin)

    Returns:
        Dict: 权限检查结果
    """
    try:
        from ginkgo.data.containers import container

        service = container.api_key_service()
        has_permission = service.check_permission(x_api_key, permission)

        return {
            "code": 0,
            "message": "success",
            "data": {
                "has_permission": has_permission,
                "permission": permission
            }
        }

    except Exception as e:
        logger.error(f"Failed to check permission: {e}")
        raise HTTPException(status_code=500, detail=str(e))


class RevealApiKeyRequest(BaseModel):
    """显示完整 API Key 请求"""
    password: str


@router.post("/{uuid}/reveal")
async def reveal_api_key(uuid: str) -> Dict:
    """
    获取完整的 API Key（需要登录）

    Args:
        uuid: API Key UUID

    Returns:
        Dict: 包含完整 API Key 的响应
    """
    try:
        from ginkgo.data.containers import container

        # 获取 API Key 详情（包含完整 key）
        service = container.api_key_service()
        result = service.reveal_api_key(uuid)

        if result.get("success"):
            return {
                "code": 0,
                "message": "success",
                "data": result["data"]
            }
        else:
            raise HTTPException(status_code=404, detail=result.get("message", "API Key 不存在"))

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to reveal API key: {e}")
        raise HTTPException(status_code=500, detail=str(e))
