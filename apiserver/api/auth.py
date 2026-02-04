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
from ginkgo.data.containers import container
from ginkgo.data.models import MUserCredential, MUser
from ginkgo.enums import SOURCE_TYPES, USER_TYPES

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
    """对密码进行哈希"""
    return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')


def verify_password(password: str, password_hash: str) -> bool:
    """验证密码"""
    return bcrypt.checkpw(password.encode('utf-8'), password_hash.encode('utf-8'))


def get_user_credential_crud():
    """获取UserCredentialCRUD实例"""
    return container.user_credential_crud()


def get_user_crud():
    """获取UserCRUD实例"""
    return container.user_crud()


@router.post("/login", response_model=LoginResponse)
async def login(login_request: LoginRequest, req: Request):
    """用户登录"""
    logger.info(f"Login attempt for user: {login_request.username}")

    user_crud = get_user_crud()
    credential_crud = get_user_credential_crud()

    # 根据username查找MUser
    users = user_crud.find(filters={"username": login_request.username, "is_del": False}, as_dataframe=False)

    if not users:
        logger.warning(f"Login failed for user: {login_request.username} - user not found")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid username or password"
        )

    user = users[0]

    # 获取关联的Credential
    credentials = credential_crud.get_by_user_id(user.uuid, as_dataframe=False)

    if not credentials:
        logger.warning(f"Login failed for user: {login_request.username} - no credential found")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid username or password"
        )

    credential = credentials[0]

    # 检查账户是否启用
    if not credential.is_active or not user.is_active:
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
    credential_crud.update_last_login(credential.uuid, client_ip)

    # 生成JWT token
    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    token_data = {
        "user_uuid": user.uuid,
        "credential_uuid": credential.uuid,
        "username": user.username,
        "is_admin": credential.is_admin
    }
    token = create_access_token(token_data, access_token_expires)

    # 计算过期时间
    expires_at = datetime.utcnow() + access_token_expires

    logger.info(f"Login successful for user: {login_request.username}")

    return LoginResponse(
        token=token,
        expires_at=expires_at.isoformat() + "Z",
        user=UserSummary(
            uuid=user.uuid,
            username=user.username,
            display_name=user.display_name or user.username,
            is_admin=credential.is_admin
        )
    )


@router.post("/register", response_model=UserSummary, status_code=201)
async def register(data: RegisterRequest, req: Request):
    """用户注册 - 同时创建MUser和MUserCredential"""
    logger.info(f"Registration attempt for username: {data.username}")

    user_crud = get_user_crud()
    credential_crud = get_user_credential_crud()

    # 检查用户名是否已存在
    existing_users = user_crud.find(filters={"username": data.username, "is_del": False}, as_dataframe=False)
    if existing_users:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Username already exists"
        )

    try:
        # 1. 先创建MUser（业务用户）
        user = MUser(
            username=data.username,
            display_name=data.display_name or data.username,
            email="",
            description=f"Registered user: {data.username}",
            user_type=USER_TYPES.PERSON,
            is_active=True,
            source=SOURCE_TYPES.OTHER
        )
        created_user = user_crud.add(user)

        if not created_user:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to create user"
            )

        # 2. 创建MUserCredential，关联到MUser
        password_hash = hash_password(data.password)
        credential = MUserCredential(
            user_id=created_user.uuid,  # 关联到MUser
            password_hash=password_hash,
            is_active=True,
            is_admin=False
        )
        created_credential = credential_crud.add(credential)

        if not created_credential:
            # 如果创建凭证失败，删除已创建的user
            user_crud.delete(filters={"uuid": created_user.uuid})
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to create user credential"
            )

        logger.info(f"User registered successfully: {data.username} (user_uuid={created_user.uuid})")

        return UserSummary(
            uuid=created_user.uuid,
            username=data.username,
            display_name=data.display_name or data.username,
            is_admin=False
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Registration error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Registration failed"
        )


@router.post("/logout")
async def logout():
    """用户登出"""
    # JWT 是无状态的，登出主要在前端删除 token
    # 如果需要服务端失效 token，可以使用 Redis 黑名单
    return {"message": "Logged out successfully"}


@router.get("/verify")
async def verify_token(req: Request):
    """验证Token"""
    # 由于 JWT 中间件已验证，这里直接返回成功
    user_uuid = req.state.user_uuid if hasattr(req.state, "user_uuid") else None
    username = req.state.username if hasattr(req.state, "username") else None
    is_admin = req.state.is_admin if hasattr(req.state, "is_admin") else False

    return {
        "valid": True,
        "user_uuid": user_uuid,
        "username": username,
        "is_admin": is_admin
    }


@router.post("/change-password")
async def change_password(data: ChangePasswordRequest, req: Request):
    """修改密码"""
    # 需要JWT认证
    credential_uuid = req.state.credential_uuid if hasattr(req.state, "credential_uuid") else None
    user_uuid = req.state.user_uuid if hasattr(req.state, "user_uuid") else None

    if not credential_uuid:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated"
        )

    credential_crud = get_user_credential_crud()

    # 获取用户凭证
    credentials = credential_crud.find(filters={"uuid": credential_uuid}, as_dataframe=False)
    if not credentials:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User credential not found"
        )

    credential = credentials[0]

    # 验证旧密码
    if not verify_password(data.old_password, credential.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect old password"
        )

    # 更新密码
    new_password_hash = hash_password(data.new_password)
    success = credential_crud.update_password(credential.uuid, new_password_hash)

    if not success:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update password"
        )

    logger.info(f"Password changed for user: {user_uuid}")

    return {"message": "Password changed successfully"}


@router.get("/me", response_model=UserSummary)
async def get_current_user(req: Request):
    """获取当前用户信息"""
    user_uuid = req.state.user_uuid if hasattr(req.state, "user_uuid") else None
    username = req.state.username if hasattr(req.state, "username") else None
    is_admin = req.state.is_admin if hasattr(req.state, "is_admin") else False

    if not user_uuid:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated"
        )

    user_crud = get_user_crud()
    credential_crud = get_user_credential_crud()

    # 获取用户信息
    users = user_crud.find(filters={"uuid": user_uuid}, as_dataframe=False)

    if not users:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )

    user = users[0]

    # 获取credential以确认admin状态
    credentials = credential_crud.get_by_user_id(user_uuid, as_dataframe=False)
    is_admin = credentials[0].is_admin if credentials else False

    return UserSummary(
        uuid=user.uuid,
        username=user.username,
        display_name=user.display_name or user.username,
        is_admin=is_admin
    )
