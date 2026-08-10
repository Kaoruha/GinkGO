"""ADR-044 §5: WebSocket Authorization header 支持（Electron 双形态）。

覆盖:
1. header 优先于 query param（Electron 主进程注入路径）
2. 无 header 时回退 query param（浏览器兼容路径）
3. header 与 query 都无 token → handler close(1008)

复用 handler 内 verify_token（不重写校验逻辑）；本测试只验证 token 提取与握手前 close。
"""

import os

# #5464: api.core import 链触发 config.py 全局 Settings()，需合法 SECRET_KEY。
os.environ.setdefault("SECRET_KEY", "test-secret-key-for-jwt-security-tests")

import importlib

import pytest

from websocket.handlers._auth import _extract_ws_token
from websocket.handlers.portfolio_handler import PortfolioHandler


class _MockQueryParams:
    """模拟 Starlette websocket.query_params（支持 .get）"""

    def __init__(self, mapping):
        self._mapping = mapping

    def get(self, key, default=None):
        return self._mapping.get(key, default)


class _MockHeaders:
    """模拟 Starlette websocket.headers（大小写不敏感 .get）"""

    def __init__(self, mapping):
        self._mapping = {k.lower(): v for k, v in mapping.items()}

    def get(self, key, default=None):
        return self._mapping.get(key.lower(), default)


class _MockWebSocket:
    """最小 WebSocket mock：仅满足 _extract_ws_token 与 close 路径。"""

    def __init__(self, headers=None, query=None):
        self.headers = _MockHeaders(headers or {})
        self.query_params = _MockQueryParams(query or {})
        self.closed = []

    async def close(self, code=1000, reason=None):
        self.closed.append((code, reason))


# ---------- _extract_ws_token 单元测试 ----------


@pytest.mark.unit
def test_extract_token_header_takes_priority():
    """header token 优先于 query param。"""
    ws = _MockWebSocket(
        headers={"authorization": "Bearer header-token"},
        query={"token": "query-token"},
    )
    assert _extract_ws_token(ws) == "header-token"


@pytest.mark.unit
def test_extract_token_header_case_insensitive_scheme():
    """Bearer 前缀大小写不敏感（与 HTTP 规范对齐）。"""
    ws = _MockWebSocket(
        headers={"authorization": "bearer mixed-case-token"},
        query={"token": "query-token"},
    )
    assert _extract_ws_token(ws) == "mixed-case-token"


@pytest.mark.unit
def test_extract_token_fallback_to_query():
    """无 header（或非 Bearer）时回退 query param（浏览器兼容）。"""
    ws = _MockWebSocket(query={"token": "query-token"})
    assert _extract_ws_token(ws) == "query-token"


@pytest.mark.unit
def test_extract_token_no_bearer_falls_to_query():
    """header 存在但非 Bearer scheme → 不误判，回退 query。"""
    ws = _MockWebSocket(
        headers={"authorization": "Basic xyz"},
        query={"token": "query-token"},
    )
    assert _extract_ws_token(ws) == "query-token"


@pytest.mark.unit
def test_extract_token_missing_returns_none():
    """header 与 query 都无 token → None（由 handler 转 close 1008）。"""
    ws = _MockWebSocket()
    assert _extract_ws_token(ws) is None


@pytest.mark.unit
def test_extract_token_empty_bearer_falls_to_query():
    """`Bearer `（空 token）不应返回空串，应继续 fallback query 取真值。"""
    ws = _MockWebSocket(
        headers={"authorization": "Bearer "},
        query={"token": "query-token"},
    )
    # 空 Bearer → fall through → query 真值
    assert _extract_ws_token(ws) == "query-token"


# ---------- handler 集成：close(1008) 路径 ----------


@pytest.mark.asyncio
async def test_ws_missing_token_closes_1008():
    """header 和 query 都无 token → handler close(1008)。"""
    ws = _MockWebSocket()  # 无 headers / 无 query token
    await PortfolioHandler().websocket_endpoint(ws)
    assert ws.closed == [(1008, "Missing token")]


@pytest.mark.asyncio
async def test_ws_invalid_token_closes_1008(monkeypatch):
    """token 存在但 verify_token 失败 → close(1008) invalid。"""
    # 注意：websocket/handlers/__init__.py 把 portfolio_handler 重导出为实例，
    # `from websocket.handlers import portfolio_handler` 拿到的是实例不是模块。
    # 用 importlib.import_module 显式取模块对象，patch 模块级 verify_token 绑定。
    ph_mod = importlib.import_module("websocket.handlers.portfolio_handler")

    def _boom(_token):
        raise ValueError("bad token")

    monkeypatch.setattr(ph_mod, "verify_token", _boom)

    ws = _MockWebSocket(query={"token": "garbage"})
    await PortfolioHandler().websocket_endpoint(ws)
    assert ws.closed == [(1008, "Invalid or expired token")]
