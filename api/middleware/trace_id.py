"""请求级 trace_id 中间件 (#6784 可观测层接入 1/4)。

每个 API 请求注入/透传 trace_id，绑定到 GLOG contextvars，贯穿该请求在
API 进程内的全部日志 (router→service→crud)，并回写 X-Trace-Id 响应头，
供客户端关联。是后续跨进程 trace_id 传播 (backtest/paper/live worker) 的前置基座。
"""
import uuid

from ginkgo.libs import GLOG
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

TRACE_ID_HEADER = "X-Trace-Id"


def _new_trace_id() -> str:
    """生成 16 字符 hex trace_id (与 error_handler._trace_id() 同 scheme)。"""
    return uuid.uuid4().hex[:16]


class TraceIdMiddleware(BaseHTTPMiddleware):
    """为每个请求绑定 trace_id 到 GLOG contextvars，并回写响应头。

    绑定期间，该请求在 API 进程内发出的全部 GLOG 日志 (router→service→crud)
    都携带同一 trace_id (container 模式输出为 ECS trace.id 字段)；请求结束
    后 contextvar 自动复位，杜绝跨请求泄漏。
    """

    async def dispatch(self, request: Request, call_next):
        trace_id = request.headers.get(TRACE_ID_HEADER) or _new_trace_id()
        with GLOG.with_trace_id(trace_id):
            response: Response = await call_next(request)
        response.headers[TRACE_ID_HEADER] = trace_id
        return response
