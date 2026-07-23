# Issue: #5899
# Upstream: api.api.auth, api.middleware.auth
# Downstream: pytest
# Role: /auth/refresh 端点 #5899 不变量测试

"""
/auth/refresh 端点测试 — #5899

验证 refresh 续签同样遵守 #5899 的 DB-实查不变量（与 /auth/verify、/auth/me 对齐）：
- 被禁用用户 → 401（不发新 token）
- 被降权管理员 → 新 token 的 is_admin 来自 DB 而非旧 payload
- DB 异常 → fail-closed（新 token is_admin=False，不传播旧 payload）
- 凭据/用户已删除 → 401
- payload 缺 user_uuid → 401
- 正常活跃用户 → 200 + 新 token + DB-fresh is_admin
"""

import pytest
from unittest.mock import MagicMock, patch
from types import SimpleNamespace
from datetime import datetime, timedelta
from fastapi import HTTPException

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


def _mock_request(headers=None):
    """模拟 FastAPI Request"""
    state = SimpleNamespace()
    req = MagicMock()
    req.state = state
    req.headers = headers or {}
    return req


def _patch_blacklist(revoked=False):
    """隔离 blacklist 状态：check_revoked 受控返回（refresh 的黑名单行为正交于 #5899 修复）。"""
    mock_bl = MagicMock()
    mock_bl.check_revoked.return_value = revoked
    return patch("api.auth.token_blacklist", mock_bl)


# ============================================================
# Test 1: 被禁用用户 → 401（核心回归用例）
# ============================================================

class TestRefreshDisabledUser:
    """#5899: is_active=False 的用户不得 refresh（不发新 token）"""

    @pytest.mark.asyncio
    async def test_disabled_user_denied(self):
        from api.auth import refresh_token

        # 旧 token 仍带 is_admin=True（禁用前签发）
        payload = _default_payload(user_uuid="u-disabled", username="disabled", is_admin=True)
        token = _make_token(payload)

        mock_cred = MagicMock()
        mock_cred.is_active = False
        mock_cred.is_admin = True
        mock_svc = MagicMock()
        mock_svc.get_credential.return_value = mock_cred

        with _patch_blacklist(), patch("api.auth.get_user_service", return_value=mock_svc):
            req = _mock_request(headers={"Authorization": f"Bearer {token}"})
            with pytest.raises(HTTPException) as exc:
                await refresh_token(req)

        assert exc.value.status_code == 401
        assert "disabled" in exc.value.detail.lower()


# ============================================================
# Test 2: 被降权管理员 → 新 token is_admin 来自 DB（非旧 payload）
# ============================================================

class TestRefreshDemotedAdmin:
    """#5899: is_admin 从 DB 实查，不信任旧 payload"""

    @pytest.mark.asyncio
    async def test_is_admin_from_db_not_payload(self):
        from api.auth import refresh_token

        # 旧 token is_admin=True（降权前签发），DB 现在说 False
        payload = _default_payload(user_uuid="u-demoted", username="demoted", is_admin=True)
        token = _make_token(payload)

        mock_cred = MagicMock()
        mock_cred.is_active = True
        mock_cred.is_admin = False  # DB: 已降权
        mock_svc = MagicMock()
        mock_svc.get_credential.return_value = mock_cred

        with _patch_blacklist(), patch("api.auth.get_user_service", return_value=mock_svc):
            req = _mock_request(headers={"Authorization": f"Bearer {token}"})
            result = await refresh_token(req)

        # 新 token 的 is_admin 必须是 DB 的 False，不是 payload 的 True
        assert result["data"]["user"]["is_admin"] is False


# ============================================================
# Test 3: DB 异常 → fail-closed（新 token is_admin=False）
# ============================================================

class TestRefreshDBFailure:
    """#5899: DB 查询异常时新 token is_admin 必须 fail-closed，不回退旧 payload"""

    @pytest.mark.asyncio
    async def test_db_exception_is_admin_false(self):
        from api.auth import refresh_token

        # 旧 token is_admin=True（伪造），DB 抛异常
        payload = _default_payload(user_uuid="u-fake", username="attacker", is_admin=True)
        token = _make_token(payload)

        mock_svc = MagicMock()
        mock_svc.get_credential.side_effect = Exception("connection pool exhausted")

        with _patch_blacklist(), patch("api.auth.get_user_service", return_value=mock_svc):
            req = _mock_request(headers={"Authorization": f"Bearer {token}"})
            result = await refresh_token(req)

        # fail-closed: 仍发新 token（不锁死用户），但 is_admin 必须为 False
        assert result["data"]["token"]
        assert result["data"]["user"]["is_admin"] is False


# ============================================================
# Test 4: 凭据/用户已删除 → 401
# ============================================================

class TestRefreshCredentialGone:
    """#5899: 凭据/用户已删除 → 不发新 token"""

    @pytest.mark.asyncio
    async def test_credential_none_denied(self):
        from api.auth import refresh_token

        payload = _default_payload(user_uuid="u-gone", username="gone")
        token = _make_token(payload)

        mock_svc = MagicMock()
        mock_svc.get_credential.return_value = None

        with _patch_blacklist(), patch("api.auth.get_user_service", return_value=mock_svc):
            req = _mock_request(headers={"Authorization": f"Bearer {token}"})
            with pytest.raises(HTTPException) as exc:
                await refresh_token(req)

        assert exc.value.status_code == 401


# ============================================================
# Test 5: payload 缺 user_uuid → 401
# ============================================================

class TestRefreshMissingUserUUID:
    """#5899: payload 无 user_uuid → 无法核验身份，不发新 token"""

    @pytest.mark.asyncio
    async def test_missing_user_uuid_denied(self):
        from api.auth import refresh_token

        payload = _default_payload()
        del payload["user_uuid"]
        token = _make_token(payload)

        with _patch_blacklist():
            req = _mock_request(headers={"Authorization": f"Bearer {token}"})
            with pytest.raises(HTTPException) as exc:
                await refresh_token(req)

        assert exc.value.status_code == 401


# ============================================================
# Test 6: 正常活跃用户 → 200 + 新 token + DB-fresh is_admin
# ============================================================

class TestRefreshHappyPath:
    """正常 refresh：活跃用户拿到新 token，is_admin 来自 DB"""

    @pytest.mark.asyncio
    async def test_active_user_gets_new_token(self):
        from api.auth import refresh_token

        payload = _default_payload(user_uuid="u-ok", username="ok", is_admin=False)
        token = _make_token(payload)

        mock_cred = MagicMock()
        mock_cred.is_active = True
        mock_cred.is_admin = True  # DB: 是 admin（即使旧 token 说 False）
        mock_svc = MagicMock()
        mock_svc.get_credential.return_value = mock_cred

        with _patch_blacklist(), patch("api.auth.get_user_service", return_value=mock_svc):
            req = _mock_request(headers={"Authorization": f"Bearer {token}"})
            result = await refresh_token(req)

        assert result["data"]["token"]
        assert result["data"]["user"]["is_admin"] is True
        assert result["data"]["user"]["username"] == "ok"
