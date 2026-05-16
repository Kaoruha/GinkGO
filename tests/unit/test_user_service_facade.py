# See #22: UserService/UserGroupService facade methods must return ServiceResult

import pytest
from unittest.mock import MagicMock, patch

from ginkgo.data.services.base_service import ServiceResult


pytestmark = pytest.mark.unit


def _mock_user_service():
    from ginkgo.user.services.user_service import UserService
    with patch.object(UserService, '__init__', lambda self: None):
        svc = UserService()
    svc.user_contact_crud = MagicMock()
    return svc


def _mock_user_group_service():
    from ginkgo.user.services.user_group_service import UserGroupService
    with patch.object(UserGroupService, '__init__', lambda self: None):
        svc = UserGroupService()
    svc.user_group_crud = MagicMock()
    svc.user_group_mapping_crud = MagicMock()
    return svc


class TestGetActiveContactsReturnsServiceResult:
    def test_returns_service_result_success(self):
        svc = _mock_user_service()
        mock_contacts = [MagicMock()]
        svc.user_contact_crud.get_by_user.return_value = mock_contacts

        result = svc.get_active_contacts("user-001")

        assert isinstance(result, ServiceResult)
        assert result.success is True
        assert result.data == mock_contacts

    def test_returns_service_result_error(self):
        svc = _mock_user_service()
        svc.user_contact_crud.get_by_user.side_effect = Exception("db error")

        result = svc.get_active_contacts("user-001")

        assert isinstance(result, ServiceResult)
        assert result.success is False


class TestGetGroupByUuidReturnsServiceResult:
    def test_returns_service_result_success(self):
        svc = _mock_user_group_service()
        mock_group = MagicMock()
        svc.user_group_crud.find.return_value = [mock_group]

        result = svc.get_group_by_uuid("grp-001")

        assert isinstance(result, ServiceResult)
        assert result.success is True
        assert result.data == mock_group

    def test_returns_service_result_not_found(self):
        svc = _mock_user_group_service()
        svc.user_group_crud.find.return_value = []

        result = svc.get_group_by_uuid("nonexistent")

        assert isinstance(result, ServiceResult)
        assert result.success is False

    def test_returns_service_result_error(self):
        svc = _mock_user_group_service()
        svc.user_group_crud.find.side_effect = Exception("db error")

        result = svc.get_group_by_uuid("grp-001")

        assert isinstance(result, ServiceResult)
        assert result.success is False


class TestGetGroupByNameReturnsServiceResult:
    def test_returns_service_result_success(self):
        svc = _mock_user_group_service()
        mock_group = MagicMock()
        svc.user_group_crud.find.return_value = [mock_group]

        result = svc.get_group_by_name("traders")

        assert isinstance(result, ServiceResult)
        assert result.success is True
        assert result.data == mock_group

    def test_returns_service_result_not_found(self):
        svc = _mock_user_group_service()
        svc.user_group_crud.find.return_value = []

        result = svc.get_group_by_name("nonexistent")

        assert isinstance(result, ServiceResult)
        assert result.success is False


class TestGetGroupMemberUuidsReturnsServiceResult:
    def test_returns_service_result_success(self):
        svc = _mock_user_group_service()
        m1, m2 = MagicMock(user_uuid="u1"), MagicMock(user_uuid="u2")
        svc.user_group_mapping_crud.find_by_group.return_value = [m1, m2]

        result = svc.get_group_member_uuids("grp-001")

        assert isinstance(result, ServiceResult)
        assert result.success is True
        assert result.data == ["u1", "u2"]

    def test_returns_service_result_error(self):
        svc = _mock_user_group_service()
        svc.user_group_mapping_crud.find_by_group.side_effect = Exception("db error")

        result = svc.get_group_member_uuids("grp-001")

        assert isinstance(result, ServiceResult)
        assert result.success is False
