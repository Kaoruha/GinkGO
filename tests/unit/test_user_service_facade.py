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


class TestUserServiceFuzzySearchLimitPushDown:
    """#6572: service.fuzzy_search 透传 limit 给 CRUD，删 head() Python 截断"""

    def test_passes_limit_to_crud(self):
        from ginkgo.data.crud.model_conversion import ModelList
        svc = _mock_user_service()
        svc.user_crud = MagicMock()
        svc.user_crud.fuzzy_search.return_value = ModelList([], MagicMock())

        svc.fuzzy_search("Alice", limit=5)

        svc.user_crud.fuzzy_search.assert_called_once_with("Alice", limit=5)

    def test_does_not_head_truncate_when_limit_given(self):
        """limit 下推 CRUD 后，service 不再用 ModelList.head() 截断（DB 层已 limit）"""
        from ginkgo.data.crud.model_conversion import ModelList
        svc = _mock_user_service()
        svc.user_crud = MagicMock()
        # 3 条结果 + limit=1：当前实现会 head(1)，改后不调 head
        svc.user_crud.fuzzy_search.return_value = ModelList([
            MagicMock(user_type=0), MagicMock(user_type=0), MagicMock(user_type=0),
        ], MagicMock())

        with patch.object(ModelList, "head") as head_spy, \
             patch("ginkgo.user.services.user_service.USER_TYPES"):
            svc.fuzzy_search("Alice", limit=1)

        head_spy.assert_not_called()


class TestUserGroupServiceFuzzySearchLimitPushDown:
    """#6572: user_group_service.fuzzy_search 透传 limit，删 head() 截断"""

    def test_passes_limit_to_crud(self):
        from ginkgo.data.crud.model_conversion import ModelList
        svc = _mock_user_group_service()
        svc.user_group_crud.fuzzy_search.return_value = ModelList([], MagicMock())

        svc.fuzzy_search("traders", limit=5)

        svc.user_group_crud.fuzzy_search.assert_called_once_with("traders", limit=5)

    def test_does_not_head_truncate_when_limit_given(self):
        from ginkgo.data.crud.model_conversion import ModelList
        svc = _mock_user_group_service()
        svc.user_group_crud.fuzzy_search.return_value = ModelList([
            MagicMock(), MagicMock(), MagicMock(),
        ], MagicMock())

        with patch.object(ModelList, "head") as head_spy:
            svc.fuzzy_search("traders", limit=1)

        head_spy.assert_not_called()
