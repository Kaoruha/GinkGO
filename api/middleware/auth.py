"""
JWT认证中间件

统一处理所有请求的 token 校验：
1. 检查 Authorization header (Bearer token)
2. 如果 header 没有，检查 URL query param (token=xxx)
3. 无 token 或 token 无效/过期 → 401
4. WebSocket 由 handler 调用 verify_token() 自行校验（BaseHTTPMiddleware 不支持 WebSocket）
5. Token 黑名单：logout/改密码后 token 立即失效（#5802, #5582, #5448）
"""
import uuid as _uuid
from fastapi import Request, HTTPException, status
from starlette.middleware.base import BaseHTTPMiddleware
from jose import JWTError, jwt
from datetime import datetime, timedelta
from typing import Optional

from core.config import settings
from core.logging import logger


class TokenBlacklist:
    """内存 Token 黑名单（#5802, #5582, #5448）

    支持两种撤销粒度：
    - 按 jti 撤销单个 token（logout）
    - 按 user_uuid 撤销该用户所有 token（改密码）
    """

    def __init__(self):
        # jti → True
        self._store: set[str] = set()
        # user_uuid → revoked_up_to timestamp
        self._user_revoked: dict[str, datetime] = {}

    def add(self, jti: str) -> None:
        """将单个 token 加入黑名单"""
        self._store.add(jti)

    def is_blacklisted(self, jti: str) -> bool:
        """检查 jti 是否在黑名单中"""
        return jti in self._store

    def revoke_user(self, user_uuid: str) -> None:
        """撤销某用户的所有 token（记录时间戳）"""
        self._user_revoked[user_uuid] = datetime.utcnow()

    def is_user_revoked(self, user_uuid: str) -> bool:
        """检查用户是否被全局撤销"""
        return user_uuid in self._user_revoked

    def check_revoked(self, payload: dict) -> bool:
        """综合检查 token 是否被撤销（jti 或 user 维度）"""
        jti = payload.get("jti")
        if jti and jti in self._store:
            return True

        user_uuid = payload.get("user_uuid")
        if user_uuid and user_uuid in self._user_revoked:
            revoked_at = self._user_revoked[user_uuid]
            # token 签发时间早于撤销时间 → 已撤销
            token_iat = payload.get("iat")
            if token_iat:
                if isinstance(token_iat, (int, float)):
                    token_time = datetime.utcfromtimestamp(token_iat)
                else:
                    token_time = token_iat
                if token_time < revoked_at:
                    return True
            else:
                # 无 iat 的旧 token，安全起见也撤销
                return True
        return False

    def cleanup(self) -> None:
        """清理过期条目（可选，token 自然过期后黑名单条目可清理）"""
        # 简单实现：暂不清理，内存占用极小
        pass


# 全局单例
token_blacklist = TokenBlacklist()


class JWTAuthMiddleware(BaseHTTPMiddleware):
    """JWT认证中间件"""

    # 不需要认证的路径
    PUBLIC_PATHS = {
        "/health",
        "/api/health",
        "/docs",
        "/redoc",
        "/openapi.json",
        "/api/v1/auth/login",
        "/api/v1/auth/register",
        "/api/v1/auth/verify",
    }

    async def dispatch(self, request: Request, call_next):
        # WebSocket 无法通过 BaseHTTPMiddleware 处理，由 handler 调用 verify_token
        if request.scope.get("type") == "websocket":
            return await call_next(request)

        path = request.url.path

        if path in self.PUBLIC_PATHS:
            return await call_next(request)

        # 统一校验 token
        token = self._extract_token(request)
        if not token:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Missing authentication token",
            )

        try:
            payload = verify_token(token)
        except JWTError as e:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid or expired token",
            )

        # 注入用户信息
        request.state.user = payload
        request.state.user_uuid = payload.get("user_uuid")
        request.state.credential_uuid = payload.get("credential_uuid")
        request.state.username = payload.get("username")
        request.state.is_admin = payload.get("is_admin", False)

        return await call_next(request)

    def _extract_token(self, request: Request) -> Optional[str]:
        """先查 header，没有再查 query param"""
        authorization = request.headers.get("Authorization")
        if authorization and authorization.startswith("Bearer "):
            return authorization[7:]

        return request.query_params.get("token")


def verify_token(token: str) -> dict:
    """验证并解码 token，供中间件和 WebSocket handler 共用

    增加 token 黑名单检查（#5802, #5582, #5448）
    """
    payload = jwt.decode(token, settings.SECRET_KEY, algorithms=["HS256"])

    # 检查黑名单
    if token_blacklist.check_revoked(payload):
        raise JWTError("Token has been revoked")

    return payload


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """创建访问令牌

    自动添加 jti（唯一 token ID）和 iat（签发时间）（#5802）
    """
    to_encode = data.copy()

    # 生成唯一 token ID（用于黑名单）
    if "jti" not in to_encode:
        to_encode["jti"] = str(_uuid.uuid4())

    # 记录签发时间（用于 user 维度撤销判断）
    if "iat" not in to_encode:
        to_encode["iat"] = datetime.utcnow()

    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)

    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, settings.SECRET_KEY, algorithm="HS256")
