"""
Trace ID 中间件（全量注入）

每个请求注入一个 trace_id 到 GLOG contextvars，贯穿该请求在 API 进程内的全部日志：
- src 层（service/crud/engine）走 GLOG structlog，ecs_processor 读 _trace_id_ctx 输出 trace.id
- api 层（router/middleware）走 core.logging 标准 logging，TraceIdFilter 同源读 _trace_id_ctx
两层共享同一 _trace_id_ctx 源头，单 trace_id 即可聚合一个请求全链路日志。

透传客户端 X-Trace-Id（若有），否则生成；所有响应回写 X-Trace-Id。

#6784 可观测层接入 1/4
"""
import uuid

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from ginkgo.libs import GLOG

# 与 error_handler._trace_id 一致的格式（uuid4 hex 前 16 位）
TRACE_ID_HEADER = "X-Trace-Id"


def _new_trace_id() -> str:
    return uuid.uuid4().hex[:16]


class TraceIdMiddleware(BaseHTTPMiddleware):
    """
    全量注入 trace_id（每个请求都注入，不采样）。

    - 透传客户端 X-Trace-Id（若有），否则生成
    - GLOG.with_trace_id 注入 contextvars，同请求所有日志（api+src 层）共享
    - 响应回写 X-Trace-Id，便于客户端关联
    """

    async def dispatch(self, request: Request, call_next):
        trace_id = request.headers.get(TRACE_ID_HEADER) or _new_trace_id()
        # sync contextmanager 包 await call_next: contextvars 在同 task 贯穿该请求所有
        # 后续 await（service/crud 同 task 读到），请求结束 finally 自动 reset 不泄漏
        with GLOG.with_trace_id(trace_id):
            response: Response = await call_next(request)
        response.headers[TRACE_ID_HEADER] = trace_id
        return response
