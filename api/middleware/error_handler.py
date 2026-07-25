"""
全局错误处理中间件

将所有异常转换为统一的响应格式。
"""

import uuid

from fastapi import Request, HTTPException, status
from fastapi.responses import JSONResponse

from core.logging import logger
from core.exceptions import APIError


def _trace_id() -> str:
    """错误响应 trace_id：优先取请求已注入的（与日志一致），fallback 生成。

    TraceIdMiddleware 在请求入口 set GLOG contextvars，exception_handler 在 middleware
    内层执行，此时 trace_id 仍在作用域内 → 错误信封 trace_id 与该请求日志同源（#6784）。
    """
    try:
        from ginkgo.libs import GLOG
        return GLOG.get_trace_id() or uuid.uuid4().hex[:16]
    except ImportError:
        return uuid.uuid4().hex[:16]


async def global_error_handler(request: Request, exc: Exception):
    """将所有异常转换为 {code, data, message, trace_id} 格式"""

    if isinstance(exc, APIError):
        logger.error(f"APIError [{exc.code}] {request.url.path}: {exc.message}")
        return JSONResponse(status_code=exc.status_code, content=exc.to_dict())

    if isinstance(exc, HTTPException):
        logger.error(f"HTTPException [{exc.status_code}] {request.url.path}: {exc.detail}")
        return JSONResponse(
            status_code=exc.status_code,
            content={
                "code": exc.status_code,
                "data": None,
                "message": exc.detail,
                "trace_id": _trace_id(),
            },
        )

    # 未捕获异常
    logger.exception(f"Unhandled exception {request.url.path}: {exc}")
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "code": 500,
            "data": None,
            "message": "Internal Server Error",
            "trace_id": _trace_id(),
        },
    )
