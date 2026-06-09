# Issue: #5899
# Upstream: api.api.auth, api.middleware.auth
# Downstream: pytest
# Role: /auth/verify 端点行为测试

"""
/auth/verify 端点测试 — #5899

验证：
- 无 token → valid=False
- 有效 token → valid=True + 用户信息（is_admin 从 DB）
- 无效/黑名单 token → valid=False
"""

import pytest
from unittest.mock import MagicMock, patch
from types import SimpleNamespace
from datetime import datetime, timedelta

pytestmark = pytest.mark.unit


def _make_token(payload: dict) -> str:
    from jose import jwt
    from core.config import settings
    return jwt.encode(payload, settings.SECRET_KEY, algorithm="HS256")


def _default_payload(user_uuid="user-001", username="testuser",
                     is_admin=False, cred_uuid="cred-001"):
    return {
        "user_uuid": user_uuid,
        "credential_uuid": cred_uuid,
        "username": username,
        "is_admin": is_admin,
        "exp": datetime.utcnow() + timedelta(hours=1),
    }


def _mock_request(headers=None, query_params=None):
    """模拟 FastAPI Request"""
    state = SimpleNamespace()
    req = MagicMock()
    req.state = state
    req.headers = headers or {}
    req.query_params = query_params or {}
    return req


# ============================================================
# Test 1: 无 token → valid=False
# ============================================================

class TestVerifyNoToken:
    """#5899: 无 token 时 verify 返回 valid=False"""

    @pytest.mark.asyncio
    async def test_no_auth_header_returns_invalid(self):
        from api.auth import verify_token_endpoint
        req = _mock_request(headers={})
        result = await verify_token_endpoint(req)
        assert result["data"]["valid"] is False
        assert result["data"]["user_uuid"] is None
        assert result["data"]["username"] is None
        assert result["data"]["is_admin"] is False

    @pytest.mark.asyncio
    async def test_malformed_auth_header_returns_invalid(self):
        from api.auth import verify_token_endpoint
        req = _mock_request(headers={"Authorization": "NotBearer abc"})
        result = await verify_token_endpoint(req)
        assert result["data"]["valid"] is False


# ============================================================
# Test 2: 有效 token → valid=True + 用户信息
# ============================================================

class TestVerifyValidToken:
    """#5899: 有效 token 返回用户信息"""

    @pytest.mark.asyncio
    async def test_valid_token_returns_user_info(self):
        """有效 token → valid=True, 返回 user_uuid + username"""
        from api.auth import verify_token_endpoint
        token = _make_token(_default_payload(user_uuid="u-1", username="alice"))
        req = _mock_request(headers={"Authorization": f"Bearer {token}"})
        result = await verify_token_endpoint(req)
        assert result["data"]["valid"] is True
        assert result["data"]["user_uuid"] == "u-1"
        assert result["data"]["username"] == "alice"

    @pytest.mark.asyncio
    async def test_is_admin_from_db_not_jwt(self):
        """#5899: is_admin 应从 DB 查询，不是 JWT 中的值"""
        from api.auth import verify_token_endpoint

        # JWT 中 is_admin=False
        payload = _default_payload(user_uuid="u-admin", username="admin", is_admin=False)
        token = _make_token(payload)

        # mock get_user_service → credential.is_admin=True（DB 说是 admin）
        mock_cred = MagicMock()
        mock_cred.is_admin = True
        mock_svc = MagicMock()
        mock_svc.get_credential.return_value = mock_cred

        with patch("api.auth.get_user_service", return_value=mock_svc):
            req = _mock_request(headers={"Authorization": f"Bearer {token}"})
            result = await verify_token_endpoint(req)

        # is_admin 应来自 DB (True)，而非 JWT (False)
        assert result["data"]["is_admin"] is True


# ============================================================
# Test 3: 无效/黑名单 token → valid=False
# ============================================================

class TestVerifyInvalidToken:
    """#5899: 无效/黑名单 token 返回 valid=False"""

    @pytest.mark.asyncio
    async def test_invalid_token_returns_invalid(self):
        """伪造 token → valid=False"""
        from api.auth import verify_token_endpoint
        req = _mock_request(headers={"Authorization": "Bearer this.is.not.valid"})
        result = await verify_token_endpoint(req)
        assert result["data"]["valid"] is False
        assert result["data"]["user_uuid"] is None

    @pytest.mark.asyncio
    async def test_blacklisted_token_returns_invalid(self):
        """#5802: 黑名单中的 token → valid=False"""
        from api.auth import verify_token_endpoint
        from middleware.auth import token_blacklist

        payload = _default_payload()
        payload["jti"] = "jti-to-be-blacklisted"
        token = _make_token(payload)

        token_blacklist._store.clear()
        token_blacklist.add("jti-to-be-blacklisted")

        req = _mock_request(headers={"Authorization": f"Bearer {token}"})
        result = await verify_token_endpoint(req)
        assert result["data"]["valid"] is False

        # cleanup
        token_blacklist._store.clear()


# ============================================================
# Test 4: DB 异常时 fail-closed（is_admin=False）
# ============================================================

class TestVerifyDBFailure:
    """#5899: DB 查询异常时 is_admin 必须 fail-closed，不回退 JWT"""

    @pytest.mark.asyncio
    async def test_db_exception_is_admin_false(self):
        """DB 抛异常时 is_admin=False，不回退到 JWT 中的 is_admin=True"""
        from api.auth import verify_token_endpoint

        # JWT 中 is_admin=True（伪造的）
        payload = _default_payload(user_uuid="u-fake-admin", username="attacker", is_admin=True)
        token = _make_token(payload)

        # mock DB 查询抛异常
        mock_svc = MagicMock()
        mock_svc.get_credential.side_effect = Exception("connection pool exhausted")

        with patch("api.auth.get_user_service", return_value=mock_svc):
            req = _mock_request(headers={"Authorization": f"Bearer {token}"})
            result = await verify_token_endpoint(req)

        # fail-closed: token 有效但 is_admin 必须为 False
        assert result["data"]["valid"] is True
        assert result["data"]["is_admin"] is False
