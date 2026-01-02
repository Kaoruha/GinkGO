# Upstream: None
# Downstream: None
# Role: UserContactCRUD、UserGroupCRUD、UserGroupMappingCRUD单元测试验证CRUD操作和业务辅助方法功能


"""
UserContactCRUD, UserGroupCRUD, UserGroupMappingCRUD Unit Tests

测试覆盖:
- CRUD 初始化
- 字段配置
- 业务辅助方法
"""

import pytest
from unittest.mock import Mock, patch, MagicMock

from ginkgo.data.crud.user_contact_crud import UserContactCRUD
from ginkgo.data.crud.user_group_crud import UserGroupCRUD
from ginkgo.data.crud.user_group_mapping_crud import UserGroupMappingCRUD
from ginkgo.data.models import MUserContact, MUserGroup, MUserGroupMapping
from ginkgo.enums import CONTACT_TYPES, SOURCE_TYPES


@pytest.mark.unit
class TestUserContactCRUD:
    """UserContactCRUD 测试"""

    def test_init(self):
        """测试初始化"""
        crud = UserContactCRUD()
        assert crud.model_class == MUserContact

    def test_get_enum_mappings(self):
        """测试枚举映射"""
        crud = UserContactCRUD()
        mappings = crud._get_enum_mappings()

        assert 'contact_type' in mappings
        assert mappings['contact_type'] == CONTACT_TYPES

    def test_get_field_config(self):
        """测试字段配置"""
        crud = UserContactCRUD()
        config = crud._get_field_config()

        assert 'user_id' in config
        assert 'contact_type' in config
        assert 'address' in config
        assert 'is_primary' in config
        assert 'is_active' in config

    def test_create_from_params_requires_user_id(self):
        """测试创建需要 user_id"""
        crud = UserContactCRUD()

        with pytest.raises(ValueError, match="user_id 是必填参数"):
            crud._create_from_params(address="test@example.com")

    def test_create_from_params_success(self):
        """测试成功创建"""
        crud = UserContactCRUD()
        contact = crud._create_from_params(
            user_id="user_uuid_123",
            contact_type=CONTACT_TYPES.EMAIL,
            address="test@example.com"
        )

        assert isinstance(contact, MUserContact)
        assert contact.user_id == "user_uuid_123"

    @patch('ginkgo.data.crud.base_crud.BaseCRUD.find')
    def test_find_by_user_id(self, mock_find):
        """测试按用户ID查询"""
        mock_find.return_value = []
        crud = UserContactCRUD()

        crud.find_by_user_id("user_uuid_123")
        mock_find.assert_called_once()

    @patch('ginkgo.data.crud.base_crud.BaseCRUD.find')
    def test_find_by_contact_type(self, mock_find):
        """测试按类型查询"""
        mock_find.return_value = []
        crud = UserContactCRUD()

        crud.find_by_contact_type(CONTACT_TYPES.EMAIL)
        mock_find.assert_called_once()

    @patch('ginkgo.data.crud.base_crud.BaseCRUD.find')
    def test_find_primary_contacts(self, mock_find):
        """测试查询主联系方式"""
        mock_find.return_value = []
        crud = UserContactCRUD()

        crud.find_primary_contacts()
        mock_find.assert_called_once_with(filters={"is_primary": True}, as_dataframe=False)

    @patch('ginkgo.data.crud.base_crud.BaseCRUD.find')
    def test_find_active_contacts(self, mock_find):
        """测试查询启用联系方式"""
        mock_find.return_value = []
        crud = UserContactCRUD()

        crud.find_active_contacts(user_id="user_uuid_123")
        mock_find.assert_called_once()


@pytest.mark.unit
class TestUserGroupCRUD:
    """UserGroupCRUD 测试"""

    def test_init(self):
        """测试初始化"""
        crud = UserGroupCRUD()
        assert crud.model_class == MUserGroup

    def test_get_field_config(self):
        """测试字段配置"""
        crud = UserGroupCRUD()
        config = crud._get_field_config()

        assert 'group_id' in config
        assert 'name' in config
        assert 'description' in config

    def test_create_from_params_requires_group_id(self):
        """测试创建需要 group_id"""
        crud = UserGroupCRUD()

        with pytest.raises(ValueError, match="group_id 是必填参数"):
            crud._create_from_params(name="Test Group")

    def test_create_from_params_success(self):
        """测试成功创建"""
        crud = UserGroupCRUD()
        group = crud._create_from_params(
            group_id="admins",
            name="Administrators"
        )

        assert isinstance(group, MUserGroup)
        assert group.group_id == "admins"

    @patch('ginkgo.data.crud.base_crud.BaseCRUD.find')
    def test_find_by_group_id(self, mock_find):
        """测试按组ID查询"""
        mock_find.return_value = []
        crud = UserGroupCRUD()

        crud.find_by_group_id("admins")
        mock_find.assert_called_once()

    @patch('ginkgo.data.crud.base_crud.BaseCRUD.find')
    def test_find_by_name_pattern(self, mock_find):
        """测试按名称模糊查询"""
        mock_find.return_value = []
        crud = UserGroupCRUD()

        crud.find_by_name_pattern("admin")
        mock_find.assert_called_once()


@pytest.mark.unit
class TestUserGroupMappingCRUD:
    """UserGroupMappingCRUD 测试"""

    def test_init(self):
        """测试初始化"""
        crud = UserGroupMappingCRUD()
        assert crud.model_class == MUserGroupMapping

    def test_get_field_config(self):
        """测试字段配置"""
        crud = UserGroupMappingCRUD()
        config = crud._get_field_config()

        assert 'user_uuid' in config
        assert 'group_uuid' in config

    def test_create_from_params_requires_both_uuids(self):
        """测试创建需要 user_uuid 和 group_uuid"""
        crud = UserGroupMappingCRUD()

        with pytest.raises(ValueError, match="user_uuid 是必填参数"):
            crud._create_from_params(group_uuid="group_uuid_123")

        with pytest.raises(ValueError, match="group_uuid 是必填参数"):
            crud._create_from_params(user_uuid="user_uuid_123")

    def test_create_from_params_success(self):
        """测试成功创建"""
        crud = UserGroupMappingCRUD()
        mapping = crud._create_from_params(
            user_uuid="user_uuid_123",
            group_uuid="group_uuid_456"
        )

        assert isinstance(mapping, MUserGroupMapping)
        assert mapping.user_uuid == "user_uuid_123"
        assert mapping.group_uuid == "group_uuid_456"

    @patch('ginkgo.data.crud.base_crud.BaseCRUD.find')
    def test_find_by_user(self, mock_find):
        """测试按用户查询映射"""
        mock_find.return_value = []
        crud = UserGroupMappingCRUD()

        crud.find_by_user("user_uuid_123")
        mock_find.assert_called_once()

    @patch('ginkgo.data.crud.base_crud.BaseCRUD.find')
    def test_find_by_group(self, mock_find):
        """测试按组查询映射"""
        mock_find.return_value = []
        crud = UserGroupMappingCRUD()

        crud.find_by_group("group_uuid_456")
        mock_find.assert_called_once()

    @patch('ginkgo.data.crud.base_crud.BaseCRUD.find')
    def test_check_mapping_exists(self, mock_find):
        """测试检查映射是否存在"""
        # 存在映射
        mock_mapping = MagicMock()
        mock_find.return_value = [mock_mapping]

        crud = UserGroupMappingCRUD()
        exists = crud.check_mapping_exists("user_uuid_123", "group_uuid_456")

        assert exists is True
        mock_find.assert_called_once()

    @patch('ginkgo.data.crud.base_crud.BaseCRUD.find')
    @patch('ginkgo.data.crud.base_crud.BaseCRUD.remove')
    def test_remove_user_from_group(self, mock_remove, mock_find):
        """测试从组中移除用户"""
        # 映射存在
        mock_mapping = MagicMock()
        mock_find.return_value = [mock_mapping]
        mock_remove.return_value = 1

        crud = UserGroupMappingCRUD()
        count = crud.remove_user_from_group("user_uuid_123", "group_uuid_456")

        assert count == 1
        mock_remove.assert_called_once()

    @patch('ginkgo.data.crud.base_crud.BaseCRUD.find')
    def test_remove_user_from_group_not_exists(self, mock_find):
        """测试移除不存在的映射"""
        # 映射不存在
        mock_find.return_value = []

        crud = UserGroupMappingCRUD()
        count = crud.remove_user_from_group("user_uuid_123", "group_uuid_456")

        assert count == 0
        mock_remove.assert_not_called()

    @patch('ginkgo.data.crud.base_crud.BaseCRUD.remove')
    def test_remove_user_from_all_groups(self, mock_remove):
        """测试从所有组中移除用户"""
        mock_remove.return_value = 3

        crud = UserGroupMappingCRUD()
        count = crud.remove_user_from_all_groups("user_uuid_123")

        assert count == 3
        mock_remove.assert_called_once()
