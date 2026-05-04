"""
JWT认证中间件

统一处理所有请求的 token 校验：
1. 检查 Authorization header (Bearer token)
2. 如果 header 没有，检查 URL query param (token=xxx)
3. 无 token 或 token 无效/过期 → 401
4. WebSocket 由 handler 调用 verify_token() 自行校验（BaseHTTPMiddleware 不支持 WebSocket）
"""
from fastapi import Request, HTTPException, status
from starlette.middleware.base import BaseHTTPMiddleware
from jose import JWTError, jwt
from datetime import datetime, timedelta
from typing import Optional

from core.config import settings
from core.logging import logger


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
    """验证并解码 token，供中间件和 WebSocket handler 共用"""
    payload = jwt.decode(token, settings.SECRET_KEY, algorithms=["HS256"])
    return payload


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """创建访问令牌"""
    to_encode = data.copy()

    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)

    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, settings.SECRET_KEY, algorithm="HS256")
