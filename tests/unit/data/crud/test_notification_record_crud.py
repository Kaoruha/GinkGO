# Upstream: None
# Downstream: None
# Role: NotificationRecordCRUD单元测试验证通知记录CRUD操作功能


"""
NotificationRecordCRUD Unit Tests

测试覆盖:
- CRUD 初始化
- 记录添加和查询
- 按 message_id 查询
- 按用户 UUID 查询
- 按模板 ID 查询
- 按状态查询
- 更新状态
- 获取旧记录
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime, timedelta

from ginkgo.data.crud.notification_record_crud import NotificationRecordCRUD
from ginkgo.data.models.model_notification_record import MNotificationRecord
from ginkgo.enums import NOTIFICATION_STATUS_TYPES, SOURCE_TYPES


@pytest.mark.unit
class TestNotificationRecordCRUDInit:
    """NotificationRecordCRUD 初始化测试"""

    def test_init(self):
        """测试初始化"""
        crud = NotificationRecordCRUD()
        assert crud._model_class == MNotificationRecord


@pytest.mark.unit
class TestNotificationRecordCRUDAdd:
    """NotificationRecordCRUD 添加操作测试"""

    @patch('ginkgo.data.crud.notification_record_crud.BaseMongoCRUD.add')
    def test_add_success(self, mock_add):
        """测试成功添加记录"""
        mock_add.return_value = "test_uuid_123"

        crud = NotificationRecordCRUD()
        record = MNotificationRecord(
            message_id="test_message",
            content="Test content"
        )

        result = crud.add(record)

        assert result == "test_uuid_123"
        mock_add.assert_called_once_with(record)

    @patch('ginkgo.data.crud.notification_record_crud.BaseMongoCRUD.add')
    def test_add_failure(self, mock_add):
        """测试添加失败"""
        mock_add.side_effect = Exception("Database error")

        crud = NotificationRecordCRUD()
        record = MNotificationRecord(
            message_id="test_message",
            content="Test content"
        )

        result = crud.add(record)

        assert result is None


@pytest.mark.unit
class TestNotificationRecordCRUDGetByMessageId:
    """NotificationRecordCRUD 按 message_id 查询测试"""

    @patch('ginkgo.data.crud.notification_record_crud.BaseMongoCRUD._get_collection')
    def test_get_by_message_id(self, mock_get_collection):
        """测试根据 message_id 查询"""
        mock_collection = MagicMock()
        mock_get_collection.return_value = mock_collection

        doc = {
            "_id": "mock_id",
            "uuid": "abc123" * 5,
            "message_id": "test_message_123",
            "content": "Test content",
            "content_type": "text",
            "channels": ["discord"],
            "status": NOTIFICATION_STATUS_TYPES.SENT.value,
            "channel_results": "{}",
            "priority": 1,
            "user_uuid": None,
            "template_id": None,
            "error_message": None,
            "sent_at": datetime.now(),
            "ttl_days": 7,
            "meta": "{}",
            "desc": "",
            "create_at": datetime.now(),
            "update_at": datetime.now(),
            "is_del": False,
            "source": SOURCE_TYPES.OTHER.value
        }
        mock_collection.find_one.return_value = doc

        crud = NotificationRecordCRUD()
        result = crud.get_by_message_id("test_message_123")

        assert result is not None
        assert result.message_id == "test_message_123"
        assert result.status == NOTIFICATION_STATUS_TYPES.SENT.value
        mock_collection.find_one.assert_called_once_with({
            "message_id": "test_message_123",
            "is_del": False
        })

    @patch('ginkgo.data.crud.notification_record_crud.BaseMongoCRUD._get_collection')
    def test_get_by_message_id_not_found(self, mock_get_collection):
        """测试查询不存在的记录"""
        mock_collection = MagicMock()
        mock_get_collection.return_value = mock_collection
        mock_collection.find_one.return_value = None

        crud = NotificationRecordCRUD()
        result = crud.get_by_message_id("nonexistent")

        assert result is None


@pytest.mark.unit
class TestNotificationRecordCRUDGetByUser:
    """NotificationRecordCRUD 按用户查询测试"""

    @patch('ginkgo.data.crud.notification_record_crud.BaseMongoCRUD._get_collection')
    def test_get_by_user(self, mock_get_collection):
        """测试根据用户 UUID 查询"""
        mock_collection = MagicMock()
        mock_get_collection.return_value = mock_collection

        doc1 = {
            "_id": "mock_id1",
            "uuid": "abc123" * 5,
            "message_id": "msg1",
            "content": "Content 1",
            "content_type": "text",
            "channels": ["email"],
            "status": NOTIFICATION_STATUS_TYPES.SENT.value,
            "channel_results": "{}",
            "priority": 1,
            "user_uuid": "user_123",
            "template_id": None,
            "error_message": None,
            "sent_at": datetime.now(),
            "ttl_days": 7,
            "meta": "{}",
            "desc": "",
            "create_at": datetime.now(),
            "update_at": datetime.now(),
            "is_del": False,
            "source": SOURCE_TYPES.OTHER.value
        }

        doc2 = {
            "_id": "mock_id2",
            "uuid": "def456" * 5,
            "message_id": "msg2",
            "content": "Content 2",
            "content_type": "markdown",
            "channels": ["discord"],
            "status": NOTIFICATION_STATUS_TYPES.PENDING.value,
            "channel_results": "{}",
            "priority": 1,
            "user_uuid": "user_123",
            "template_id": None,
            "error_message": None,
            "sent_at": None,
            "ttl_days": 7,
            "meta": "{}",
            "desc": "",
            "create_at": datetime.now(),
            "update_at": datetime.now(),
            "is_del": False,
            "source": SOURCE_TYPES.OTHER.value
        }

        mock_cursor = MagicMock()
        mock_cursor.sort.return_value.limit.return_value.to_list.return_value = [doc1, doc2]
        mock_collection.find.return_value = mock_cursor
        mock_get_collection.return_value = mock_collection

        crud = NotificationRecordCRUD()
        results = crud.get_by_user("user_123")

        assert len(results) == 2
        assert results[0].user_uuid == "user_123"
        assert results[1].user_uuid == "user_123"

    @patch('ginkgo.data.crud.notification_record_crud.BaseMongoCRUD._get_collection')
    def test_get_by_user_with_status_filter(self, mock_get_collection):
        """测试根据用户 UUID 和状态查询"""
        mock_collection = MagicMock()
        mock_get_collection.return_value = mock_collection

        doc = {
            "_id": "mock_id",
            "uuid": "abc123" * 5,
            "message_id": "msg1",
            "content": "Content",
            "content_type": "text",
            "channels": ["email"],
            "status": NOTIFICATION_STATUS_TYPES.FAILED.value,
            "channel_results": "{}",
            "priority": 1,
            "user_uuid": "user_123",
            "template_id": None,
            "error_message": "Error",
            "sent_at": datetime.now(),
            "ttl_days": 7,
            "meta": "{}",
            "desc": "",
            "create_at": datetime.now(),
            "update_at": datetime.now(),
            "is_del": False,
            "source": SOURCE_TYPES.OTHER.value
        }

        mock_cursor = MagicMock()
        mock_cursor.sort.return_value.limit.return_value.to_list.return_value = [doc]
        mock_collection.find.return_value = mock_cursor
        mock_get_collection.return_value = mock_collection

        crud = NotificationRecordCRUD()
        results = crud.get_by_user("user_123", status=NOTIFICATION_STATUS_TYPES.FAILED.value)

        assert len(results) == 1
        assert results[0].status == NOTIFICATION_STATUS_TYPES.FAILED.value


@pytest.mark.unit
class TestNotificationRecordCRUDGetByTemplateId:
    """NotificationRecordCRUD 按模板 ID 查询测试"""

    @patch('ginkgo.data.crud.notification_record_crud.BaseMongoCRUD._get_collection')
    def test_get_by_template_id(self, mock_get_collection):
        """测试根据模板 ID 查询"""
        mock_collection = MagicMock()
        mock_get_collection.return_value = mock_collection

        doc = {
            "_id": "mock_id",
            "uuid": "abc123" * 5,
            "message_id": "msg1",
            "content": "Content",
            "content_type": "text",
            "channels": ["email"],
            "status": NOTIFICATION_STATUS_TYPES.SENT.value,
            "channel_results": "{}",
            "priority": 1,
            "user_uuid": None,
            "template_id": "template_123",
            "error_message": None,
            "sent_at": datetime.now(),
            "ttl_days": 7,
            "meta": "{}",
            "desc": "",
            "create_at": datetime.now(),
            "update_at": datetime.now(),
            "is_del": False,
            "source": SOURCE_TYPES.OTHER.value
        }

        mock_cursor = MagicMock()
        mock_cursor.sort.return_value.limit.return_value.to_list.return_value = [doc]
        mock_collection.find.return_value = mock_cursor
        mock_get_collection.return_value = mock_collection

        crud = NotificationRecordCRUD()
        results = crud.get_by_template_id("template_123")

        assert len(results) == 1
        assert results[0].template_id == "template_123"


@pytest.mark.unit
class TestNotificationRecordCRUDGetByStatus:
    """NotificationRecordCRUD 按状态查询测试"""

    @patch('ginkgo.data.crud.notification_record_crud.BaseMongoCRUD._get_collection')
    def test_get_by_status(self, mock_get_collection):
        """测试根据状态查询"""
        mock_collection = MagicMock()
        mock_get_collection.return_value = mock_collection

        doc = {
            "_id": "mock_id",
            "uuid": "abc123" * 5,
            "message_id": "msg1",
            "content": "Content",
            "content_type": "text",
            "channels": ["email"],
            "status": NOTIFICATION_STATUS_TYPES.FAILED.value,
            "channel_results": "{}",
            "priority": 1,
            "user_uuid": None,
            "template_id": None,
            "error_message": "Error",
            "sent_at": datetime.now(),
            "ttl_days": 7,
            "meta": "{}",
            "desc": "",
            "create_at": datetime.now(),
            "update_at": datetime.now(),
            "is_del": False,
            "source": SOURCE_TYPES.OTHER.value
        }

        mock_cursor = MagicMock()
        mock_cursor.sort.return_value.limit.return_value.to_list.return_value = [doc]
        mock_collection.find.return_value = mock_cursor
        mock_get_collection.return_value = mock_collection

        crud = NotificationRecordCRUD()
        results = crud.get_by_status(NOTIFICATION_STATUS_TYPES.FAILED.value)

        assert len(results) == 1
        assert results[0].status == NOTIFICATION_STATUS_TYPES.FAILED.value

    def test_get_recent_failed(self):
        """测试获取最近的失败记录"""
        crud = NotificationRecordCRUD()

        # Mock get_by_status
        failed_records = [
            MNotificationRecord(
                message_id="failed_msg1",
                content="Failed content",
                status=NOTIFICATION_STATUS_TYPES.FAILED.value
            ),
            MNotificationRecord(
                message_id="failed_msg2",
                content="Failed content 2",
                status=NOTIFICATION_STATUS_TYPES.FAILED.value
            )
        ]

        crud.get_by_status = Mock(return_value=failed_records)

        results = crud.get_recent_failed(limit=50)

        assert len(results) == 2
        crud.get_by_status.assert_called_once_with(
            status=NOTIFICATION_STATUS_TYPES.FAILED.value,
            limit=50
        )


@pytest.mark.unit
class TestNotificationRecordCRUDUpdateStatus:
    """NotificationRecordCRUD 状态更新测试"""

    @patch('ginkgo.data.crud.notification_record_crud.BaseMongoCRUD._get_collection')
    def test_update_status(self, mock_get_collection):
        """测试更新状态"""
        mock_collection = MagicMock()
        mock_get_collection.return_value = mock_collection

        mock_result = MagicMock()
        mock_result.modified_count = 1
        mock_collection.update_many.return_value = mock_result

        crud = NotificationRecordCRUD()
        count = crud.update_status(
            "test_message",
            NOTIFICATION_STATUS_TYPES.SENT.value
        )

        assert count == 1
        mock_collection.update_many.assert_called_once()
        call_args = mock_collection.update_many.call_args
        assert call_args[0][0]["message_id"] == "test_message"
        assert call_args[0][1]["$set"]["status"] == NOTIFICATION_STATUS_TYPES.SENT.value
        assert "update_at" in call_args[0][1]["$set"]

    @patch('ginkgo.data.crud.notification_record_crud.BaseMongoCRUD._get_collection')
    def test_update_status_with_error(self, mock_get_collection):
        """测试更新状态（包含错误信息）"""
        mock_collection = MagicMock()
        mock_get_collection.return_value = mock_collection

        mock_result = MagicMock()
        mock_result.modified_count = 1
        mock_collection.update_many.return_value = mock_result

        crud = NotificationRecordCRUD()
        count = crud.update_status(
            "test_message",
            NOTIFICATION_STATUS_TYPES.FAILED.value,
            error_message="Webhook timeout"
        )

        assert count == 1
        call_args = mock_collection.update_many.call_args
        assert call_args[0][1]["$set"]["error_message"] == "Webhook timeout"

    @patch('ginkgo.data.crud.notification_record_crud.BaseMongoCRUD._get_collection')
    def test_update_status_sent_sets_sent_at(self, mock_get_collection):
        """测试更新为已发送时设置 sent_at"""
        mock_collection = MagicMock()
        mock_get_collection.return_value = mock_collection

        mock_result = MagicMock()
        mock_result.modified_count = 1
        mock_collection.update_many.return_value = mock_result

        crud = NotificationRecordCRUD()
        count = crud.update_status(
            "test_message",
            NOTIFICATION_STATUS_TYPES.SENT.value
        )

        assert count == 1
        call_args = mock_collection.update_many.call_args
        assert "sent_at" in call_args[0][1]["$set"]


@pytest.mark.unit
class TestNotificationRecordCRUDGetOldRecords:
    """NotificationRecordCRUD 获取旧记录测试"""

    @patch('ginkgo.data.crud.notification_record_crud.BaseMongoCRUD._get_collection')
    def test_get_old_records(self, mock_get_collection):
        """测试获取旧记录"""
        mock_collection = MagicMock()
        mock_get_collection.return_value = mock_collection

        old_date = datetime.now() - timedelta(days=10)
        doc = {
            "_id": "mock_id",
            "uuid": "abc123" * 5,
            "message_id": "old_msg",
            "content": "Old content",
            "content_type": "text",
            "channels": [],
            "status": NOTIFICATION_STATUS_TYPES.SENT.value,
            "channel_results": "{}",
            "priority": 1,
            "user_uuid": None,
            "template_id": None,
            "error_message": None,
            "sent_at": old_date,
            "ttl_days": 7,
            "meta": "{}",
            "desc": "",
            "create_at": old_date,
            "update_at": old_date,
            "is_del": False,
            "source": SOURCE_TYPES.OTHER.value
        }

        mock_cursor = MagicMock()
        mock_cursor.limit.return_value.to_list.return_value = [doc]
        mock_collection.find.return_value = mock_cursor
        mock_get_collection.return_value = mock_collection

        crud = NotificationRecordCRUD()
        results = crud.get_old_records(days_old=7)

        assert len(results) == 1
        mock_collection.find.assert_called_once()
        call_args = mock_collection.find.call_args
        assert "$lt" in call_args[0][0]["create_at"]


@pytest.mark.unit
class TestNotificationRecordCRUDDocToModel:
    """NotificationRecordCRUD 文档转换测试"""

    def test_doc_to_model(self):
        """测试文档转模型"""
        crud = NotificationRecordCRUD()

        doc = {
            "_id": "mock_id",
            "uuid": "abc123" * 5,
            "message_id": "test_msg",
            "content": "Content",
            "content_type": "markdown",
            "channels": ["discord", "email"],
            "status": NOTIFICATION_STATUS_TYPES.SENT.value,
            "channel_results": '{"discord": {"success": true}}',
            "priority": 2,
            "user_uuid": "user_123",
            "template_id": "template_123",
            "error_message": None,
            "sent_at": datetime.now(),
            "ttl_days": 14,
            "meta": "{}",
            "desc": "Test record",
            "create_at": datetime.now(),
            "update_at": datetime.now(),
            "is_del": False,
            "source": SOURCE_TYPES.OTHER.value
        }

        model = crud._doc_to_model(doc)

        assert isinstance(model, MNotificationRecord)
        assert model.message_id == "test_msg"
        assert model.content_type == "markdown"
        assert "discord" in model.channels
        assert model.priority == 2
        assert model.ttl_days == 14
