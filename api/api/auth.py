"""
认证相关API路由
"""

from fastapi import APIRouter, HTTPException, status, Request, Header
from pydantic import BaseModel
from datetime import datetime, timedelta
from typing import Optional
import bcrypt

from middleware.auth import create_access_token
from core.config import settings
from core.logging import logger
from core.response import ok
from ginkgo.data.services.user_service import UserService

router = APIRouter()


class LoginRequest(BaseModel):
    username: str
    password: str


class UserSummary(BaseModel):
    uuid: str
    username: str
    display_name: str
    is_admin: bool


class LoginResponse(BaseModel):
    token: str
    expires_at: str
    user: UserSummary


class RegisterRequest(BaseModel):
    username: str
    password: str
    display_name: Optional[str] = None


class ChangePasswordRequest(BaseModel):
    old_password: str
    new_password: str


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')


def verify_password(password: str, password_hash: str) -> bool:
    return bcrypt.checkpw(password.encode('utf-8'), password_hash.encode('utf-8'))


def get_user_service():
    return UserService()


@router.post("/login")
async def login(login_request: LoginRequest, req: Request):
    """用户登录"""
    logger.info(f"Login attempt for user: {login_request.username}")

    user_service = get_user_service()

    # 根据username查找用户
    result = user_service.list_users(username=login_request.username)

    if not result.success or not result.data:
        logger.warning(f"Login failed for user: {login_request.username} - user not found")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid username or password"
        )

    user_info = result.data[0]
    user_uuid = user_info["uuid"]

    # 获取关联的Credential
    credential = user_service.get_credential(user_uuid)

    if not credential:
        logger.warning(f"Login failed for user: {login_request.username} - no credential found")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid username or password"
        )

    # 检查账户是否启用
    if not credential.is_active or not user_info.get("is_active", True):
        logger.warning(f"Login failed for user: {login_request.username} - account disabled")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account is disabled"
        )

    # 验证密码
    if not verify_password(login_request.password, credential.password_hash):
        logger.warning(f"Login failed for user: {login_request.username} - wrong password")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid username or password"
        )

    # 更新最后登录时间
    client_ip = req.client.host if req.client else ""
    user_service.update_last_login(credential.uuid, client_ip)

    # 生成JWT token
    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    token_data = {
        "user_uuid": user_uuid,
        "credential_uuid": credential.uuid,
        "username": user_info["username"],
        "is_admin": credential.is_admin
    }
    token = create_access_token(token_data, access_token_expires)

    expires_at = datetime.utcnow() + access_token_expires

    logger.info(f"Login successful for user: {login_request.username}")

    response_data = {
        "token": token,
        "expires_at": expires_at.isoformat() + "Z",
        "user": {
            "uuid": user_uuid,
            "username": user_info["username"],
            "display_name": user_info.get("display_name", user_info["username"]),
            "is_admin": credential.is_admin
        }
    }
    return ok(data=response_data)


@router.post("/register", status_code=201)
async def register(data: RegisterRequest, req: Request):
    """用户注册"""
    logger.info(f"Registration attempt for username: {data.username}")

    user_service = get_user_service()

    password_hash = hash_password(data.password)
    result = user_service.create_user(
        username=data.username,
        display_name=data.display_name,
        description=f"Registered user: {data.username}",
        password_hash=password_hash,
    )

    if not result.success:
        if "already exists" in result.error:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=result.error)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=result.error
        )

    logger.info(f"User registered successfully: {data.username}")
    return ok(data=result.data)


@router.post("/logout")
async def logout():
    return ok(message="Logged out successfully")


@router.get("/verify")
async def verify_token(req: Request):
    user_uuid = req.state.user_uuid if hasattr(req.state, "user_uuid") else None
    username = req.state.username if hasattr(req.state, "username") else None
    is_admin = req.state.is_admin if hasattr(req.state, "is_admin") else False

    return ok(data={
        "valid": True,
        "user_uuid": user_uuid,
        "username": username,
        "is_admin": is_admin
    })


@router.post("/change-password")
async def change_password(data: ChangePasswordRequest, req: Request):
    """修改密码"""
    credential_uuid = req.state.credential_uuid if hasattr(req.state, "credential_uuid") else None
    user_uuid = req.state.user_uuid if hasattr(req.state, "user_uuid") else None

    if not credential_uuid:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated"
        )

    user_service = get_user_service()

    # 获取用户凭证
    credential = user_service.get_credential(user_uuid)
    if not credential:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User credential not found"
        )

    # 验证旧密码
    if not verify_password(data.old_password, credential.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect old password"
        )

    # 更新密码
    new_password_hash = hash_password(data.new_password)
    success = user_service.update_password(credential.uuid, new_password_hash)

    if not success:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update password"
        )

    logger.info(f"Password changed for user: {user_uuid}")
    return ok(message="Password changed successfully")


@router.get("/me")
async def get_current_user(req: Request):
    """获取当前用户信息"""
    user_uuid = req.state.user_uuid if hasattr(req.state, "user_uuid") else None

    if not user_uuid:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated"
        )

    user_service = get_user_service()
    result = user_service.get_user(user_uuid)

    if not result.success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )

    user = result.data
    credential = user_service.get_credential(user_uuid)

    user_data = {
        "uuid": user.uuid,
        "username": user.username,
        "display_name": user.display_name or user.username,
        "is_admin": credential.is_admin if credential else False
    }
    return ok(data=user_data)
