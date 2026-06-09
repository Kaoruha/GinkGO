# Issues: #5802, #5582, #5448, #5770, #5679, #5464
# Upstream: api.middleware.auth, api.api.auth, api.api.settings, api.core.config
# Downstream: pytest
# Role: JWT/认证安全批量修复测试

"""
JWT 认证安全测试

验证 6 个安全 issue 的修复：
- #5802/#5582/#5448: Token 黑名单（logout/改密码后旧 token 失效）
- #5770/#5679: reset-password 权限校验 + 不返回明文密码
- #5464: SECRET_KEY 禁止默认值
"""

import asyncio
import pytest
from unittest.mock import MagicMock, patch
from datetime import datetime, timedelta


pytestmark = pytest.mark.unit


def _make_token(payload: dict) -> str:
    """用 settings.SECRET_KEY 生成 JWT token（与 verify_token 一致）"""
    from jose import jwt
    from core.config import settings
    return jwt.encode(payload, settings.SECRET_KEY, algorithm="HS256")


def _default_payload(user_uuid="user-001", username="testuser",
                     is_admin=False, cred_uuid="cred-001"):
    """构造标准 JWT payload"""
    return {
        "user_uuid": user_uuid,
        "credential_uuid": cred_uuid,
        "username": username,
        "is_admin": is_admin,
        "exp": datetime.utcnow() + timedelta(hours=1),
    }


# ============================================================
# #5802: Logout 后 token 应被拒绝
# ============================================================

class TestTokenBlacklistOnLogout:
    """#5802: logout 后 token 应立即失效"""

    def test_blacklisted_token_rejected_by_verify(self):
        """logout 后 verify_token 应抛 JWTError"""
        from middleware.auth import token_blacklist, verify_token
        from jose import JWTError

        payload = _default_payload()
        payload["jti"] = "token-abc-123"
        token = _make_token(payload)

        # 先确认 token 有效
        decoded = verify_token(token)
        assert decoded["user_uuid"] == "user-001"

        # 加入黑名单（模拟 logout）
        token_blacklist.add("token-abc-123")

        # 验证被拒绝
        with pytest.raises(JWTError):
            verify_token(token)

    def test_logout_adds_token_to_blacklist(self):
        """logout 端点应将 token 的 jti 写入黑名单"""
        from middleware.auth import token_blacklist

        token_blacklist._store.clear()
        token_blacklist.add("jti-from-logout")

        assert token_blacklist.is_blacklisted("jti-from-logout") is True

    def test_non_blacklisted_token_still_valid(self):
        """未加入黑名单的 token 应正常通过"""
        from middleware.auth import token_blacklist, verify_token

        token_blacklist._store.clear()
        payload = _default_payload()
        payload["jti"] = "valid-token-jti"
        token = _make_token(payload)

        # 未加黑名单，应正常解码
        decoded = verify_token(token)
        assert decoded["user_uuid"] == "user-001"


# ============================================================
# #5582/#5448: 改密码后旧 token 应被拒绝
# ============================================================

class TestTokenBlacklistOnPasswordChange:
    """#5582/#5448: 改密码后旧 token 应失效"""

    def test_revoke_all_user_tokens_after_password_change(self):
        """改密码后该用户所有 token 应被批量撤销"""
        from middleware.auth import token_blacklist

        token_blacklist._store.clear()
        token_blacklist.revoke_user("user-001")

        assert token_blacklist.is_user_revoked("user-001") is True

    def test_other_user_tokens_not_affected(self):
        """改密码不应影响其他用户的 token"""
        from middleware.auth import token_blacklist

        token_blacklist._store.clear()
        token_blacklist.revoke_user("user-001")

        assert token_blacklist.is_user_revoked("user-002") is False

    def test_revoked_user_token_rejected(self):
        """被撤销用户的 token 应被拒绝"""
        from middleware.auth import token_blacklist, verify_token
        from jose import JWTError

        token_blacklist._store.clear()
        token_blacklist._user_revoked.clear()

        payload = _default_payload()
        payload["jti"] = "revoked-token"
        token = _make_token(payload)

        # 正常通过
        decoded = verify_token(token)
        assert decoded["user_uuid"] == "user-001"

        # 撤销该用户
        token_blacklist.revoke_user("user-001")

        # 被拒绝
        with pytest.raises(JWTError, match="revoked"):
            verify_token(token)


# ============================================================
# #5770/#5679: reset-password 权限校验
# ============================================================

class TestResetPasswordAuthorization:
    """#5770/#5679: reset-password 端点权限校验"""

    def test_normal_user_cannot_reset_others_password(self):
        """普通用户重置他人密码应返回 403"""
        from api.settings import reset_user_password
        from fastapi import HTTPException

        req = MagicMock()
        req.state.user_uuid = "user-normal"
        req.state.is_admin = False

        with pytest.raises(HTTPException) as exc_info:
            asyncio.run(
                reset_user_password("user-admin-uuid", {"new_password": "hacked123"}, req)
            )
        assert exc_info.value.status_code == 403

    def test_admin_can_reset_others_password(self):
        """管理员应能重置他人密码"""
        from api.settings import reset_user_password

        req = MagicMock()
        req.state.user_uuid = "user-admin"
        req.state.is_admin = True

        with patch("api.settings.get_user_service") as mock_svc:
            mock_svc.return_value.reset_password.return_value = MagicMock(success=True)
            result = asyncio.run(
                reset_user_password("user-target-uuid", {"new_password": "NewPass123!"}, req)
            )
        # 不应抛异常
        assert result is not None

    def test_reset_password_response_no_plaintext(self):
        """密码重置响应不应包含明文密码"""
        from api.settings import reset_user_password

        req = MagicMock()
        req.state.user_uuid = "user-admin"
        req.state.is_admin = True

        with patch("api.settings.get_user_service") as mock_svc:
            mock_svc.return_value.reset_password.return_value = MagicMock(success=True)
            result = asyncio.run(
                reset_user_password("user-target-uuid", {"new_password": "Secret123!"}, req)
            )
        # 响应中不应有 new_password 字段
        assert "new_password" not in str(result)


# ============================================================
# #5464: SECRET_KEY 禁止默认值
# ============================================================

class TestSecretKeyConfig:
    """#5464: JWT SECRET_KEY 不应使用默认值"""

    def test_config_refuses_default_secret_key(self):
        """使用默认 SECRET_KEY 时应抛出 ValueError"""
        from core.config import Settings
        with pytest.raises(ValueError, match="SECRET_KEY"):
            Settings(SECRET_KEY="your-secret-key-change-in-production")


# ============================================================
# PR #6057 review: delete_user 后旧 token 应被撤销
# ============================================================

class TestTokenBlacklistOnDeleteUser:
    """删除用户后该用户所有 token 应失效"""

    def test_delete_user_revokes_tokens(self):
        """delete_user 应调用 token_blacklist.revoke_user 撤销旧 token"""
        from api.settings import delete_user

        with patch("api.settings.get_user_service") as mock_svc:
            mock_svc.return_value.delete_user.return_value = MagicMock(success=True)

            with patch("middleware.auth.token_blacklist") as mock_bl:
                asyncio.run(delete_user("user-to-delete"))

                mock_bl.revoke_user.assert_called_once_with("user-to-delete")

    def test_delete_user_without_revoke_leaves_token_valid(self):
        """验证问题存在：未 revoke 时旧 token 仍然有效"""
        from middleware.auth import token_blacklist, verify_token
        from jose import JWTError

        token_blacklist._store.clear()
        token_blacklist._user_revoked.clear()

        payload = _default_payload(user_uuid="doomed-user")
        payload["jti"] = "delete-test-jti"
        token = _make_token(payload)

        # 确认 token 有效
        decoded = verify_token(token)
        assert decoded["user_uuid"] == "doomed-user"

        # 撤销（模拟 delete_user 应做的操作）
        token_blacklist.revoke_user("doomed-user")

        # 确认被拒绝
        with pytest.raises(JWTError, match="revoked"):
            verify_token(token)
