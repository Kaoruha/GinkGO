"""
全局错误处理中间件

处理所有 API 抛出的异常，返回统一的响应格式。
"""

from fastapi import Request, HTTPException, status
from fastapi.responses import JSONResponse
from datetime import datetime

from core.logging import logger
from core.exceptions import APIError


async def global_error_handler(request: Request, exc: Exception):
    """
    全局错误处理器

    将所有异常转换为统一的 API 响应格式。

    Args:
        request: FastAPI 请求对象
        exc: 捕获的异常

    Returns:
        JSONResponse: 统一格式的错误响应
    """
    # 记录错误
    logger.error(f"Error processing {request.url.path}: {exc}")

    # APIError 处理（使用新统一格式）
    if isinstance(exc, APIError):
        response_data = exc.to_dict()
        return JSONResponse(
            status_code=exc.status_code,
            content=response_data
        )

    # HTTPException 处理（兼容 FastAPI 内置异常）
    if isinstance(exc, HTTPException):
        return JSONResponse(
            status_code=exc.status_code,
            content={
                "success": False,
                "data": None,
                "error": str(exc.status_code),
                "message": exc.detail
            }
        )

    # 其他未捕获异常
    logger.exception(f"Unhandled exception: {exc}")

    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "success": False,
            "data": None,
            "error": "INTERNAL_ERROR",
            "message": "Internal Server Error"
        }
    )
