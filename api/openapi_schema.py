"""
自定义 OpenAPI schema 生成 — #5714

为 FastAPI app 注入 Bearer JWT securityScheme，受保护端点显式标注 security。

背景：鉴权由 JWTAuthMiddleware（BaseHTTPMiddleware）实现，对 FastAPI 的 schema
生成器不可见（get_openapi 只扫描路由 Depends/Security，不扫描 add_middleware）。
故此处集中补全 spec 的 auth 契约，运行时鉴权行为仍由中间件负责，二者复用
同一份 PUBLIC_PATHS 真相源避免漂移。
"""
from fastapi import FastAPI
from fastapi.openapi.utils import get_openapi

from middleware.auth import JWTAuthMiddleware

BEARER_SCHEME_NAME = "bearerAuth"


def build_openapi_schema(app: FastAPI) -> dict:
    """构造含 securitySchemes 的 OpenAPI schema。

    - 注入 bearerAuth (http/bearer/JWT)
    - 受保护端点（path 不在 JWTAuthMiddleware.PUBLIC_PATHS）标注 security
    - public 端点不标注（Swagger UI 显示为无需认证）
    - 结果缓存于 app.openapi_schema（FastAPI 惯例，重复调用返回同一对象）
    """
    if app.openapi_schema:
        return app.openapi_schema

    schema = get_openapi(
        title=app.title,
        version=app.version,
        openapi_version=app.openapi_version,
        description=app.description,
        routes=app.routes,
    )

    schema.setdefault("components", {}).setdefault("securitySchemes", {})[BEARER_SCHEME_NAME] = {
        "type": "http",
        "scheme": "bearer",
        "bearerFormat": "JWT",
    }

    public_paths = JWTAuthMiddleware.PUBLIC_PATHS
    for path, methods in schema.get("paths", {}).items():
        for _method, op in methods.items():
            if not isinstance(op, dict):
                continue
            if path in public_paths:
                continue
            op["security"] = [{BEARER_SCHEME_NAME: []}]

    app.openapi_schema = schema
    return schema
