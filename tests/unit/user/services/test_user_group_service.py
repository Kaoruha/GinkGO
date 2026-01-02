# Upstream: None
# Downstream: None
# Role: UserGroupService单元测试验证用户组管理业务逻辑功能


"""
UserGroupService Unit Tests

测试覆盖:
- 用户组创建
- 用户加入/移除组
- 用户组删除
- 用户组查询和列表
- 用户组成员查询
"""

import pytest
from unittest.mock import Mock, patch, MagicMock

from ginkgo.user.services.user_group_service import UserGroupService
from ginkgo.data.services.base_service import ServiceResult
from ginkgo.data.models import MUserGroup, MUserGroupMapping
from ginkgo.enums import SOURCE_TYPES


@pytest.mark.unit
class TestUserGroupServiceInit:
    """UserGroupService 初始化测试"""

    def test_init(self):
        """测试 UserGroupService 初始化"""
        user_group_crud = Mock()
        user_group_mapping_crud = Mock()

        service = UserGroupService(user_group_crud, user_group_mapping_crud)

        assert service.user_group_crud == user_group_crud
        assert service.user_group_mapping_crud == user_group_mapping_crud


@pytest.mark.unit
class TestUserGroupServiceCreateGroup:
    """UserGroupService 用户组创建测试"""

    def test_create_group_success(self):
        """测试成功创建用户组"""
        user_group_crud = Mock()
        user_group_mapping_crud = Mock()

        # Mock the find method to return empty list (no existing group)
        user_group_crud.find.return_value = []

        # Mock add to return a proper MUserGroup object with uuid
        mock_group = Mock()
        mock_group.uuid = "group_uuid_123"
        mock_group.name = "Administrators"
        user_group_crud.add.return_value = mock_group

        service = UserGroupService(user_group_crud, user_group_mapping_crud)

        result = service.create_group(
            name="Administrators",
            description="Admin users"
        )

        assert result.success is True
        assert result.data["uuid"] == "group_uuid_123"
        assert result.data["name"] == "Administrators"
        assert result.data["description"] == "Admin users"
        user_group_crud.add.assert_called_once()

    def test_create_group_already_exists(self):
        """测试创建已存在的用户组"""
        user_group_crud = Mock()
        user_group_mapping_crud = Mock()

        # Mock find to return existing group
        mock_existing_group = Mock()
        user_group_crud.find.return_value = [mock_existing_group]

        service = UserGroupService(user_group_crud, user_group_mapping_crud)

        result = service.create_group(name="Administrators")

        assert result.success is False
        assert "already exists" in result.error
        user_group_crud.add.assert_not_called()

    def test_create_group_database_failure(self):
        """测试数据库插入失败"""
        user_group_crud = Mock()
        user_group_mapping_crud = Mock()

        # Mock find to return empty list (no existing group)
        user_group_crud.find.return_value = []
        # Mock add to return None (failure)
        user_group_crud.add.return_value = None

        service = UserGroupService(user_group_crud, user_group_mapping_crud)

        result = service.create_group(name="Test Group")

        assert result.success is False
        assert "Failed to create group" in result.error


@pytest.mark.unit
class TestUserGroupServiceAddUserToGroup:
    """UserGroupService 用户加入组测试"""

    def test_add_user_to_group_success(self):
        """测试成功添加用户到组"""
        user_group_crud = Mock()
        user_group_mapping_crud = Mock()

        mock_group = MagicMock()
        mock_group.uuid = "group_uuid_123"
        user_group_crud.find.return_value = [mock_group]
        user_group_mapping_crud.check_mapping_exists.return_value = False

        # Mock add to return a proper MUserGroupMapping object with uuid
        mock_mapping = Mock()
        mock_mapping.uuid = "mapping_uuid_123"
        user_group_mapping_crud.add.return_value = mock_mapping

        service = UserGroupService(user_group_crud, user_group_mapping_crud)

        result = service.add_user_to_group("user_uuid_123", "group_uuid_123")

        assert result.success is True
        assert result.data["mapping_uuid"] == "mapping_uuid_123"
        assert result.data["user_uuid"] == "user_uuid_123"
        assert result.data["group_uuid"] == "group_uuid_123"
        user_group_mapping_crud.add.assert_called_once()

    def test_add_user_to_group_group_not_found(self):
        """测试添加到不存在的组"""
        user_group_crud = Mock()
        user_group_mapping_crud = Mock()
        user_group_crud.find.return_value = []

        service = UserGroupService(user_group_crud, user_group_mapping_crud)

        result = service.add_user_to_group("user_uuid_123", "nonexistent_group")

        assert result.success is False
        assert "Group not found" in result.error
        user_group_mapping_crud.add.assert_not_called()

    def test_add_user_to_group_already_exists(self):
        """测试添加已存在的映射"""
        user_group_crud = Mock()
        user_group_mapping_crud = Mock()

        mock_group = MagicMock()
        user_group_crud.find.return_value = [mock_group]
        user_group_mapping_crud.check_mapping_exists.return_value = True

        service = UserGroupService(user_group_crud, user_group_mapping_crud)

        result = service.add_user_to_group("user_uuid_123", "group_uuid_123")

        assert result.success is False
        assert "already in group" in result.error
        user_group_mapping_crud.add.assert_not_called()


@pytest.mark.unit
class TestUserGroupServiceRemoveUserFromGroup:
    """UserGroupService 用户移除组测试"""

    def test_remove_user_from_group_success(self):
        """测试成功从组中移除用户"""
        user_group_crud = Mock()
        user_group_mapping_crud = Mock()
        user_group_mapping_crud.remove_user_from_group.return_value = 1

        service = UserGroupService(user_group_crud, user_group_mapping_crud)

        result = service.remove_user_from_group("user_uuid_123", "group_uuid_123")

        assert result.success is True
        assert result.data["deleted_count"] == 1
        user_group_mapping_crud.remove_user_from_group.assert_called_once_with(
            "user_uuid_123", "group_uuid_123"
        )

    def test_remove_user_from_group_not_found(self):
        """测试移除不存在的映射"""
        user_group_crud = Mock()
        user_group_mapping_crud = Mock()
        user_group_mapping_crud.remove_user_from_group.return_value = 0

        service = UserGroupService(user_group_crud, user_group_mapping_crud)

        result = service.remove_user_from_group("user_uuid_123", "group_uuid_123")

        assert result.success is False
        assert "not found" in result.error.lower()


@pytest.mark.unit
class TestUserGroupServiceDeleteGroup:
    """UserGroupService 用户组删除测试"""

    def test_delete_group_success(self):
        """测试成功删除用户组"""
        user_group_crud = Mock()
        user_group_mapping_crud = Mock()

        mock_mapping1 = MagicMock()
        mock_mapping1.user_uuid = "user1"
        mock_mapping2 = MagicMock()
        mock_mapping2.user_uuid = "user2"

        user_group_mapping_crud.find_by_group.return_value = [mock_mapping1, mock_mapping2]
        user_group_mapping_crud.remove_user_from_group.return_value = 1
        user_group_crud.remove.return_value = None  # remove doesn't return a count

        service = UserGroupService(user_group_crud, user_group_mapping_crud)

        result = service.delete_group("group_uuid_123")

        assert result.success is True
        assert result.data["group_uuid"] == "group_uuid_123"
        assert result.data["mappings_removed"] == 2

    def test_delete_group_not_found(self):
        """测试删除不存在的组（实际上会成功，即使没有mappings）"""
        user_group_crud = Mock()
        user_group_mapping_crud = Mock()
        user_group_mapping_crud.find_by_group.return_value = []  # No mappings
        user_group_crud.remove.return_value = None

        service = UserGroupService(user_group_crud, user_group_mapping_crud)

        result = service.delete_group("nonexistent_group")

        # The current implementation doesn't check if group exists before deleting
        # It will succeed with 0 mappings removed
        assert result.success is True
        assert result.data["mappings_removed"] == 0


@pytest.mark.unit
class TestUserGroupServiceGetGroup:
    """UserGroupService 用户组查询测试"""

    def test_get_group_success(self):
        """测试成功获取用户组"""
        user_group_crud = Mock()
        user_group_mapping_crud = Mock()

        mock_group = MagicMock()
        mock_group.uuid = "group_uuid_123"
        mock_group.name = "Administrators"
        mock_group.description = "Admin users"
        mock_group.is_active = True
        mock_group.source = SOURCE_TYPES.OTHER.value
        mock_group.create_at = None
        mock_group.update_at = None

        user_group_crud.find.return_value = [mock_group]

        service = UserGroupService(user_group_crud, user_group_mapping_crud)

        result = service.get_group("group_uuid_123")

        assert result.success is True
        assert result.data["uuid"] == "group_uuid_123"
        assert result.data["name"] == "Administrators"
        assert result.data["description"] == "Admin users"
        assert result.data["is_active"] is True

    def test_get_group_not_found(self):
        """测试获取不存在的用户组"""
        user_group_crud = Mock()
        user_group_mapping_crud = Mock()
        user_group_crud.find.return_value = []

        service = UserGroupService(user_group_crud, user_group_mapping_crud)

        result = service.get_group("nonexistent_group")

        assert result.success is False
        assert "Group not found" in result.error


@pytest.mark.unit
class TestUserGroupServiceListGroups:
    """UserGroupService 用户组列表测试"""

    def test_list_groups_success(self):
        """测试成功列出用户组"""
        user_group_crud = Mock()
        user_group_mapping_crud = Mock()

        mock_group1 = MagicMock()
        mock_group1.uuid = "group1"
        mock_group1.name = "Administrators"
        mock_group1.description = "Admin users"
        mock_group1.is_active = True
        mock_group1.create_at = None

        mock_group2 = MagicMock()
        mock_group2.uuid = "group2"
        mock_group2.name = "Users"
        mock_group2.description = "Regular users"
        mock_group2.is_active = True
        mock_group2.create_at = None

        user_group_crud.find.return_value = [mock_group1, mock_group2]

        service = UserGroupService(user_group_crud, user_group_mapping_crud)

        result = service.list_groups()

        assert result.success is True
        assert result.data["count"] == 2
        assert len(result.data["groups"]) == 2

    def test_list_groups_with_filters(self):
        """测试带过滤条件列出用户组"""
        user_group_crud = Mock()
        user_group_mapping_crud = Mock()
        user_group_crud.find.return_value = []

        service = UserGroupService(user_group_crud, user_group_mapping_crud)

        result = service.list_groups(is_active=True)

        user_group_crud.find.assert_called_once()
        call_kwargs = user_group_crud.find.call_args.kwargs
        assert "filters" in call_kwargs
        assert call_kwargs["filters"]["is_active"] is True


@pytest.mark.unit
class TestUserGroupServiceGetGroupMembers:
    """UserGroupService 用户组成员查询测试"""

    def test_get_group_members_success(self):
        """测试成功获取用户组成员"""
        user_group_crud = Mock()
        user_group_mapping_crud = Mock()

        mock_mapping1 = MagicMock()
        mock_mapping1.uuid = "mapping1"
        mock_mapping1.user_uuid = "user1"
        mock_mapping1.group_uuid = "group1"

        mock_mapping2 = MagicMock()
        mock_mapping2.uuid = "mapping2"
        mock_mapping2.user_uuid = "user2"
        mock_mapping2.group_uuid = "group1"

        user_group_mapping_crud.find_by_group.return_value = [mock_mapping1, mock_mapping2]

        service = UserGroupService(user_group_crud, user_group_mapping_crud)

        result = service.get_group_members("group1")

        assert result.success is True
        assert result.data["count"] == 2
        assert len(result.data["members"]) == 2
        user_group_mapping_crud.find_by_group.assert_called_once_with("group1")


@pytest.mark.unit
class TestUserGroupServiceGetUserGroups:
    """UserGroupService 用户所属组查询测试"""

    def test_get_user_groups_success(self):
        """测试成功获取用户所属组"""
        user_group_crud = Mock()
        user_group_mapping_crud = Mock()

        mock_mapping1 = MagicMock()
        mock_mapping1.group_uuid = "group1"

        mock_mapping2 = MagicMock()
        mock_mapping2.group_uuid = "group2"

        mock_group1 = MagicMock()
        mock_group1.uuid = "group1"
        mock_group1.group_id = "admins"
        mock_group1.name = "Administrators"
        mock_group1.description = "Admin users"

        mock_group2 = MagicMock()
        mock_group2.uuid = "group2"
        mock_group2.group_id = "users"
        mock_group2.name = "Users"
        mock_group2.description = "Regular users"

        user_group_mapping_crud.find_by_user.return_value = [mock_mapping1, mock_mapping2]
        user_group_crud.find.side_effect = [
            [mock_group1],
            [mock_group2]
        ]

        service = UserGroupService(user_group_crud, user_group_mapping_crud)

        result = service.get_user_groups("user_uuid_123")

        assert result.success is True
        assert result.data["count"] == 2
        assert len(result.data["groups"]) == 2
        assert result.data["groups"][0]["name"] == "Administrators"

    def test_get_user_groups_empty(self):
        """测试获取用户的空组列表"""
        user_group_crud = Mock()
        user_group_mapping_crud = Mock()
        user_group_mapping_crud.find_by_user.return_value = []

        service = UserGroupService(user_group_crud, user_group_mapping_crud)

        result = service.get_user_groups("user_uuid_123")

        assert result.success is True
        assert result.data["count"] == 0
        assert len(result.data["groups"]) == 0
