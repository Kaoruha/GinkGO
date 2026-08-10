"""WebSocket token 提取共用 helper（ADR-044 §5）。

Electron 双形态：
- 主进程注入 `Authorization: Bearer <token>` header（生产形态，避免 token 落入 URL 日志/历史）
- 浏览器形态保留 `?token=xxx` query param（WebSocket 浏览器原生无法设置 header）

header 优先，query 兜底；两者都无由 handler 自行 close(1008)。
"""

from typing import Optional

from fastapi import WebSocket


def _extract_ws_token(websocket: WebSocket) -> Optional[str]:
    """ADR-044 §5: header 优先（Electron 主进程注入），query 兼容（浏览器）。

    scheme 大小写不敏感（HTTP 规范：RFC 7235 §2.1 scheme is case-insensitive），
    比 `JWTAuthMiddleware._extract_token`（case-sensitive）更宽容——ws 入口更严格
    的校验由 verify_token 承担。空 Bearer（`Bearer ` 后无字符）视为无 header，
    继续 fallback query param，避免空串误判为 token。浏览器 WebSocket API 无法
    设置 header，故 ws 路径上保留 query param fallback。
    """
    auth = websocket.headers.get("authorization")
    if auth and auth.lower().startswith("bearer "):
        tok = auth[7:].strip()
        if tok:
            return tok
        # 空 Bearer：fall through 到 query param（不返回空串）
    return websocket.query_params.get("token")
