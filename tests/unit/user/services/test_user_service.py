# Upstream: None
# Downstream: None
# Role: UserService单元测试验证用户管理业务逻辑功能


"""
UserService Unit Tests

测试覆盖:
- 用户创建
- 联系方式添加
- 用户级联删除
- 用户查询和列表
"""

import pytest
from unittest.mock import Mock, patch, MagicMock

from ginkgo.user.services.user_service import UserService
from ginkgo.data.services.base_service import ServiceResult
from ginkgo.data.models import MUser, MUserContact
from ginkgo.enums import USER_TYPES, CONTACT_TYPES, SOURCE_TYPES


@pytest.mark.unit
class TestUserServiceInit:
    """UserService 初始化测试"""

    def test_init(self):
        """测试 UserService 初始化"""
        user_crud = Mock()
        user_contact_crud = Mock()

        service = UserService(user_crud, user_contact_crud)

        assert service.user_crud == user_crud
        assert service.user_contact_crud == user_contact_crud


@pytest.mark.unit
class TestUserServiceAddUser:
    """UserService 用户创建测试"""

    def test_add_user_success(self):
        """测试成功创建用户"""
        user_crud = Mock()
        user_contact_crud = Mock()

        # Mock add to return a proper MUser object with uuid
        mock_user = Mock()
        mock_user.uuid = "test_uuid_123"
        user_crud.add.return_value = mock_user

        service = UserService(user_crud, user_contact_crud)

        result = service.add_user(name="Test User", user_type=USER_TYPES.PERSON)

        assert result.success is True
        assert result.data["uuid"] == "test_uuid_123"
        assert result.data["name"] == "Test User"
        assert result.data["user_type"] == "PERSON"
        user_crud.add.assert_called_once()

    def test_add_user_with_string_type(self):
        """测试使用字符串类型创建用户"""
        user_crud = Mock()
        user_contact_crud = Mock()

        # Mock add to return a proper MUser object with uuid
        mock_user = Mock()
        mock_user.uuid = "test_uuid_456"
        user_crud.add.return_value = mock_user

        service = UserService(user_crud, user_contact_crud)

        result = service.add_user(name="Test Channel", user_type="CHANNEL")

        assert result.success is True
        assert result.data["uuid"] == "test_uuid_456"
        assert result.data["user_type"] == "CHANNEL"
        user_crud.add.assert_called_once()

    @patch('ginkgo.user.services.user_service.USER_TYPES')
    def test_add_user_invalid_type(self, mock_user_types):
        """测试无效用户类型"""
        user_crud = Mock()
        user_contact_crud = Mock()

        mock_user_types.validate_input.return_value = None

        service = UserService(user_crud, user_contact_crud)

        result = service.add_user(name="Test User", user_type=999)

        assert result.success is False
        assert "Invalid user_type" in result.error
        user_crud.add.assert_not_called()

    def test_add_user_database_failure(self):
        """测试数据库插入失败"""
        user_crud = Mock()
        user_contact_crud = Mock()
        user_crud.add.return_value = None

        service = UserService(user_crud, user_contact_crud)

        result = service.add_user(name="Test User")

        assert result.success is False
        assert "Failed to create user" in result.error


@pytest.mark.unit
class TestUserServiceAddContact:
    """UserService 联系方式添加测试"""

    def test_add_contact_success(self):
        """测试成功添加联系方式"""
        user_crud = Mock()
        user_contact_crud = Mock()

        # Mock add to return a proper MUserContact object with uuid
        mock_contact = Mock()
        mock_contact.uuid = "contact_uuid_123"
        user_contact_crud.add.return_value = mock_contact

        service = UserService(user_crud, user_contact_crud)

        result = service.add_contact(
            user_uuid="user_123",
            contact_type=CONTACT_TYPES.EMAIL,
            address="test@example.com"
        )

        assert result.success is True
        assert result.data["uuid"] == "contact_uuid_123"
        assert result.data["address"] == "test@example.com"
        assert result.data["contact_type"] == "EMAIL"
        user_contact_crud.add.assert_called_once()

    def test_add_contact_with_string_type(self):
        """测试使用字符串类型添加联系方式"""
        user_crud = Mock()
        user_contact_crud = Mock()

        # Mock add to return a proper MUserContact object with uuid
        mock_contact = Mock()
        mock_contact.uuid = "contact_uuid_456"
        user_contact_crud.add.return_value = mock_contact

        service = UserService(user_crud, user_contact_crud)

        result = service.add_contact(
            user_uuid="user_123",
            contact_type="DISCORD",
            address="https://discord webhook"
        )

        assert result.success is True
        assert result.data["uuid"] == "contact_uuid_456"
        assert result.data["contact_type"] == "DISCORD"

    @patch('ginkgo.user.services.user_service.CONTACT_TYPES')
    def test_add_contact_invalid_type(self, mock_contact_types):
        """测试无效联系方式类型"""
        user_crud = Mock()
        user_contact_crud = Mock()

        mock_contact_types.validate_input.return_value = None

        service = UserService(user_crud, user_contact_crud)

        result = service.add_contact(
            user_uuid="user_123",
            contact_type=999,
            address="test@example.com"
        )

        assert result.success is False
        assert "Invalid contact_type" in result.error
        user_contact_crud.add.assert_not_called()


@pytest.mark.unit
class TestUserServiceDeleteUser:
    """UserService 用户删除测试"""

    def test_delete_user_success(self):
        """测试成功删除用户"""
        user_crud = Mock()
        user_contact_crud = Mock()
        user_crud.delete.return_value = 1

        service = UserService(user_crud, user_contact_crud)

        result = service.delete_user("user_uuid_123")

        assert result.success is True
        assert result.data["deleted_count"] == 1
        user_crud.delete.assert_called_once_with(filters={"uuid": "user_uuid_123"})

    def test_delete_user_not_found(self):
        """测试删除不存在的用户"""
        user_crud = Mock()
        user_contact_crud = Mock()
        user_crud.delete.return_value = 0

        service = UserService(user_crud, user_contact_crud)

        result = service.delete_user("nonexistent_user")

        assert result.success is False
        assert "User not found" in result.error


@pytest.mark.unit
class TestUserServiceGetUser:
    """UserService 用户查询测试"""

    @patch('ginkgo.user.services.user_service.USER_TYPES')
    @patch('ginkgo.user.services.user_service.SOURCE_TYPES')
    def test_get_user_success(self, mock_source_types, mock_user_types):
        """测试成功获取用户"""
        user_crud = Mock()
        user_contact_crud = Mock()

        mock_user = MagicMock()
        mock_user.uuid = "user_uuid_123"
        mock_user.name = "Test User"
        mock_user.user_type = USER_TYPES.PERSON.value
        mock_user.is_active = True
        mock_user.source = SOURCE_TYPES.OTHER.value
        mock_user.create_at = None
        mock_user.update_at = None

        user_crud.find.return_value = [mock_user]
        mock_user_types.from_int.return_value = USER_TYPES.PERSON
        mock_source_types.from_int.return_value = SOURCE_TYPES.OTHER

        service = UserService(user_crud, user_contact_crud)

        result = service.get_user("user_uuid_123")

        assert result.success is True
        assert result.data["uuid"] == "user_uuid_123"
        assert result.data["name"] == "Test User"
        user_crud.find.assert_called_once()

    def test_get_user_not_found(self):
        """测试获取不存在的用户"""
        user_crud = Mock()
        user_contact_crud = Mock()
        user_crud.find.return_value = []

        service = UserService(user_crud, user_contact_crud)

        result = service.get_user("nonexistent_user")

        assert result.success is False
        assert "User not found" in result.error


@pytest.mark.unit
class TestUserServiceListUsers:
    """UserService 用户列表测试"""

    @patch('ginkgo.user.services.user_service.USER_TYPES')
    def test_list_users_success(self, mock_user_types):
        """测试成功列出用户"""
        user_crud = Mock()
        user_contact_crud = Mock()

        mock_user1 = MagicMock()
        mock_user1.uuid = "user1"
        mock_user1.name = "User 1"
        mock_user1.user_type = USER_TYPES.PERSON.value
        mock_user1.is_active = True
        mock_user1.create_at = None

        mock_user2 = MagicMock()
        mock_user2.uuid = "user2"
        mock_user2.name = "User 2"
        mock_user2.user_type = USER_TYPES.CHANNEL.value
        mock_user2.is_active = True
        mock_user2.create_at = None

        user_crud.find.return_value = [mock_user1, mock_user2]
        mock_user_types.from_int.side_effect = [USER_TYPES.PERSON, USER_TYPES.CHANNEL]

        service = UserService(user_crud, user_contact_crud)

        result = service.list_users()

        assert result.success is True
        assert result.data["count"] == 2
        assert len(result.data["users"]) == 2

    @patch('ginkgo.user.services.user_service.USER_TYPES')
    def test_list_users_with_filters(self, mock_user_types):
        """测试带过滤条件列出用户"""
        user_crud = Mock()
        user_contact_crud = Mock()

        user_crud.find.return_value = []
        mock_user_types.validate_input.return_value = USER_TYPES.PERSON.value

        service = UserService(user_crud, user_contact_crud)

        result = service.list_users(user_type=USER_TYPES.PERSON, is_active=True)

        user_crud.find.assert_called_once()
        call_kwargs = user_crud.find.call_args.kwargs
        assert "filters" in call_kwargs
        assert call_kwargs["filters"]["user_type"] == USER_TYPES.PERSON.value
        assert call_kwargs["filters"]["is_active"] is True


@pytest.mark.unit
class TestUserServiceGetUserContacts:
    """UserService 用户联系方式查询测试"""

    @patch('ginkgo.user.services.user_service.CONTACT_TYPES')
    def test_get_user_contacts_success(self, mock_contact_types):
        """测试成功获取用户联系方式"""
        user_crud = Mock()
        user_contact_crud = Mock()

        mock_contact1 = MagicMock()
        mock_contact1.uuid = "contact1"
        mock_contact1.contact_type = CONTACT_TYPES.EMAIL.value
        mock_contact1.address = "email1@example.com"
        mock_contact1.is_primary = True
        mock_contact1.is_active = True

        mock_contact2 = MagicMock()
        mock_contact2.uuid = "contact2"
        mock_contact2.contact_type = CONTACT_TYPES.DISCORD.value
        mock_contact2.address = "webhook_url"
        mock_contact2.is_primary = False
        mock_contact2.is_active = True

        user_contact_crud.find_by_user_id.return_value = [mock_contact1, mock_contact2]
        mock_contact_types.from_int.side_effect = [CONTACT_TYPES.EMAIL, CONTACT_TYPES.DISCORD]

        service = UserService(user_crud, user_contact_crud)

        result = service.get_user_contacts("user_uuid_123")

        assert result.success is True
        assert result.data["count"] == 2
        assert len(result.data["contacts"]) == 2
        user_contact_crud.find_by_user_id.assert_called_once_with(user_id="user_uuid_123", as_dataframe=False)

    def test_get_user_contacts_empty(self):
        """测试获取用户的空联系方式列表"""
        user_crud = Mock()
        user_contact_crud = Mock()
        user_contact_crud.find_by_user_id.return_value = []

        service = UserService(user_crud, user_contact_crud)

        result = service.get_user_contacts("user_uuid_123")

        assert result.success is True
        assert result.data["count"] == 0
        assert len(result.data["contacts"]) == 0
