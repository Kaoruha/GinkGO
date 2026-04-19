"""
Live Account 相关API路由

实盘账号管理接口，对应前端 web-ui/src/api/modules/live.ts
"""

from fastapi import APIRouter, Query, Request, status
from typing import Optional
from core.logging import logger
from core.response import ok
from core.exceptions import NotFoundError, ValidationError, BusinessError

from models.accounts import (
    LiveAccountSummary,
    LiveAccountDetail,
    CreateLiveAccountRequest,
    UpdateLiveAccountRequest,
    UpdateAccountStatusRequest,
    ValidateAccountResponse,
    BalanceResponse,
    PositionsResponse,
)

router = APIRouter()


def get_live_account_service():
    """获取LiveAccountService实例"""
    from ginkgo.data.containers import container
    return container.live_account_service()


def _get_user_id(request: Request) -> str:
    """从 request.state 获取 user_id"""
    try:
        return request.state.user_id
    except AttributeError:
        return "default_user"


@router.get("/")
async def list_accounts(
    request: Request,
    exchange: Optional[str] = Query(None, description="过滤交易所"),
    environment: Optional[str] = Query(None, description="过滤环境"),
    status_filter: Optional[str] = Query(None, alias="status", description="过滤状态"),
):
    """获取实盘账号列表"""
    try:
        service = get_live_account_service()
        user_id = _get_user_id(request)

        result = service.get_user_accounts(
            user_id=user_id,
            page=1,
            page_size=100,
            exchange=exchange,
            environment=environment,
            status=status_filter,
        )

        if not result["success"]:
            raise BusinessError(result.get("message", "Failed to list accounts"))

        return ok(data=result["data"], message="Accounts retrieved successfully")
    except BusinessError:
        raise
    except Exception as e:
        logger.error(f"Error listing accounts: {e}")
        raise BusinessError(f"Error listing accounts: {e}")


@router.post("/", status_code=status.HTTP_201_CREATED)
async def create_account(request: Request, data: CreateLiveAccountRequest):
    """创建实盘账号"""
    try:
        service = get_live_account_service()
        user_id = _get_user_id(request)

        result = service.create_account(
            user_id=user_id,
            exchange=data.exchange.value,
            name=data.name,
            api_key=data.api_key,
            api_secret=data.api_secret,
            passphrase=data.passphrase,
            environment=data.environment.value,
            description=data.description,
            auto_validate=data.auto_validate,
        )

        if not result["success"]:
            raise BusinessError(result.get("message", "Failed to create account"))

        return ok(data=result["data"], message="Account created successfully")
    except BusinessError:
        raise
    except Exception as e:
        logger.error(f"Error creating account: {e}")
        raise BusinessError(f"Error creating account: {e}")


@router.get("/{account_id}")
async def get_account(account_id: str):
    """获取实盘账号详情"""
    try:
        service = get_live_account_service()
        result = service.get_account_by_uuid(account_id)

        if not result["success"]:
            raise NotFoundError("Account", account_id)

        return ok(data=result["data"], message="Account retrieved successfully")
    except NotFoundError:
        raise
    except Exception as e:
        logger.error(f"Error getting account {account_id}: {e}")
        raise BusinessError(f"Error getting account: {e}")


@router.put("/{account_id}")
async def update_account(account_id: str, data: UpdateLiveAccountRequest):
    """更新实盘账号信息"""
    try:
        service = get_live_account_service()

        result = service.update_account(
            account_uuid=account_id,
            name=data.name,
            api_key=data.api_key,
            api_secret=data.api_secret,
            passphrase=data.passphrase,
            description=data.description,
        )

        if not result["success"]:
            raise NotFoundError("Account", account_id)

        return ok(data=result["data"], message="Account updated successfully")
    except (NotFoundError, BusinessError):
        raise
    except Exception as e:
        logger.error(f"Error updating account {account_id}: {e}")
        raise BusinessError(f"Error updating account: {e}")


@router.delete("/{account_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_account(account_id: str):
    """删除实盘账号（软删除）"""
    try:
        service = get_live_account_service()
        result = service.delete_account(account_id)

        if not result["success"]:
            raise NotFoundError("Account", account_id)

        logger.info(f"Account {account_id} deleted successfully")
    except NotFoundError:
        raise
    except Exception as e:
        logger.error(f"Error deleting account {account_id}: {e}")
        raise BusinessError(f"Error deleting account: {e}")


@router.post("/{account_id}/validate")
async def validate_account(account_id: str):
    """验证实盘账号API凭证"""
    try:
        service = get_live_account_service()
        result = service.validate_account(account_id)

        if result["success"]:
            return ok(
                data={
                    "valid": result.get("valid", True),
                    "message": result.get("message", ""),
                    "account_info": result.get("account_info"),
                },
                message="Validation successful",
            )
        else:
            # 验证失败也返回 200，前端根据 valid 字段判断
            return ok(
                data={
                    "valid": False,
                    "message": result.get("message", "Validation failed"),
                    "error": result.get("message", ""),
                },
                message="Validation completed",
            )
    except Exception as e:
        logger.error(f"Error validating account {account_id}: {e}")
        return ok(
            data={
                "valid": False,
                "message": "Validation error",
                "error": str(e),
            },
            message="Validation completed",
        )


@router.put("/{account_id}/status")
async def update_account_status(account_id: str, data: UpdateAccountStatusRequest):
    """更新账号状态"""
    try:
        service = get_live_account_service()

        result = service.update_account_status(account_id, data.status.value)

        if not result["success"]:
            raise NotFoundError("Account", account_id)

        return ok(data=result["data"], message="Account status updated successfully")
    except (NotFoundError, BusinessError):
        raise
    except Exception as e:
        logger.error(f"Error updating account status {account_id}: {e}")
        raise BusinessError(f"Error updating account status: {e}")


@router.get("/{account_id}/balance")
async def get_account_balance(account_id: str):
    """获取账户余额信息"""
    try:
        service = get_live_account_service()
        result = service.get_account_balance(account_id)

        if not result["success"]:
            raise BusinessError(result.get("message", "Failed to get balance"))

        return ok(data=result["data"], message="Balance retrieved successfully")
    except BusinessError:
        raise
    except Exception as e:
        logger.error(f"Error getting account balance {account_id}: {e}")
        raise BusinessError(f"Error getting account balance: {e}")


@router.get("/{account_id}/positions")
async def get_account_positions(account_id: str):
    """获取账户持仓信息"""
    try:
        service = get_live_account_service()
        result = service.get_account_positions(account_id)

        if not result["success"]:
            raise BusinessError(result.get("message", "Failed to get positions"))

        return ok(data=result["data"], message="Positions retrieved successfully")
    except BusinessError:
        raise
    except Exception as e:
        logger.error(f"Error getting account positions {account_id}: {e}")
        raise BusinessError(f"Error getting account positions: {e}")
