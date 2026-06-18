# Issues: #5467, #5465, #5458, #5472
# Upstream: api.api.auth, api.api.settings, src.ginkgo.data.models.model_user
# Downstream: pytest
# Role: Auth/Security 批量修复测试

"""
Auth/Security 批量修复测试

覆盖 4 个 issue：
- #5458: email 解耦 — 注册/更新接口拒绝 email（MUser 无 email 字段，靠 user_contacts 绑定）
- #5472: 密码强度校验（待定）
- #5465: reset-password 默认密码 123456（待定）
- #5467: 4 个用户管理端点缺 admin 守卫（待定）
"""

import asyncio
import pytest
from unittest.mock import MagicMock, patch


pytestmark = pytest.mark.unit


# ============================================================
# #5458: email 解耦 — 注册接口拒绝 email
# ============================================================

class TestRegisterRejectsEmail:
    """#5458: email 不属于 MUser，注册接口应拒绝 email 字段"""

    def test_register_request_rejects_email(self):
        """RegisterRequest 带 email 应抛 ValidationError"""
        from pydantic import ValidationError
        from api.auth import RegisterRequest

        with pytest.raises(ValidationError):
            RegisterRequest(username="alice", password="Secret123!", email="a@b.com")

    def test_register_request_accepts_valid_fields(self):
        """合法字段（无 email）应正常构造"""
        from api.auth import RegisterRequest

        req = RegisterRequest(username="alice", password="Secret123!", display_name="Alice")
        assert req.username == "alice"
        assert req.display_name == "Alice"


# ============================================================
# #5458: email 解耦 — update_user 不再处理 email（走 contacts API）
# ============================================================

class TestUpdateUserRejectsEmail:
    """#5458: email 由 contacts API 管理，UserUpdate 不应接受 email 字段"""

    def test_user_update_rejects_email(self):
        """UserUpdate 带 email 应抛 ValidationError"""
        from pydantic import ValidationError
        from api.settings import UserUpdate

        with pytest.raises(ValidationError):
            UserUpdate(email="a@b.com")

    def test_user_update_accepts_profile_fields(self):
        """合法字段（display_name/roles/status，无 email）应正常构造"""
        from api.settings import UserUpdate

        u = UserUpdate(display_name="Alice", roles=["admin"], status="active")
        assert u.display_name == "Alice"
        assert u.roles == ["admin"]


# ============================================================
# #5465: reset-password 不应默认弱密码 123456
# ============================================================

class TestResetPasswordNoDefault:
    """#5465: 未传 new_password 必须拒绝，不可兜底成 123456"""

    def _admin_req(self):
        req = MagicMock()
        req.state.user_uuid = "user-admin"
        req.state.is_admin = True
        return req

    def test_reset_without_new_password_rejected(self):
        """管理员未传 new_password 应返 400，而非默认 123456"""
        from api.settings import reset_user_password
        from fastapi import HTTPException

        with pytest.raises(HTTPException) as exc_info:
            asyncio.run(reset_user_password("user-target", {}, self._admin_req()))
        assert exc_info.value.status_code == 400

    def test_reset_does_not_call_service_with_default(self):
        """被拒时 service.reset_password 不应被调用（防止任何默认值落库）"""
        from api.settings import reset_user_password
        from fastapi import HTTPException

        with patch("api.settings.get_user_service") as mock_svc:
            mock_svc.return_value.reset_password.return_value = MagicMock(success=True)
            with pytest.raises(HTTPException):
                asyncio.run(reset_user_password("user-target", {}, self._admin_req()))
            mock_svc.return_value.reset_password.assert_not_called()


# ============================================================
# #5467: 用户管理端点须 admin 守卫
# ============================================================

class TestUserMgmtAdminGuard:
    """#5467: list/create/update/delete 用户须管理员，普通用户 → 403"""

    def _req(self, is_admin):
        req = MagicMock()
        req.state.is_admin = is_admin
        return req

    def test_list_users_requires_admin(self):
        """普通用户调 list_users 应返 403"""
        from api.settings import list_users
        from fastapi import HTTPException

        with pytest.raises(HTTPException) as exc_info:
            asyncio.run(list_users(req=self._req(False)))
        assert exc_info.value.status_code == 403

    def test_create_user_requires_admin(self):
        """普通用户调 create_user 应返 403"""
        from api.settings import create_user
        from fastapi import HTTPException

        with pytest.raises(HTTPException) as exc_info:
            asyncio.run(create_user(self._req(False), MagicMock()))
        assert exc_info.value.status_code == 403

    def test_update_user_requires_admin(self):
        """普通用户调 update_user 应返 403"""
        from api.settings import update_user
        from fastapi import HTTPException

        with pytest.raises(HTTPException) as exc_info:
            asyncio.run(update_user(self._req(False), "user-target", MagicMock()))
        assert exc_info.value.status_code == 403

    def test_delete_user_requires_admin(self):
        """普通用户调 delete_user 应返 403"""
        from api.settings import delete_user
        from fastapi import HTTPException

        with pytest.raises(HTTPException) as exc_info:
            asyncio.run(delete_user(self._req(False), "user-target"))
        assert exc_info.value.status_code == 403

    def test_admin_passes_guard(self):
        """管理员调 list_users 不应被守卫拦截（守卫不误伤）"""
        from api.settings import list_users

        with patch("api.settings.get_user_service") as mock_svc:
            mock_svc.return_value.list_users.return_value = MagicMock(success=True, data={"users": []})
            # 不应抛 403；具体返回不限
            asyncio.run(list_users(req=self._req(True)))
