# #4604: 验证完整版 UserService 合并薄版凭证方法后的行为
# 这些方法原存在于 data/services/user_service.py，现迁移到 user/services/user_service.py

import pytest
from unittest.mock import MagicMock, patch
from datetime import datetime

from ginkgo.data.services.base_service import ServiceResult


pytestmark = pytest.mark.unit


def _mock_user_service():
    """创建一个 mock 的 UserService，跳过构造函数"""
    from ginkgo.user.services.user_service import UserService
    with patch.object(UserService, '__init__', lambda self: None):
        svc = UserService()
    svc.user_crud = MagicMock()
    svc.user_contact_crud = MagicMock()
    svc.user_credential_crud = MagicMock()
    return svc


class TestGetCredential:
    """get_credential(user_id) → 返回凭据对象或 None"""

    def test_returns_credential_when_found(self):
        svc = _mock_user_service()
        mock_cred = MagicMock(uuid="cred-001", user_id="user-001", password_hash="hash")
        svc.user_credential_crud.get_by_user_id.return_value = mock_cred

        result = svc.get_credential("user-001")

        assert result is not None
        assert result.uuid == "cred-001"
        svc.user_credential_crud.get_by_user_id.assert_called_once_with("user-001")

    def test_returns_none_when_not_found(self):
        svc = _mock_user_service()
        svc.user_credential_crud.get_by_user_id.return_value = None

        result = svc.get_credential("nonexistent")

        assert result is None


class TestGetAllCredentials:
    """get_all_credentials() → 返回 {user_id: credential} 字典"""

    def test_returns_dict_of_credentials(self):
        svc = _mock_user_service()
        c1 = MagicMock(user_id="u1")
        c2 = MagicMock(user_id="u2")
        svc.user_credential_crud.find.return_value = [c1, c2]

        result = svc.get_all_credentials()

        assert isinstance(result, dict)
        assert "u1" in result
        assert "u2" in result
        assert result["u1"] is c1

    def test_returns_empty_dict_on_error(self):
        svc = _mock_user_service()
        svc.user_credential_crud.find.side_effect = Exception("db error")

        result = svc.get_all_credentials()

        assert result == {}


class TestUpdateLastLogin:
    """update_last_login(credential_uuid, ip) → 返回 bool"""

    def test_returns_true_on_success(self):
        svc = _mock_user_service()

        result = svc.update_last_login("cred-001", "127.0.0.1")

        assert result is True
        call_args = svc.user_credential_crud.modify.call_args
        assert call_args[0][0] == {"uuid": "cred-001"}
        updates = call_args[0][1]
        assert "last_login_at" in updates
        assert updates["last_login_ip"] == "127.0.0.1"

    def test_returns_false_on_error(self):
        svc = _mock_user_service()
        svc.user_credential_crud.modify.side_effect = Exception("db error")

        result = svc.update_last_login("cred-001", "127.0.0.1")

        assert result is False


class TestUpdatePassword:
    """update_password(credential_uuid, new_hash) → 返回 bool"""

    def test_returns_true_on_success(self):
        svc = _mock_user_service()

        result = svc.update_password("cred-001", "new_hash_abc")

        assert result is True
        svc.user_credential_crud.modify.assert_called_once_with(
            {"uuid": "cred-001"},
            {"password_hash": "new_hash_abc"},
        )

    def test_returns_false_on_error(self):
        svc = _mock_user_service()
        svc.user_credential_crud.modify.side_effect = Exception("db error")

        result = svc.update_password("cred-001", "new_hash")

        assert result is False


class TestResetPassword:
    """reset_password(user_uuid, new_hash) → 返回 ServiceResult"""

    def test_success_when_credential_found(self):
        svc = _mock_user_service()
        mock_cred = MagicMock(uuid="cred-001")
        svc.user_credential_crud.get_by_user_id.return_value = mock_cred

        result = svc.reset_password("user-001", "new_hash")

        assert isinstance(result, ServiceResult)
        assert result.success is True
        svc.user_credential_crud.modify.assert_called_once_with(
            {"uuid": "cred-001"},
            {"password_hash": "new_hash"},
        )

    def test_error_when_credential_not_found(self):
        svc = _mock_user_service()
        svc.user_credential_crud.get_by_user_id.return_value = None

        result = svc.reset_password("user-001", "new_hash")

        assert isinstance(result, ServiceResult)
        assert result.success is False

    def test_error_on_exception(self):
        svc = _mock_user_service()
        svc.user_credential_crud.get_by_user_id.side_effect = Exception("db error")

        result = svc.reset_password("user-001", "new_hash")

        assert isinstance(result, ServiceResult)
        assert result.success is False


class TestGetContact:
    """get_contact(contact_uuid) → 返回 ServiceResult"""

    def test_success_when_found(self):
        svc = _mock_user_service()
        mock_contact = MagicMock(uuid="contact-001")
        svc.user_contact_crud.find.return_value = [mock_contact]

        result = svc.get_contact("contact-001")

        assert isinstance(result, ServiceResult)
        assert result.success is True
        assert result.data is mock_contact

    def test_error_when_not_found(self):
        svc = _mock_user_service()
        svc.user_contact_crud.find.return_value = []

        result = svc.get_contact("nonexistent")

        assert isinstance(result, ServiceResult)
        assert result.success is False

    def test_error_on_exception(self):
        svc = _mock_user_service()
        svc.user_contact_crud.find.side_effect = Exception("db error")

        result = svc.get_contact("contact-001")

        assert isinstance(result, ServiceResult)
        assert result.success is False


class TestUpdateUserSyncsCredential:
    """#4612 review: update_user 应同步 is_active 到凭据表"""

    def _setup_update_user(self):
        """创建 service 并 mock 基本查询"""
        svc = _mock_user_service()
        mock_user = MagicMock(
            uuid="u-001", username="alice", display_name="Alice",
            description="", user_type=1, is_active=True, source=1,
            create_at=None, update_at=None,
        )
        svc.user_crud.find.return_value = [mock_user]
        mock_cred = MagicMock(uuid="cred-001", is_admin=False, is_active=True)
        svc.user_credential_crud.get_by_user_id.return_value = mock_cred
        return svc, mock_cred

    def test_syncs_is_admin_to_credential(self):
        svc, mock_cred = self._setup_update_user()

        result = svc.update_user("u-001", is_admin=True)

        assert result.success
        cred_call = svc.user_credential_crud.modify.call_args
        assert cred_call.kwargs["filters"] == {"uuid": "cred-001"}
        assert cred_call.kwargs["updates"]["is_admin"] is True

    def test_syncs_is_active_to_credential(self):
        """禁用用户时应同时禁用凭据"""
        svc, mock_cred = self._setup_update_user()

        result = svc.update_user("u-001", is_active=False)

        assert result.success
        cred_call = svc.user_credential_crud.modify.call_args
        assert cred_call.kwargs["filters"] == {"uuid": "cred-001"}
        assert cred_call.kwargs["updates"]["is_active"] is False

    def test_syncs_both_is_admin_and_is_active(self):
        """同时更新 is_admin 和 is_active 应在一个 modify 调用中"""
        svc, mock_cred = self._setup_update_user()

        result = svc.update_user("u-001", is_admin=True, is_active=False)

        assert result.success
        cred_call = svc.user_credential_crud.modify.call_args
        assert cred_call.kwargs["updates"] == {"is_admin": True, "is_active": False}


class TestAddUserDuplicateCheck:
    """#4612 review: add_user 应检查重名"""

    def test_rejects_duplicate_username(self):
        """重名注册应返回含 'already exists' 的错误"""
        svc = _mock_user_service()
        svc.user_crud.find.return_value = [MagicMock(username="alice")]

        result = svc.add_user(name="alice", password_hash="hash123")

        assert result.success is False
        assert "already exists" in result.error

    def test_allows_new_username(self):
        """新用户名不应被拒绝"""
        svc = _mock_user_service()
        svc.user_crud.find.return_value = []  # 无重名
        mock_created = MagicMock(uuid="new-uuid")
        svc.user_crud.add.return_value = mock_created
        svc.user_credential_crud.add.return_value = MagicMock(uuid="cred-001")

        result = svc.add_user(name="bob", password_hash="hash123")

        assert result.success is True
