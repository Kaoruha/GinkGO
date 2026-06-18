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

import pytest


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
