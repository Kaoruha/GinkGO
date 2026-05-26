"""Smoke test for UserGroupService -- #3823"""
import pytest
from unittest.mock import MagicMock, patch

try:
    from ginkgo.user.services.user_group_service import UserGroupService
    HAS_MODULE = True
except ImportError:
    HAS_MODULE = False


@pytest.mark.skipif(not HAS_MODULE, reason="ginkgo.user.services.user_group_service not importable")
class TestUserGroupServiceSmoke:
    """冒烟测试：验证可实例化和公开方法可调用"""

    def _make_svc(self):
        mock_group_crud = MagicMock()
        mock_mapping_crud = MagicMock()
        svc = UserGroupService(
            user_group_crud=mock_group_crud,
            user_group_mapping_crud=mock_mapping_crud,
        )
        return svc, mock_group_crud, mock_mapping_crud

    def test_instantiation(self):
        svc, _, _ = self._make_svc()
        assert svc is not None

    def test_create_group_callable(self):
        svc, mock_crud, _ = self._make_svc()
        mock_crud.find.return_value = []
        mock_crud.add.return_value = MagicMock(uuid="g1")
        result = svc.create_group(name="test_group")
        assert result is not None

    def test_create_group_rejects_system_name(self):
        svc, _, _ = self._make_svc()
        result = svc.create_group(name="System")
        assert result is not None
        assert not result.success

    def test_add_user_to_group_callable(self):
        svc, mock_crud, mock_mapping = self._make_svc()
        mock_crud.find.return_value = [MagicMock()]
        mock_mapping.check_mapping_exists.return_value = False
        mock_mapping.add.return_value = MagicMock(uuid="m1")
        result = svc.add_user_to_group(user_uuid="u1", group_uuid="g1")
        assert result is not None

    def test_remove_user_from_group_callable(self):
        svc, _, mock_mapping = self._make_svc()
        mock_mapping.remove_user_from_group.return_value = 1
        result = svc.remove_user_from_group(user_uuid="u1", group_uuid="g1")
        assert result is not None

    def test_get_group_callable(self):
        svc, mock_crud, _ = self._make_svc()
        mock_group = MagicMock(
            uuid="g1", name="test", description=None,
            is_active=True, source=15,
            create_at=MagicMock(isoformat=lambda: "2025-01-01"),
            update_at=MagicMock(isoformat=lambda: "2025-01-01"),
        )
        mock_crud.find.return_value = [mock_group]
        result = svc.get_group(group_uuid="g1")
        assert result is not None

    def test_list_groups_callable(self):
        svc, mock_crud, _ = self._make_svc()
        mock_crud.find.return_value = []
        result = svc.list_groups()
        assert result is not None
