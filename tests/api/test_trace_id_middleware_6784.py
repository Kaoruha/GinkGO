"""#6784: API 请求 trace_id 贯穿 GLOG 日志 (可观测层接入 1/4)。

验证 TraceIdMiddleware 行为(注入/透传/响应头/无泄漏)及 error_handler
trace_id 复用。口径 tests/api(用 api_modules fixture 延迟 import api/)。
"""
# 注意：api_modules fixture 临时把 api/ 加进 sys.path，
# 使 `from middleware.trace_id import TraceIdMiddleware` 可解析。


def test_middleware_generates_trace_id_header_when_absent(api_modules):
    """无入站 X-Trace-Id → 生成新 trace_id 并写入响应头(16 hex)。"""
    from fastapi import FastAPI
    from fastapi.testclient import TestClient
    from middleware.trace_id import TraceIdMiddleware

    app = FastAPI()
    app.add_middleware(TraceIdMiddleware)

    @app.get("/ping")
    def ping():
        return {"ok": True}

    client = TestClient(app)
    resp = client.get("/ping")
    assert resp.status_code == 200
    assert "x-trace-id" in resp.headers
    tid = resp.headers["x-trace-id"]
    assert len(tid) == 16
    int(tid, 16)  # 合法 hex


def test_middleware_passes_through_client_trace_id(api_modules):
    """入站带 X-Trace-Id → 响应头复用该值(不重新生成)。"""
    from fastapi import FastAPI
    from fastapi.testclient import TestClient
    from middleware.trace_id import TraceIdMiddleware

    app = FastAPI()
    app.add_middleware(TraceIdMiddleware)

    @app.get("/ping")
    def ping():
        return {"ok": True}

    client = TestClient(app)
    fixed = "abcdef0123456789"
    resp = client.get("/ping", headers={"X-Trace-Id": fixed})
    assert resp.headers["x-trace-id"] == fixed


def test_middleware_binds_trace_id_to_glog_contextvar(api_modules):
    """请求处理期间 GLOG contextvar 被设为绑定的 trace_id (贯穿 router/service/crud)。"""
    from fastapi import FastAPI
    from fastapi.testclient import TestClient
    from middleware.trace_id import TraceIdMiddleware

    app = FastAPI()
    app.add_middleware(TraceIdMiddleware)

    @app.get("/whoami")
    def whoami():
        from ginkgo.libs import GLOG
        return {"tid": GLOG.get_trace_id()}

    client = TestClient(app)
    fixed = "deadbeefdeadbeef"
    resp = client.get("/whoami", headers={"X-Trace-Id": fixed})
    assert resp.status_code == 200
    assert resp.json()["tid"] == fixed


def test_no_cross_request_trace_id_leakage(api_modules):
    """连续两请求各自生成 trace_id，第二请求不继承第一的残留 (contextvar 已复位)。"""
    from fastapi import FastAPI
    from fastapi.testclient import TestClient
    from middleware.trace_id import TraceIdMiddleware

    app = FastAPI()
    app.add_middleware(TraceIdMiddleware)

    @app.get("/cap")
    def cap():
        from ginkgo.libs import GLOG
        return {"tid": GLOG.get_trace_id()}

    client = TestClient(app)
    r1 = client.get("/cap")
    r2 = client.get("/cap")
    t1, t2 = r1.json()["tid"], r2.json()["tid"]
    assert t1 is not None and t2 is not None
    assert t1 != t2  # 无泄漏


def test_error_envelope_reuses_request_trace_id(api_modules):
    """错误信封 trace_id 复用请求绑定的值，不再二次生成。"""
    from fastapi import FastAPI, HTTPException
    from fastapi.testclient import TestClient
    from middleware.trace_id import TraceIdMiddleware
    from middleware.error_handler import global_error_handler

    app = FastAPI()
    app.add_middleware(TraceIdMiddleware)
    app.exception_handler(Exception)(global_error_handler)
    app.exception_handler(HTTPException)(global_error_handler)

    @app.get("/boom")
    def boom():
        raise HTTPException(status_code=404, detail="nope")

    client = TestClient(app, raise_server_exceptions=False)
    fixed = "cafecafecafecafe"
    resp = client.get("/boom", headers={"X-Trace-Id": fixed})
    assert resp.status_code == 404
    assert resp.json()["trace_id"] == fixed


def test_stdlib_logger_carries_trace_id(api_modules):
    """API 业务层 stdlib logger 输出携带请求 trace_id (TraceIdFilter 注入)。

    业务层用 `from core.logging import logger` (stdlib)，不走 GLOG structlog；
    Filter 读 GLOG contextvar 注入 record.trace_id，使 stdlib 日志也能用
    trace_id 检索。
    """
    import io
    import logging
    from fastapi import FastAPI
    from fastapi.testclient import TestClient
    from middleware.trace_id import TraceIdMiddleware

    stream = io.StringIO()
    h = logging.StreamHandler(stream)
    h.setFormatter(logging.Formatter("%(trace_id)s|%(message)s"))

    app = FastAPI()
    app.add_middleware(TraceIdMiddleware)

    @app.get("/log")
    def log():
        from core.logging import logger
        logger.addHandler(h)
        try:
            logger.info("biz-marker")
        finally:
            logger.removeHandler(h)
        return {"ok": True}

    client = TestClient(app)
    fixed = "ffeeddccbbaa9988"
    client.get("/log", headers={"X-Trace-Id": fixed})
    out = stream.getvalue()
    assert "biz-marker" in out
    assert fixed in out  # trace_id 注入 stdlib 日志输出
