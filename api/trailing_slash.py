"""HTTP middleware: strip trailing slash from request path in-place.

配合 FastAPI(redirect_slashes=False) 使用。路由统一注册无 slash 形式（列表
端点 ``@router.get("")``），本 middleware 把带 trailing slash 的请求路径
内部 rewrite（改 ``request.scope["path"]``），在路由匹配前生效——零 307
重定向，避免 POST 丢 Authorization header（#5389）。
"""
from typing import Awaitable, Callable

from starlette.requests import Request
from starlette.responses import Response


async def strip_trailing_slash(
    request: Request, call_next: Callable[[Request], Awaitable[Response]]
) -> Response:
    path = request.url.path
    # 根 "/" 与空路径不处理（docs / redoc / openapi.json 等根路由）
    if len(path) > 1 and path.endswith("/"):
        stripped = path.rstrip("/")
        request.scope["path"] = stripped
        # raw_path 同步（部分中间件 / access log 读 raw_path）
        request.scope["raw_path"] = stripped.encode("utf-8")
    return await call_next(request)
