"""
全局错误处理中间件
"""

from fastapi import Request, HTTPException, status
from fastapi.responses import JSONResponse
from datetime import datetime

from core.logging import logger


async def global_error_handler(request: Request, exc: Exception):
    """全局错误处理器"""

    # 记录错误
    logger.error(f"Error processing {request.url.path}: {exc}")

    # HTTPException 处理
    if isinstance(exc, HTTPException):
        return JSONResponse(
            status_code=exc.status_code,
            content={
                "code": exc.status_code,
                "message": exc.detail,
                "timestamp": datetime.utcnow().isoformat() + "Z"
            }
        )

    # 其他未捕获异常
    logger.exception(f"Unhandled exception: {exc}")

    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "code": 500,
            "message": "Internal Server Error",
            "timestamp": datetime.utcnow().isoformat() + "Z"
        }
    )


class APIError(Exception):
    """自定义API错误基类"""

    def __init__(self, message: str, code: int = 500):
        self.message = message
        self.code = code
        super().__init__(self.message)


class NotFoundError(APIError):
    """资源未找到错误"""

    def __init__(self, message: str = "Resource not found"):
        super().__init__(message, 404)


class ValidationError(APIError):
    """验证错误"""

    def __init__(self, message: str = "Validation failed"):
        super().__init__(message, 400)


class UnauthorizedError(APIError):
    """未授权错误"""

    def __init__(self, message: str = "Unauthorized"):
        super().__init__(message, 401)


class ForbiddenError(APIError):
    """禁止访问错误"""

    def __init__(self, message: str = "Forbidden"):
        super().__init__(message, 403)
