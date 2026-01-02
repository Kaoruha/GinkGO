# Upstream: None
# Downstream: None
# Role: NotificationTemplateCRUD单元测试验证通知模板CRUD操作功能


"""
NotificationTemplateCRUD Unit Tests

测试覆盖:
- CRUD 初始化
- 模板添加和查询
- 按 template_id 和 name 查询
- 按标签查询
- 模板更新
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime

from ginkgo.data.crud.notification_template_crud import NotificationTemplateCRUD
from ginkgo.data.models.model_notification_template import MNotificationTemplate
from ginkgo.enums import TEMPLATE_TYPES, SOURCE_TYPES


@pytest.mark.unit
class TestNotificationTemplateCRUDInit:
    """NotificationTemplateCRUD 初始化测试"""

    def test_init(self):
        """测试初始化"""
        crud = NotificationTemplateCRUD()
        assert crud._model_class == MNotificationTemplate


@pytest.mark.unit
class TestNotificationTemplateCRUDAdd:
    """NotificationTemplateCRUD 添加操作测试"""

    @patch('ginkgo.data.crud.notification_template_crud.BaseMongoCRUD.add')
    def test_add_success(self, mock_add):
        """测试成功添加模板"""
        mock_add.return_value = "test_uuid_123"

        crud = NotificationTemplateCRUD()
        template = MNotificationTemplate(
            template_id="test_template",
            template_name="Test Template",
            content="Test content"
        )

        # Mock get_by_template_id 返回 None（不存在）
        crud.get_by_template_id = Mock(return_value=None)

        result = crud.add(template)

        assert result == "test_uuid_123"
        mock_add.assert_called_once_with(template)

    def test_add_duplicate_template_id(self):
        """测试添加重复的 template_id"""
        crud = NotificationTemplateCRUD()

        existing_template = MNotificationTemplate(
            template_id="existing",
            template_name="Existing",
            content="Content"
        )

        # Mock get_by_template_id 返回已存在的模板
        crud.get_by_template_id = Mock(return_value=existing_template)

        new_template = MNotificationTemplate(
            template_id="existing",
            template_name="New",
            content="New content"
        )

        result = crud.add(new_template)

        assert result is None


@pytest.mark.unit
class TestNotificationTemplateCRUDGet:
    """NotificationTemplateCRUD 查询操作测试"""

    @patch('ginkgo.data.crud.notification_template_crud.BaseMongoCRUD._get_collection')
    def test_get_by_template_id(self, mock_get_collection):
        """测试根据 template_id 查询"""
        mock_collection = MagicMock()
        mock_get_collection.return_value = mock_collection

        doc = {
            "_id": "mock_id",
            "uuid": "abc123" * 5,
            "template_id": "test_template",
            "template_name": "Test Template",
            "template_type": TEMPLATE_TYPES.TEXT.value,
            "content": "Test content",
            "variables": "{}",
            "is_active": True,
            "tags": [],
            "meta": "{}",
            "desc": "",
            "create_at": datetime.now(),
            "update_at": datetime.now(),
            "is_del": False,
            "source": SOURCE_TYPES.OTHER.value
        }
        mock_collection.find_one.return_value = doc

        crud = NotificationTemplateCRUD()
        result = crud.get_by_template_id("test_template")

        assert result is not None
        assert result.template_id == "test_template"
        mock_collection.find_one.assert_called_once_with({
            "template_id": "test_template",
            "is_del": False
        })

    @patch('ginkgo.data.crud.notification_template_crud.BaseMongoCRUD._get_collection')
    def test_get_by_template_id_not_found(self, mock_get_collection):
        """测试查询不存在的模板"""
        mock_collection = MagicMock()
        mock_get_collection.return_value = mock_collection
        mock_collection.find_one.return_value = None

        crud = NotificationTemplateCRUD()
        result = crud.get_by_template_id("nonexistent")

        assert result is None

    @patch('ginkgo.data.crud.notification_template_crud.BaseMongoCRUD._get_collection')
    def test_get_by_template_name(self, mock_get_collection):
        """测试根据模板名称模糊查询"""
        mock_collection = MagicMock()
        mock_get_collection.return_value = mock_collection

        doc1 = {
            "_id": "mock_id1",
            "uuid": "abc123" * 5,
            "template_id": "template1",
            "template_name": "Test Template One",
            "template_type": TEMPLATE_TYPES.TEXT.value,
            "content": "Content 1",
            "variables": "{}",
            "is_active": True,
            "tags": [],
            "meta": "{}",
            "desc": "",
            "create_at": datetime.now(),
            "update_at": datetime.now(),
            "is_del": False,
            "source": SOURCE_TYPES.OTHER.value
        }

        mock_cursor = MagicMock()
        mock_cursor.to_list.return_value = [doc1]
        mock_collection.find.return_value = mock_cursor
        mock_get_collection.return_value = mock_collection

        crud = NotificationTemplateCRUD()
        results = crud.get_by_template_name("Test")

        assert len(results) == 1
        assert results[0].template_name == "Test Template One"

    @patch('ginkgo.data.crud.notification_template_crud.BaseMongoCRUD._get_collection')
    def test_get_active_templates(self, mock_get_collection):
        """测试获取启用的模板"""
        mock_collection = MagicMock()
        mock_get_collection.return_value = mock_collection

        doc = {
            "_id": "mock_id",
            "uuid": "abc123" * 5,
            "template_id": "active_template",
            "template_name": "Active Template",
            "template_type": TEMPLATE_TYPES.MARKDOWN.value,
            "content": "Content",
            "variables": "{}",
            "is_active": True,
            "tags": [],
            "meta": "{}",
            "desc": "",
            "create_at": datetime.now(),
            "update_at": datetime.now(),
            "is_del": False,
            "source": SOURCE_TYPES.OTHER.value
        }

        mock_cursor = MagicMock()
        mock_cursor.to_list.return_value = [doc]
        mock_collection.find.return_value = mock_cursor
        mock_get_collection.return_value = mock_collection

        crud = NotificationTemplateCRUD()
        results = crud.get_active_templates()

        assert len(results) == 1
        assert results[0].is_active is True

    @patch('ginkgo.data.crud.notification_template_crud.BaseMongoCRUD._get_collection')
    def test_get_by_tags_match_all(self, mock_get_collection):
        """测试按标签查询（匹配所有标签）"""
        mock_collection = MagicMock()
        mock_get_collection.return_value = mock_collection

        doc = {
            "_id": "mock_id",
            "uuid": "abc123" * 5,
            "template_id": "tagged_template",
            "template_name": "Tagged Template",
            "template_type": TEMPLATE_TYPES.TEXT.value,
            "content": "Content",
            "variables": "{}",
            "is_active": True,
            "tags": ["trading", "alert", "urgent"],
            "meta": "{}",
            "desc": "",
            "create_at": datetime.now(),
            "update_at": datetime.now(),
            "is_del": False,
            "source": SOURCE_TYPES.OTHER.value
        }

        mock_cursor = MagicMock()
        mock_cursor.to_list.return_value = [doc]
        mock_collection.find.return_value = mock_cursor
        mock_get_collection.return_value = mock_collection

        crud = NotificationTemplateCRUD()
        results = crud.get_by_tags(["trading", "alert"], match_all=True)

        assert len(results) == 1
        assert "trading" in results[0].tags
        assert "alert" in results[0].tags

    @patch('ginkgo.data.crud.notification_template_crud.BaseMongoCRUD._get_collection')
    def test_get_by_tags_match_any(self, mock_get_collection):
        """测试按标签查询（匹配任一标签）"""
        mock_collection = MagicMock()
        mock_get_collection.return_value = mock_collection

        doc = {
            "_id": "mock_id",
            "uuid": "abc123" * 5,
            "template_id": "tagged_template",
            "template_name": "Tagged Template",
            "template_type": TEMPLATE_TYPES.TEXT.value,
            "content": "Content",
            "variables": "{}",
            "is_active": True,
            "tags": ["trading"],
            "meta": "{}",
            "desc": "",
            "create_at": datetime.now(),
            "update_at": datetime.now(),
            "is_del": False,
            "source": SOURCE_TYPES.OTHER.value
        }

        mock_cursor = MagicMock()
        mock_cursor.to_list.return_value = [doc]
        mock_collection.find.return_value = mock_cursor
        mock_get_collection.return_value = mock_collection

        crud = NotificationTemplateCRUD()
        results = crud.get_by_tags(["trading", "alert"], match_all=False)

        assert len(results) == 1


@pytest.mark.unit
class TestNotificationTemplateCRUDUpdate:
    """NotificationTemplateCRUD 更新操作测试"""

    @patch('ginkgo.data.crud.notification_template_crud.BaseMongoCRUD._get_collection')
    def test_update_by_template_id(self, mock_get_collection):
        """测试根据 template_id 更新"""
        mock_collection = MagicMock()
        mock_get_collection.return_value = mock_collection

        mock_result = MagicMock()
        mock_result.modified_count = 1
        mock_collection.update_many.return_value = mock_result

        crud = NotificationTemplateCRUD()
        count = crud.update_by_template_id(
            "test_template",
            content="New content",
            subject="New subject"
        )

        assert count == 1
        mock_collection.update_many.assert_called_once()
        call_args = mock_collection.update_many.call_args
        assert call_args[0][0]["template_id"] == "test_template"
        assert call_args[0][1]["$set"]["content"] == "New content"

    @patch('ginkgo.data.crud.notification_template_crud.BaseMongoCRUD._get_collection')
    def test_update_by_template_id_partial(self, mock_get_collection):
        """测试部分字段更新"""
        mock_collection = MagicMock()
        mock_get_collection.return_value = mock_collection

        mock_result = MagicMock()
        mock_result.modified_count = 1
        mock_collection.update_many.return_value = mock_result

        crud = NotificationTemplateCRUD()
        count = crud.update_by_template_id(
            "test_template",
            is_active=False
        )

        assert count == 1
        call_args = mock_collection.update_many.call_args
        assert "is_active" in call_args[0][1]["$set"]
        assert "content" not in call_args[0][1]["$set"]


@pytest.mark.unit
class TestNotificationTemplateCRUDDocToModel:
    """NotificationTemplateCRUD 文档转换测试"""

    def test_doc_to_model(self):
        """测试文档转模型"""
        crud = NotificationTemplateCRUD()

        doc = {
            "_id": "mock_id",
            "uuid": "abc123" * 5,
            "template_id": "test",
            "template_name": "Test",
            "template_type": TEMPLATE_TYPES.TEXT.value,
            "subject": "Subject",
            "content": "Content",
            "variables": "{}",
            "is_active": True,
            "tags": ["test"],
            "meta": "{}",
            "desc": "Description",
            "create_at": datetime.now(),
            "update_at": datetime.now(),
            "is_del": False,
            "source": SOURCE_TYPES.OTHER.value
        }

        model = crud._doc_to_model(doc)

        assert isinstance(model, MNotificationTemplate)
        assert model.template_id == "test"
        assert model.template_name == "Test"
