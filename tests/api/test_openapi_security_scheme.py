# Issue: #5714
# Upstream: api.openapi_schema, api.middleware.auth
# Downstream: pytest
# Role: OpenAPI spec securitySchemes 行为测试

"""
OpenAPI spec securitySchemes 测试 — #5714

验证 build_openapi_schema 为 FastAPI app 注入 Bearer JWT securityScheme，
受保护端点显式标注 security，public 端点（JWTAuthMiddleware.PUBLIC_PATHS）
不标注。鉴权仍由中间件运行时负责，此处只补 spec 契约。
"""
import pytest

pytestmark = pytest.mark.unit


def _make_app_with_routes():
    """构造最小 FastAPI app（含 public + protected 路由），避免触发 containers。"""
    from fastapi import FastAPI

    app = FastAPI(title="test", version="0.0.1")

    @app.get("/health")
    def health():
        return {"ok": 1}

    @app.get("/api/v1/auth/login")
    def login():
        return {}

    @app.get("/api/v1/portfolios")
    def list_portfolios():
        return []

    return app


def test_security_schemes_defines_bearer_jwt(api_modules):
    """securitySchemes 含 bearerAuth: http/bearer/JWT。"""
    from openapi_schema import build_openapi_schema

    app = _make_app_with_routes()
    schema = build_openapi_schema(app)
    schemes = schema["components"]["securitySchemes"]
    assert "bearerAuth" in schemes
    bearer = schemes["bearerAuth"]
    assert bearer["type"] == "http"
    assert bearer["scheme"] == "bearer"
    assert bearer["bearerFormat"] == "JWT"


def test_protected_endpoint_has_bearer_security(api_modules):
    """受保护端点标注 security: [{bearerAuth: []}]。"""
    from openapi_schema import build_openapi_schema

    app = _make_app_with_routes()
    schema = build_openapi_schema(app)
    op = schema["paths"]["/api/v1/portfolios"]["get"]
    assert op.get("security") == [{"bearerAuth": []}]


def test_public_endpoints_have_no_security(api_modules):
    """public 端点（PUBLIC_PATHS）不标注 security。"""
    from openapi_schema import build_openapi_schema

    app = _make_app_with_routes()
    schema = build_openapi_schema(app)
    for public_path in ("/health", "/api/v1/auth/login"):
        op = schema["paths"][public_path]["get"]
        assert "security" not in op, f"{public_path} 应为 public 不带 security"


def test_schema_cached_on_app(api_modules):
    """重复调用复用缓存（FastAPI openapi_schema 惯例）。"""
    from openapi_schema import build_openapi_schema

    app = _make_app_with_routes()
    s1 = build_openapi_schema(app)
    s2 = build_openapi_schema(app)
    assert s1 is s2
