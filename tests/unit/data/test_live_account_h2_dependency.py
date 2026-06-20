"""
#5796 回归保护: OKX 账户余额查询依赖 h2

python-okx 声明依赖 httpx[http2]>=0.24.0, 其底层 HTTP/2 支持需要 h2 包。
h2 缺失时, OKX balance 查询报错:
    "Using http2=True, but the 'h2' package is not installed"

这些测试锁定行为契约: OKX 经由的 httpx HTTP/2 路径必须可用。
若未来依赖被误删, 测试会在创建 http2 client 时失败。
"""

import pytest


def test_httpx_http2_client_constructible():
    """httpx HTTP/2 client 必须可创建 (需 h2)。

    python-okx 内部以 http2=True 构造 httpx.Client; h2 缺失会在此抛
    ImportError。这是 OKX balance/validate 链路真正经过的路径。
    """
    import httpx

    client = httpx.Client(http2=True)  # h2 缺失 → ImportError
    try:
        assert client is not None
    finally:
        client.close()


def test_h2_package_present():
    """h2 包本身可导入 (httpx http2 支持的直接依赖)。"""
    import h2  # noqa: F401  # 行为: 可导入即依赖就位

    assert h2 is not None
