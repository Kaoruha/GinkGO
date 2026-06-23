# Issue: #5680
# Upstream: api.api.settings (_require_contact_ownership, update_user_contact)
# Downstream: ginkgo.data.services.user_service.UserService
# Role: contacts 端点 ownership 校验测试——非 owner 非 admin 不得改他人联系方式

"""
contacts 端点 ownership 校验测试 (#5680)。

#5680 根因：api/api/settings.py 的 by-contact_uuid 端点（PUT update / DELETE /
test / set-primary）完全无 ownership 校验——不取当前用户、不校验 contact 归属、
不调 _require_admin，任意登录用户可操作他人联系方式。

修复：提取 _require_contact_ownership(req, contact_uuid) helper（端点层接线，
不改 service/CRUD 层），校验 contact.user_id == 当前用户 OR _resolve_is_admin。
"""

import asyncio
from types import SimpleNamespace
from unittest.mock import patch, MagicMock

import pytest
from fastapi import HTTPException

from ginkgo.data.services.base_service import ServiceResult


def _make_req(user_uuid):
    """构造带 JWT 中间件注入 user_uuid 的 Request mock。"""
    return SimpleNamespace(state=SimpleNamespace(user_uuid=user_uuid))


def _mock_contact(owner_uuid):
    """构造 MUserContact mock（user_id 属性 = owner）。"""
    m = MagicMock()
    m.user_id = owner_uuid
    return m


def _patch_user_service(get_contact_data=None, is_admin=False, update_success=True):
    """patch api.settings.get_user_service 返回配置好的 mock service。

    返回 patcher（caller 负责 start/stop 或用 @patch）。
    """
    svc = MagicMock()
    contact = _mock_contact(get_contact_data) if get_contact_data else None
    if get_contact_data is not None:
        svc.get_contact.return_value = ServiceResult.success(contact)
    else:
        svc.get_contact.return_value = ServiceResult.error("Contact not found")
    svc.get_credential.return_value = MagicMock(is_admin=is_admin)
    svc.update_contact.return_value = (
        ServiceResult.success(data=None) if update_success else ServiceResult.error("fail")
    )
    return svc


class TestRequireContactOwnership:
    """#5680: _require_contact_ownership helper 各分支。"""

    @patch("api.settings.get_user_service")
    def test_owner_passes(self, mock_get_svc):
        """contact owner 可操作（不 raise）。"""
        mock_get_svc.return_value = _patch_user_service(get_contact_data="user-A", is_admin=False)
        from api.settings import _require_contact_ownership

        req = _make_req("user-A")
        _require_contact_ownership(req, "contact-1")  # 不 raise

    @patch("api.settings.get_user_service")
    def test_non_owner_non_admin_forbidden(self, mock_get_svc):
        """非 owner 非 admin → 403。"""
        mock_get_svc.return_value = _patch_user_service(get_contact_data="user-A", is_admin=False)
        from api.settings import _require_contact_ownership

        req = _make_req("user-B")
        with pytest.raises(HTTPException) as exc:
            _require_contact_ownership(req, "contact-1")
        assert exc.value.status_code == 403

    @patch("api.settings.get_user_service")
    def test_admin_passes_on_others_contact(self, mock_get_svc):
        """admin 可操作他人 contact（不 raise）。"""
        mock_get_svc.return_value = _patch_user_service(get_contact_data="user-A", is_admin=True)
        from api.settings import _require_contact_ownership

        req = _make_req("admin-1")  # 非 owner，但 admin
        _require_contact_ownership(req, "contact-1")  # 不 raise

    @patch("api.settings.get_user_service")
    def test_unauthenticated_forbidden(self, mock_get_svc):
        """未认证（req.state.user_uuid 缺失）→ 403。"""
        mock_get_svc.return_value = _patch_user_service(get_contact_data="user-A")
        from api.settings import _require_contact_ownership

        req = _make_req(None)
        with pytest.raises(HTTPException) as exc:
            _require_contact_ownership(req, "contact-1")
        assert exc.value.status_code == 403

    @patch("api.settings.get_user_service")
    def test_contact_not_found_returns_404(self, mock_get_svc):
        """contact 不存在 → 404（不泄露存在性给非 owner，但 owner 未见 404 语义；
        这里用 404 因 get_contact 本就返 not found，属正常语义）。"""
        mock_get_svc.return_value = _patch_user_service(get_contact_data=None)
        from api.settings import _require_contact_ownership

        req = _make_req("user-A")
        with pytest.raises(HTTPException) as exc:
            _require_contact_ownership(req, "missing-contact")
        assert exc.value.status_code == 404


class TestUpdateContactEndpointOwnership:
    """#5680: PUT /users/contacts/{contact_uuid} 端点接线 ownership 校验。"""

    @patch("api.settings.get_user_service")
    def test_update_non_owner_forbidden(self, mock_get_svc):
        """非 owner 调用 PUT update → 403（端点接线 helper）。"""
        mock_get_svc.return_value = _patch_user_service(
            get_contact_data="user-A", is_admin=False, update_success=True
        )
        from api.settings import update_user_contact, UserContactUpdate

        req = _make_req("user-B")
        data = UserContactUpdate(address="evil@evil.com")
        with pytest.raises(HTTPException) as exc:
            asyncio.run(update_user_contact("contact-1", data, req))
        assert exc.value.status_code == 403
        # service.update_contact 不应被调（ownership 拦截在前）
        mock_get_svc.return_value.update_contact.assert_not_called()

    @patch("api.settings.get_user_service")
    def test_update_owner_succeeds(self, mock_get_svc):
        """owner 调用 PUT update → 成功，update_contact 被调。"""
        mock_get_svc.return_value = _patch_user_service(
            get_contact_data="user-A", is_admin=False, update_success=True
        )
        from api.settings import update_user_contact, UserContactUpdate

        req = _make_req("user-A")
        data = UserContactUpdate(address="new@user-a.com")
        result = asyncio.run(update_user_contact("contact-1", data, req))
        mock_get_svc.return_value.update_contact.assert_called_once()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
