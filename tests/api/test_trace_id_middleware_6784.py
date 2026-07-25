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


# ---------------------------------------------------------------------------
# #6788 review: 中间件异常路径回归守护
#
# 缺陷：内层中间件(如 JWTAuthMiddleware 401)抛 HTTPException 时,异常逃逸 TraceIdMiddleware
# 的 with 块 → contextvar reset + 响应头写入行被跳过;global_error_handler 由 ServerErrorMiddleware
# 在 contextvar 作用域之外触发,trace_id 二次生成且日志显示 "-"。修复靠 request.state.trace_id
# (随 scope 存活、跨 unwind)作跨层通道,handler 补头 + 临时复位 contextvar。
#
# 用忠实最小栈复现(内层 raise 中间件 + TraceId 最外层 + 同 main.py 的 handler 注册),
# 因真实 api.main 的 lifespan 会 connection_manager.start() 拉起 DB,TestClient 集成测试不稳;
# 本最小栈与 main.py 中间件栈序+exception_handler 注册完全等价,足以在 CI 抓回归。
# ---------------------------------------------------------------------------


def _build_raising_stack(api_modules, raiser):
    """复刻 main.py 栈序:内层 raising 中间件 + TraceIdMiddleware 最外层 + 全局 handler。"""
    from fastapi import FastAPI, HTTPException
    from starlette.middleware.base import BaseHTTPMiddleware
    from middleware.trace_id import TraceIdMiddleware
    from middleware.error_handler import global_error_handler

    app = FastAPI()
    app.add_middleware(raiser)                          # 内层(模拟 JWT)
    app.add_middleware(TraceIdMiddleware)              # 最后注册 = 栈顶最外层(同 main.py)
    app.exception_handler(Exception)(global_error_handler)
    app.exception_handler(HTTPException)(global_error_handler)
    return app


def test_middleware_raised_exception_keeps_header_and_trace_id(api_modules):
    """内层中间件 raise HTTPException(401) → X-Trace-Id 头不丢、body trace_id 不脱钩。

    回归 #6788 问题 1:修复前 header=None、body trace_id 新生成、日志 trace_id="-"。
    """
    from fastapi import HTTPException
    from fastapi.testclient import TestClient
    from starlette.middleware.base import BaseHTTPMiddleware

    class JWTLikeMiddleware(BaseHTTPMiddleware):
        async def dispatch(self, request, call_next):
            raise HTTPException(status_code=401, detail="Missing authentication token")

    app = _build_raising_stack(api_modules, JWTLikeMiddleware)
    client = TestClient(app, raise_server_exceptions=False)

    resp = client.get("/anything")  # 任意路径,内层中间件无条件 raise
    assert resp.status_code == 401
    header_tid = resp.headers.get("x-trace-id")
    assert header_tid is not None, "中间件异常路径 X-Trace-Id 头丢失 (#6788 问题 1)"
    body_tid = resp.json()["trace_id"]
    assert body_tid == header_tid, (
        f"body trace_id({body_tid})与响应头({header_tid})脱钩 — 应复用同一 trace_id"
    )


def test_middleware_raised_exception_passes_through_client_trace_id(api_modules):
    """中间件异常路径下,入站 X-Trace-Id 仍正确透传到响应头/body。"""
    from fastapi import HTTPException
    from fastapi.testclient import TestClient
    from starlette.middleware.base import BaseHTTPMiddleware

    class JWTLikeMiddleware(BaseHTTPMiddleware):
        async def dispatch(self, request, call_next):
            raise HTTPException(status_code=401, detail="Invalid token")

    app = _build_raising_stack(api_modules, JWTLikeMiddleware)
    client = TestClient(app, raise_server_exceptions=False)

    fixed = "1122334455667788"
    resp = client.get("/anything", headers={"X-Trace-Id": fixed})
    assert resp.status_code == 401
    assert resp.headers.get("x-trace-id") == fixed, "异常路径未透传入站 trace_id"
    assert resp.json()["trace_id"] == fixed


def test_middleware_raised_exception_log_carries_trace_id(api_modules):
    """中间件异常路径下,global_error_handler 的错误日志携带请求 trace_id(非 "-")。

    回归 #6788:修复前 contextvar 已 reset,handler 日志输出 trace_id="-"。
    """
    import io
    import logging
    from fastapi import HTTPException
    from fastapi.testclient import TestClient
    from starlette.middleware.base import BaseHTTPMiddleware

    class JWTLikeMiddleware(BaseHTTPMiddleware):
        async def dispatch(self, request, call_next):
            raise HTTPException(status_code=401, detail="Missing authentication token")

    app = _build_raising_stack(api_modules, JWTLikeMiddleware)

    stream = io.StringIO()
    h = logging.StreamHandler(stream)
    h.setFormatter(logging.Formatter("%(trace_id)s|%(message)s"))

    from core.logging import logger
    logger.addHandler(h)
    try:
        client = TestClient(app, raise_server_exceptions=False)
        fixed = "9988776655443322"
        client.get("/anything", headers={"X-Trace-Id": fixed})
    finally:
        logger.removeHandler(h)

    out = stream.getvalue()
    assert "Missing authentication token" in out
    assert fixed in out, (
        f"中间件异常路径错误日志 trace_id 未对齐请求值(期望含 {fixed}):\n{out}"
    )


def test_middleware_raised_unhandled_exception_returns_500_with_trace_id(api_modules):
    """内层中间件抛非 HTTPException → 500 响应仍带 X-Trace-Id 头 + 一致 trace_id。"""
    from fastapi.testclient import TestClient
    from starlette.middleware.base import BaseHTTPMiddleware

    class BombMiddleware(BaseHTTPMiddleware):
        async def dispatch(self, request, call_next):
            raise RuntimeError("boom from middleware")

    app = _build_raising_stack(api_modules, BombMiddleware)
    client = TestClient(app, raise_server_exceptions=False)

    resp = client.get("/anything")
    assert resp.status_code == 500
    header_tid = resp.headers.get("x-trace-id")
    assert header_tid is not None, "500 异常路径 X-Trace-Id 头丢失"
    assert resp.json()["trace_id"] == header_tid

