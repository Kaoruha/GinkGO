"""
JWT认证中间件
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

    # 跳过认证的路径（精确匹配）
    SKIP_AUTH_PATHS = {
        "/health",
        "/api/health",  # 前端代理路径
        "/docs",
        "/redoc",
        "/openapi.json",
        "/api/v1/auth/login",
        "/api/v1/auth/register",
        "/api/v1/auth/verify",
    }

    # 跳过认证的路径前缀（前缀匹配）
    SKIP_AUTH_PREFIXES = {
        "/api/v1/portfolios",  # 开发模式暂时跳过认证
        "/api/v1/backtests",   # 开发模式暂时跳过认证
        "/api/v1/node-graphs", # 开发模式暂时跳过认证（节点图配置）
        "/api/v1/components", # 开发模式暂时跳过认证
        "/api/v1/data",       # 开发模式暂时跳过认证
        "/api/v1/dashboard",  # 开发模式暂时跳过认证
        "/api/v1/settings",   # 开发模式暂时跳过认证（设置页面）
    }

    async def dispatch(self, request: Request, call_next):
        path = request.url.path

        # 检查精确匹配的路径
        if path in self.SKIP_AUTH_PATHS:
            return await call_next(request)

        # 检查前缀匹配的路径
        for prefix in self.SKIP_AUTH_PREFIXES:
            if path.startswith(prefix):
                return await call_next(request)

        # 获取 token
        token = self.get_token_from_request(request)

        if not token:
            logger.warning(f"Missing token for {request.url.path}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Missing authentication token"
            )

        # 验证 token
        try:
            payload = decode_token(token)
            # 将用户信息注入到 request.state
            request.state.user = payload
            request.state.user_uuid = payload.get("user_uuid")
            request.state.credential_uuid = payload.get("credential_uuid")
            request.state.username = payload.get("username")
            request.state.is_admin = payload.get("is_admin", False)
        except JWTError as e:
            logger.warning(f"Invalid token: {e}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid or expired token"
            )

        return await call_next(request)

    def get_token_from_request(self, request: Request) -> Optional[str]:
        """从请求中获取 token"""
        # 从 Authorization header 获取
        authorization = request.headers.get("Authorization")
        if authorization and authorization.startswith("Bearer "):
            return authorization[7:]  # 去掉 "Bearer " 前缀

        # 从 query 参数获取（用于 WebSocket）
        token = request.query_params.get("token")
        if token:
            return token

        return None


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """创建访问令牌"""
    to_encode = data.copy()

    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)

    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm="HS256")

    return encoded_jwt


def decode_token(token: str) -> dict:
    """解码访问令牌"""
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=["HS256"])
        return payload
    except JWTError:
        raise
