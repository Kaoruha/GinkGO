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


@pytest.fixture
def app():
    """最小 app:只挂 TraceIdMiddleware + 错误处理,避免拉起完整 Ginkgo 服务。"""
    app = FastAPI()
    app.add_middleware(TraceIdMiddleware)
    app.exception_handler(Exception)(global_error_handler)
    app.exception_handler(HTTPException)(global_error_handler)

    @app.get("/probe")
    async def probe():
        # 端点内读 GLOG contextvars,验证 src 层贯穿
        from ginkgo.libs import GLOG
        return {"trace_id": GLOG.get_trace_id()}

    @app.get("/boom")
    async def boom():
        raise HTTPException(status_code=400, detail="test error")

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
