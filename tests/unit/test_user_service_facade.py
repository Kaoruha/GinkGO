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
        svc = _mock_user_service()
        svc.user_crud = MagicMock()
        svc.user_crud.fuzzy_search.return_value = []

        svc.fuzzy_search("Alice", limit=5)

        svc.user_crud.fuzzy_search.assert_called_once_with("Alice", limit=5)

    def test_does_not_head_truncate_when_limit_given(self):
        """limit 下推 CRUD 后，service 不再 Python 截断（CRUD 返多少就返多少）。

        ADR-029 §Decision 9：CRUD 直接返 list（无 head 方法），service 物理上
        无法调 head()。守卫改为功能性断言：CRUD 返 3 条则 service 返 3 条
        （不做 Python 层 head(n) 截断）。
        """
        svc = _mock_user_service()
        svc.user_crud = MagicMock()
        svc.user_crud.fuzzy_search.return_value = [
            MagicMock(user_type=0), MagicMock(user_type=0), MagicMock(user_type=0),
        ]

        with patch("ginkgo.user.services.user_service.USER_TYPES"):
            result = svc.fuzzy_search("Alice", limit=1)

        # CRUD 返 3 条（limit=1 已下推到 DB），service 全透传不截断
        assert result.data["count"] == 3
        assert len(result.data["users"]) == 3


class TestUserGroupServiceFuzzySearchLimitPushDown:
    """#6572: user_group_service.fuzzy_search 透传 limit，删 head() 截断"""

    def test_passes_limit_to_crud(self):
        svc = _mock_user_group_service()
        svc.user_group_crud.fuzzy_search.return_value = []

        svc.fuzzy_search("traders", limit=5)

        svc.user_group_crud.fuzzy_search.assert_called_once_with("traders", limit=5)

    def test_does_not_head_truncate_when_limit_given(self):
        """ADR-029 §Decision 9：CRUD 直接返 list（无 head 方法），service 不截断。"""
        svc = _mock_user_group_service()
        svc.user_group_crud.fuzzy_search.return_value = [
            MagicMock(), MagicMock(), MagicMock(),
        ]

        result = svc.fuzzy_search("traders", limit=1)

        # CRUD 返 3 条（limit=1 已下推），service 全透传不截断
        assert result.data["count"] == 3
        assert len(result.data["groups"]) == 3
