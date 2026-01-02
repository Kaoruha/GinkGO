# Upstream: None
# Downstream: None
# Role: UserCRUD单元测试验证用户CRUD操作、级联软删除和业务辅助方法功能


"""
UserCRUD Unit Tests

测试覆盖:
- UserCRUD 初始化
- 基础 CRUD 操作
- 级联软删除功能
- 业务辅助方法
"""

import pytest
from unittest.mock import Mock, patch, MagicMock

from ginkgo.data.crud.user_crud import UserCRUD
from ginkgo.data.models import MUser
from ginkgo.enums import USER_TYPES, SOURCE_TYPES


@pytest.mark.unit
class TestUserCRUDInit:
    """UserCRUD 初始化测试"""

    def test_init(self):
        """测试 UserCRUD 初始化"""
        crud = UserCRUD()

        assert crud.model_class == MUser
        assert crud._is_mysql is True
        assert crud._is_clickhouse is False
        assert crud._is_mongo is False

    def test_model_class(self):
        """测试 _model_class 设置"""
        assert UserCRUD._model_class == MUser


@pytest.mark.unit
class TestUserCRUDCascadeDelete:
    """UserCRUD 级联软删除测试"""

    def test_delete_requires_filters(self):
        """测试 delete() 需要 filters 参数"""
        crud = UserCRUD()

        with pytest.raises(ValueError, match="filters参数必须提供"):
            crud.delete(filters=None)

    @patch('ginkgo.data.crud.user_crud.get_db_connection')
    def test_cascade_delete_contacts(self, mock_get_connection):
        """测试级联删除联系方式"""
        # Mock 数据库连接和session
        mock_session = MagicMock()
        mock_connection = MagicMock()
        mock_connection.return_value = mock_session
        mock_get_connection.return_value = mock_connection

        mock_result = MagicMock()
        mock_result.rowcount = 2
        mock_session.execute.return_value = mock_result

        crud = UserCRUD()
        user_uuids = ["user1", "user2"]

        count = crud._cascade_delete_contacts(user_uuids)

        assert count == 2
        assert mock_session.execute.called
        assert mock_session.commit.called

    @patch('ginkgo.data.crud.user_crud.get_db_connection')
    def test_cascade_delete_group_mappings(self, mock_get_connection):
        """测试级联删除用户组映射"""
        # Mock 数据库连接和session
        mock_session = MagicMock()
        mock_connection = MagicMock()
        mock_connection.return_value = mock_session
        mock_get_connection.return_value = mock_connection

        mock_result = MagicMock()
        mock_result.rowcount = 3
        mock_session.execute.return_value = mock_result

        crud = UserCRUD()
        user_uuids = ["user1", "user2", "user3"]

        count = crud._cascade_delete_group_mappings(user_uuids)

        assert count == 3
        assert mock_session.execute.called
        assert mock_session.commit.called

    @patch('ginkgo.data.crud.user_crud.get_db_connection')
    def test_cascade_delete_handles_connection_error(self, mock_get_connection):
        """测试级联删除处理连接错误"""
        mock_get_connection.return_value = None

        crud = UserCRUD()
        user_uuids = ["user1"]

        # 不应抛出异常，应返回0
        count = crud._cascade_delete_contacts(user_uuids)
        assert count == 0

        count = crud._cascade_delete_group_mappings(user_uuids)
        assert count == 0


@pytest.mark.unit
class TestUserCRUDBusinessMethods:
    """UserCRUD 业务辅助方法测试"""

    @patch('ginkgo.data.crud.base_crud.BaseCRUD.find')
    def test_find_by_name(self, mock_find):
        """测试按名称查询用户"""
        mock_find.return_value = []

        crud = UserCRUD()
        result = crud.find_by_name("Test User")

        mock_find.assert_called_once_with(filters={"name": "Test User"}, as_dataframe=False)

    @patch('ginkgo.data.crud.base_crud.BaseCRUD.find')
    def test_find_by_user_type(self, mock_find):
        """测试按用户类型查询"""
        mock_find.return_value = []

        crud = UserCRUD()
        result = crud.find_by_user_type(USER_TYPES.CHANNEL)

        mock_find.assert_called_once()

    @patch('ginkgo.data.crud.base_crud.BaseCRUD.find')
    def test_find_by_user_type_invalid_type(self, mock_find):
        """测试无效的用户类型"""
        crud = UserCRUD()
        result = crud.find_by_user_type(999)

        # 应返回空列表，不调用find
        assert result == []
        mock_find.assert_not_called()

    @patch('ginkgo.data.crud.base_crud.BaseCRUD.find')
    def test_find_active_users(self, mock_find):
        """测试查询激活用户"""
        mock_find.return_value = []

        crud = UserCRUD()
        result = crud.find_active_users()

        mock_find.assert_called_once_with(filters={"is_active": True}, as_dataframe=False)


@pytest.mark.unit
class TestUserCRUDFieldConfig:
    """UserCRUD 字段配置测试"""

    def test_get_enum_mappings(self):
        """测试枚举映射配置"""
        crud = UserCRUD()
        mappings = crud._get_enum_mappings()

        assert 'user_type' in mappings
        assert 'source' in mappings
        assert mappings['user_type'] == USER_TYPES

    def test_get_field_config(self):
        """测试字段配置"""
        crud = UserCRUD()
        config = crud._get_field_config()

        # user_type 配置
        assert 'user_type' in config
        assert config['user_type']['type'] == 'enum'
        assert config['user_type']['choices'] == [t for t in USER_TYPES]

        # name 配置
        assert 'name' in config
        assert config['name']['type'] == 'string'
        assert config['name']['min'] == 0
        assert config['name']['max'] == 128

        # is_active 配置
        assert 'is_active' in config
        assert config['is_active']['type'] == 'boolean'

    def test_create_from_params(self):
        """测试从参数创建用户"""
        crud = UserCRUD()
        user = crud._create_from_params(
            name="Test User",
            user_type=USER_TYPES.PERSON,
            is_active=True
        )

        assert isinstance(user, MUser)
        assert user.name == "Test User"
        assert user.user_type == USER_TYPES.PERSON.value
        assert user.is_active is True
