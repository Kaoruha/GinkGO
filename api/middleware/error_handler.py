"""
全局错误处理中间件

将所有异常转换为统一的响应格式。
"""

import contextlib
import uuid

from fastapi import Request, HTTPException, status
from fastapi.responses import JSONResponse

from core.logging import logger
from core.exceptions import APIError
from middleware.trace_id import TRACE_ID_HEADER

try:
    from ginkgo.libs import GLOG

    _GLOG_AVAILABLE = True
except ImportError:
    _GLOG_AVAILABLE = False


def _trace_id(request: Request | None = None) -> str:
    """复用请求绑定的 trace_id，无则新生成。

    优先级：request.state.trace_id（TraceIdMiddleware 注入，随 scope 存活，能跨越
    中间件异常 unwind）→ GLOG contextvar（正常路径业务层日志已绑定）→ 新生成。
    保证错误信封、响应头与该请求全部日志同 trace_id。

    对无 state 的 fake/mock request 健壮(单测直接调 handler 的场景)。
    """
    if request is not None:
        try:
            tid = request.state.trace_id
        except (AttributeError, TypeError):
            tid = None
        if isinstance(tid, str) and tid:
            return tid
    if _GLOG_AVAILABLE:
        tid = GLOG.get_trace_id()
        if tid:
            return tid
    return uuid.uuid4().hex[:16]


async def global_error_handler(request: Request, exc: Exception):
    """将所有异常转换为 {code, data, message, trace_id} 格式。

    中间件抛出的异常（如 JWTAuthMiddleware 的 401）会逃逸到 ServerErrorMiddleware，
    在 TraceIdMiddleware 的 contextvar 作用域之外触发本 handler。故 trace_id 取
    request.state（随 scope 存活），并以 with_trace_id 临时复位 contextvar，使错误
    日志、X-Trace-Id 响应头、body trace_id 三者一致 (#6788 review 修复)。
    """
    trace_id = _trace_id(request)
    headers = {TRACE_ID_HEADER: trace_id}
    trace_cm = (
        GLOG.with_trace_id(trace_id)
        if _GLOG_AVAILABLE
        else contextlib.nullcontext()
    )
    with trace_cm:
        if isinstance(exc, APIError):
            logger.error(f"APIError [{exc.code}] {request.url.path}: {exc.message}")
            return JSONResponse(
                status_code=exc.status_code, content=exc.to_dict(), headers=headers
            )

        if isinstance(exc, HTTPException):
            logger.error(
                f"HTTPException [{exc.status_code}] {request.url.path}: {exc.detail}"
            )
            return JSONResponse(
                status_code=exc.status_code,
                headers=headers,
                content={
                    "code": exc.status_code,
                    "data": None,
                    "message": exc.detail,
                    "trace_id": trace_id,
                },
            )

        # 未捕获异常
        logger.exception(f"Unhandled exception {request.url.path}: {exc}")
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            headers=headers,
            content={
                "code": 500,
                "data": None,
                "message": "Internal Server Error",
                "trace_id": trace_id,
            },
        )
