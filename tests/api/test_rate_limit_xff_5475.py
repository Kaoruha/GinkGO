# Issue: #5475
# Upstream: middleware.rate_limit (RateLimitMiddleware.get_client_ip)
# Role: rate limiter X-Forwarded-For 信任校验测试——仅可信代理直连才采信 XFF

"""
rate limiter X-Forwarded-For 信任校验测试 (#5475)。

#5475 根因：middleware/rate_limit.py get_client_ip 无条件信任 X-Forwarded-For /
X-Real-IP 头，不校验 request.client.host（TCP 直连 IP）是否可信反向代理。
攻击者轮换伪造 XFF 头绕过限流（每伪造 IP 独立配额）。

修复：__init__ 加 trusted_proxies 参数（默认从 TRUSTED_PROXIES 环境变量读，
逗号分隔）。get_client_ip 仅当直连 IP ∈ trusted_proxies 才采信 XFF/X-Real-IP，
否则用直连 IP（fail-closed，不可伪造）。
"""

from types import SimpleNamespace
from unittest.mock import MagicMock


def _make_request(xff=None, x_real_ip=None, client_host=None):
    """构造 Request mock：headers + client.host（TCP 直连 IP）。"""
    headers = {}
    if xff is not None:
        headers["X-Forwarded-For"] = xff
    if x_real_ip is not None:
        headers["X-Real-IP"] = x_real_ip
    client = SimpleNamespace(host=client_host) if client_host else None
    return SimpleNamespace(headers=headers, client=client)


def _make_middleware(trusted_proxies=None):
    """构造 RateLimitMiddleware 实例（app 用 mock，不触发 dispatch）。"""
    from middleware.rate_limit import RateLimitMiddleware

    return RateLimitMiddleware(app=MagicMock(), trusted_proxies=trusted_proxies)


class TestGetClientIpXffTrust:
    """#5475: get_client_ip 仅在直连来自可信代理时才采信 XFF。"""

    def test_direct_ip_used_when_no_trusted_proxies(self, api_modules):
        """无可信代理（默认空）→ XFF 被忽略，用直连 IP（fail-closed）。"""
        m = _make_middleware(trusted_proxies=set())
        req = _make_request(xff="1.2.3.4", client_host="10.0.0.5")
        assert m.get_client_ip(req) == "10.0.0.5"

    def test_xff_trusted_when_from_trusted_proxy(self, api_modules):
        """直连来自可信代理 → XFF 被采信（取最左客户端 IP）。"""
        m = _make_middleware(trusted_proxies={"10.0.0.1"})
        req = _make_request(xff="203.0.113.5", client_host="10.0.0.1")
        assert m.get_client_ip(req) == "203.0.113.5"

    def test_xff_ignored_when_from_untrusted(self, api_modules):
        """直连非可信代理 → XFF 被忽略，用直连 IP（防伪造绕过）。"""
        m = _make_middleware(trusted_proxies={"10.0.0.1"})
        req = _make_request(xff="1.2.3.4", client_host="203.0.113.9")
        assert m.get_client_ip(req) == "203.0.113.9"

    def test_x_real_ip_trusted_when_from_trusted_proxy(self, api_modules):
        """直连可信代理 + 无 XFF 有 X-Real-IP → 采信 X-Real-IP。"""
        m = _make_middleware(trusted_proxies={"10.0.0.1"})
        req = _make_request(x_real_ip="203.0.113.7", client_host="10.0.0.1")
        assert m.get_client_ip(req) == "203.0.113.7"

    def test_unknown_when_no_client(self, api_modules):
        """无 client（无直连信息）→ 'unknown'。"""
        m = _make_middleware(trusted_proxies=set())
        req = _make_request(xff="1.2.3.4", client_host=None)
        assert m.get_client_ip(req) == "unknown"

    def test_xff_first_ip_taken_from_chain(self, api_modules):
        """XFF 多跳链 'client, proxy1' → 取最左（真实客户端）。"""
        m = _make_middleware(trusted_proxies={"10.0.0.1"})
        req = _make_request(xff="203.0.113.5, 10.0.0.2", client_host="10.0.0.1")
        assert m.get_client_ip(req) == "203.0.113.5"


class TestLoadTrustedProxies:
    """#5475: TRUSTED_PROXIES 环境变量解析。"""

    def test_parses_comma_separated_env(self, api_modules, monkeypatch):
        """逗号分隔的 env → set（去空白、去空段）。"""
        monkeypatch.setenv("TRUSTED_PROXIES", "10.0.0.1, 10.0.0.2 ,10.0.0.3")
        from middleware.rate_limit import _load_trusted_proxies

        assert _load_trusted_proxies() == {"10.0.0.1", "10.0.0.2", "10.0.0.3"}

    def test_empty_env_returns_empty_set(self, api_modules, monkeypatch):
        """env 未设/空 → 空 set（fail-closed）。"""
        monkeypatch.delenv("TRUSTED_PROXIES", raising=False)
        from middleware.rate_limit import _load_trusted_proxies

        assert _load_trusted_proxies() == set()


if __name__ == "__main__":
    import pytest

    pytest.main([__file__, "-v"])
