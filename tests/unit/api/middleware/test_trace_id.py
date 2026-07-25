"""
TraceIdMiddleware 单元测试（#6784 可观测层接入 1/4）

覆盖:全量注入、客户端透传、响应头回写、错误响应 trace_id 一致性、贯穿 api+src 层。
用最小 FastAPI app + TraceIdMiddleware + global_error_handler 隔离测试,不引入完整 Ginkgo app。
"""
import uuid

import pytest
from fastapi import FastAPI, HTTPException
from httpx import ASGITransport, AsyncClient

from middleware.trace_id import TRACE_ID_HEADER, TraceIdMiddleware
from middleware.error_handler import global_error_handler
from core.exceptions import APIError, NotFoundError


@pytest.fixture
def app():
    """最小 app:只挂 TraceIdMiddleware + 错误处理,避免拉起完整 Ginkgo 服务。"""
    app = FastAPI()
    app.add_middleware(TraceIdMiddleware)
    # 复刻 main.py 的三层注册(Exception/APIError/HTTPException);漏 APIError 会致
    # NotFoundError 冒泡到 ServerErrorMiddleware 而非 ExceptionMiddleware
    app.exception_handler(Exception)(global_error_handler)
    app.exception_handler(APIError)(global_error_handler)
    app.exception_handler(HTTPException)(global_error_handler)

    @app.get("/probe")
    async def probe():
        # 端点内读 GLOG contextvars,验证 src 层贯穿
        from ginkgo.libs import GLOG
        return {"trace_id": GLOG.get_trace_id()}

    @app.get("/boom")
    async def boom():
        raise HTTPException(status_code=400, detail="test error")

    @app.get("/apierror")
    async def apierror():
        # APIError 子类:构造时自生随机 trace_id(exceptions.py),用于验证 error_handler
        # override body.trace_id 为请求 trace_id(否则与 X-Trace-Id 头脱钩)
        raise NotFoundError("user", "123")

    return app


@pytest.mark.asyncio
async def test_inject_trace_id_every_request(app):
    """全量注入:无客户端头时,响应回写 X-Trace-Id,且贯穿到端点内 GLOG。"""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        r = await c.get("/probe")
    assert r.status_code == 200
    assert TRACE_ID_HEADER in r.headers
    # 贯穿:端点读到的 GLOG trace_id == 响应头
    assert r.json()["trace_id"] == r.headers[TRACE_ID_HEADER]


@pytest.mark.asyncio
async def test_passthrough_client_header(app):
    """透传:客户端带 X-Trace-Id 时复用,不重新生成。"""
    client_tid = uuid.uuid4().hex[:16]
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        r = await c.get("/probe", headers={TRACE_ID_HEADER: client_tid})
    assert r.headers[TRACE_ID_HEADER] == client_tid
    assert r.json()["trace_id"] == client_tid


@pytest.mark.asyncio
async def test_unique_trace_id_per_request(app):
    """隔离:不同请求 trace_id 不同(contextvars 不泄漏)。"""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        r1 = await c.get("/probe")
        r2 = await c.get("/probe")
    t1 = r1.headers[TRACE_ID_HEADER]
    t2 = r2.headers[TRACE_ID_HEADER]
    assert t1 != t2
    assert len(t1) == 16 and len(t2) == 16


@pytest.mark.asyncio
async def test_error_response_trace_id_consistency(app):
    """错误响应 trace_id 与响应头一致(error_handler 读 GLOG.get_trace_id,非随机重生成)。"""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        r = await c.get("/boom")
    assert r.status_code == 400
    body = r.json()
    # 错误信封 trace_id == 响应头(同一请求 trace_id 贯穿到异常处理)
    assert body["trace_id"] == r.headers[TRACE_ID_HEADER]


@pytest.mark.asyncio
async def test_error_passthrough_consistency(app):
    """透传 + 错误:客户端 trace_id 贯穿到错误响应信封。"""
    client_tid = uuid.uuid4().hex[:16]
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        r = await c.get("/boom", headers={TRACE_ID_HEADER: client_tid})
    assert r.json()["trace_id"] == client_tid
    assert r.headers[TRACE_ID_HEADER] == client_tid


@pytest.mark.asyncio
async def test_apierror_response_trace_id_consistency(app):
    """APIError 响应 body.trace_id 必须等于请求 X-Trace-Id 头,而非 exc 自生随机值。

    回归 #6797 review:exc.to_dict() 带 APIError 构造时自生的随机 trace_id,修复前
    error_handler 直接 content=exc.to_dict() 致 body 与响应头脱钩(同一响应两个 trace_id)。
    """
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        r = await c.get("/apierror")
    assert r.status_code == 404
    body = r.json()
    header_tid = r.headers[TRACE_ID_HEADER]
    assert body["trace_id"] == header_tid, (
        f"APIError body trace_id({body['trace_id']})与响应头({header_tid})脱钩 — "
        "应 override 为请求 trace_id,而非 exc 自生随机值"
    )


@pytest.mark.asyncio
async def test_apierror_passthrough_consistency(app):
    """APIError 路径下,入站 X-Trace-Id 贯穿到 body.trace_id(非 exc 随机值)。"""
    client_tid = uuid.uuid4().hex[:16]
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        r = await c.get("/apierror", headers={TRACE_ID_HEADER: client_tid})
    assert r.status_code == 404
    assert r.json()["trace_id"] == client_tid
    assert r.headers[TRACE_ID_HEADER] == client_tid


# ---------------------------------------------------------------------------
# 中间件异常路径回归守护 (port 自 #6788 review 问题 1)
#
# 缺陷:内层中间件(如 JWTAuthMiddleware 401)抛 HTTPException 时,异常逃逸
# TraceIdMiddleware 的 with 块 → contextvar reset + 响应头写入行被跳过;
# global_error_handler 由外层 ServerErrorMiddleware 在 contextvar 作用域之外触发,
# trace_id 二次生成且日志显示 "-"。修复靠 request.state.trace_id (随 scope 存活、跨 unwind)
# 作跨层通道,handler 补头 + 临时复位 contextvar。
# 用忠实最小栈复现(内层 raise 中间件 + TraceId 最外层 + 同 main.py 的 handler 注册)。
# ---------------------------------------------------------------------------


def _build_raising_stack(raiser):
    """复刻 main.py 栈序:内层 raising 中间件 + TraceIdMiddleware 最外层 + 全局 handler。"""
    from fastapi import FastAPI, HTTPException
    from middleware.trace_id import TraceIdMiddleware
    from middleware.error_handler import global_error_handler

    app = FastAPI()
    app.add_middleware(raiser)  # 内层(模拟 JWT)
    app.add_middleware(TraceIdMiddleware)  # 最后注册 = 栈顶最外层(同 main.py)
    app.exception_handler(Exception)(global_error_handler)
    app.exception_handler(HTTPException)(global_error_handler)
    return app


def test_middleware_raised_exception_keeps_header_and_trace_id():
    """内层中间件 raise HTTPException(401) → X-Trace-Id 头不丢、body trace_id 不脱钩。

    回归 #6788 问题 1:修复前 header=None、body trace_id 新生成。
    """
    from fastapi import HTTPException
    from fastapi.testclient import TestClient
    from starlette.middleware.base import BaseHTTPMiddleware

    class JWTLikeMiddleware(BaseHTTPMiddleware):
        async def dispatch(self, request, call_next):
            raise HTTPException(status_code=401, detail="Missing authentication token")

    app = _build_raising_stack(JWTLikeMiddleware)
    client = TestClient(app, raise_server_exceptions=False)

    resp = client.get("/anything")  # 任意路径,内层中间件无条件 raise
    assert resp.status_code == 401
    header_tid = resp.headers.get("x-trace-id")
    assert header_tid is not None, "中间件异常路径 X-Trace-Id 头丢失 (#6788 问题 1)"
    body_tid = resp.json()["trace_id"]
    assert body_tid == header_tid, (
        f"body trace_id({body_tid})与响应头({header_tid})脱钩 — 应复用同一 trace_id"
    )


def test_middleware_raised_exception_passes_through_client_trace_id():
    """中间件异常路径下,入站 X-Trace-Id 仍正确透传到响应头/body。"""
    from fastapi import HTTPException
    from fastapi.testclient import TestClient
    from starlette.middleware.base import BaseHTTPMiddleware

    class JWTLikeMiddleware(BaseHTTPMiddleware):
        async def dispatch(self, request, call_next):
            raise HTTPException(status_code=401, detail="Invalid token")

    app = _build_raising_stack(JWTLikeMiddleware)
    client = TestClient(app, raise_server_exceptions=False)

    fixed = "1122334455667788"
    resp = client.get("/anything", headers={"X-Trace-Id": fixed})
    assert resp.status_code == 401
    assert resp.headers.get("x-trace-id") == fixed, "异常路径未透传入站 trace_id"
    assert resp.json()["trace_id"] == fixed


def test_middleware_raised_exception_log_carries_trace_id():
    """中间件异常路径下,global_error_handler 的错误日志携带请求 trace_id(非 "-")。

    回归 #6788:修复前 contextvar 已 reset,handler 日志输出 trace_id="-"。
    """
    import io
    import logging
    from fastapi import HTTPException
    from fastapi.testclient import TestClient
    from starlette.middleware.base import BaseHTTPMiddleware
    from core.logging import logger as api_logger, TraceIdFilter

    class JWTLikeMiddleware(BaseHTTPMiddleware):
        async def dispatch(self, request, call_next):
            raise HTTPException(status_code=401, detail="Missing authentication token")

    app = _build_raising_stack(JWTLikeMiddleware)
    # 最小 app 不走 setup_logging,手动确保捕获 logger 带 TraceIdFilter(幂等)
    if not any(isinstance(f, TraceIdFilter) for f in api_logger.filters):
        api_logger.addFilter(TraceIdFilter())

    stream = io.StringIO()
    h = logging.StreamHandler(stream)
    h.setFormatter(logging.Formatter("%(trace_id)s|%(message)s"))
    api_logger.addHandler(h)
    try:
        client = TestClient(app, raise_server_exceptions=False)
        fixed = "9988776655443322"
        client.get("/anything", headers={"X-Trace-Id": fixed})
    finally:
        api_logger.removeHandler(h)

    out = stream.getvalue()
    assert fixed in out, (
        f"错误日志未携带请求 trace_id(应为 {fixed}),输出: {out!r} — contextvar 未复位 (#6788)"
    )
