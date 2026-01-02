# Upstream: None
# Downstream: None
# Role: MNotificationRecord单元测试验证通知记录模型功能


"""
MNotificationRecord Unit Tests

测试覆盖:
- 记录初始化
- 状态管理
- 渠道结果处理
- MongoDB 转换
"""

import pytest
import json
from datetime import datetime

from ginkgo.data.models import MNotificationRecord
from ginkgo.enums import NOTIFICATION_STATUS_TYPES, SOURCE_TYPES


@pytest.mark.unit
class TestNotificationRecordInit:
    """MNotificationRecord 初始化测试"""

    def test_default_init(self):
        """测试默认初始化"""
        record = MNotificationRecord(
            message_id="test_message",
            content="Test content"
        )

        assert record.message_id == "test_message"
        assert record.content == "Test content"
        assert record.content_type == "text"
        assert record.channels == []
        assert record.status == NOTIFICATION_STATUS_TYPES.PENDING.value
        assert record.priority == 1
        assert record.channel_results == "{}"
        assert record.__collection__ == "notification_records"

    def test_init_with_all_fields(self):
        """测试完整字段初始化"""
        record = MNotificationRecord(
            message_id="msg_123",
            content="Alert content",
            content_type="markdown",
            channels=["discord", "email"],
            status=NOTIFICATION_STATUS_TYPES.SENT.value,
            priority=2,
            user_uuid="user_123",
            template_id="alert_template",
            error_message=None,
            ttl_days=7
        )

        assert record.message_id == "msg_123"
        assert record.content_type == "markdown"
        assert "discord" in record.channels
        assert "email" in record.channels
        assert record.status == NOTIFICATION_STATUS_TYPES.SENT.value

    def test_priority_validation(self):
        """测试优先级验证"""
        # 有效优先级
        record = MNotificationRecord(
            message_id="test",
            content="Content",
            priority=0  # 低优先级
        )
        assert record.priority == 0

        record = MNotificationRecord(
            message_id="test",
            content="Content",
            priority=3  # 紧急
        )
        assert record.priority == 3

        # 无效优先级
        with pytest.raises(Exception):
            MNotificationRecord(
                message_id="test",
                content="Content",
                priority=5  # 超出范围
            )

    def test_ttl_days_validation(self):
        """测试 TTL 天数验证"""
        # 有效范围
        record = MNotificationRecord(
            message_id="test",
            content="Content",
            ttl_days=1
        )
        assert record.ttl_days == 1

        record = MNotificationRecord(
            message_id="test",
            content="Content",
            ttl_days=30
        )
        assert record.ttl_days == 30

        # 无效范围
        with pytest.raises(Exception):
            MNotificationRecord(
                message_id="test",
                content="Content",
                ttl_days=0
            )


@pytest.mark.unit
class TestNotificationRecordStatus:
    """MNotificationRecord 状态管理测试"""

    def test_mark_as_sent(self):
        """测试标记为已发送"""
        record = MNotificationRecord(
            message_id="test",
            content="Content"
        )

        record.mark_as_sent()

        assert record.is_sent() is True
        assert record.is_failed() is False
        assert record.is_pending() is False
        assert record.sent_at is not None

    def test_mark_as_failed(self):
        """测试标记为失败"""
        record = MNotificationRecord(
            message_id="test",
            content="Content"
        )

        record.mark_as_failed("Webhook timeout")

        assert record.is_failed() is True
        assert record.is_sent() is False
        assert record.error_message == "Webhook timeout"
        assert record.sent_at is not None

    def test_get_status_enum(self):
        """测试获取状态枚举"""
        record = MNotificationRecord(
            message_id="test",
            content="Content",
            status=NOTIFICATION_STATUS_TYPES.SENT.value
        )

        enum_status = record.get_status_enum()
        assert enum_status == NOTIFICATION_STATUS_TYPES.SENT
        assert enum_status.name == "SENT"


@pytest.mark.unit
class TestNotificationRecordChannelResults:
    """MNotificationRecord 渠道结果处理测试"""

    def test_get_channel_results_dict(self):
        """测试获取渠道结果字典"""
        results_dict = {
            "discord": {"success": True, "message_id": "123456"},
            "email": {"success": False, "error": "Invalid address"}
        }

        record = MNotificationRecord(
            message_id="test",
            content="Content",
            channel_results=json.dumps(results_dict, ensure_ascii=False)
        )

        result = record.get_channel_results_dict()
        assert result["discord"]["success"] is True
        assert result["email"]["success"] is False

    def test_set_channel_results_dict(self):
        """测试设置渠道结果字典"""
        record = MNotificationRecord(
            message_id="test",
            content="Content"
        )

        results = {
            "discord": {"success": True, "message_id": "abc123"},
            "email": {"success": True, "message_id": "xyz789"}
        }

        record.set_channel_results_dict(results)

        retrieved = record.get_channel_results_dict()
        assert retrieved == results

    def test_add_channel_result_success(self):
        """测试添加成功的渠道结果"""
        record = MNotificationRecord(
            message_id="test",
            content="Content"
        )

        record.add_channel_result(
            channel="discord",
            success=True,
            message_id="msg_123456"
        )

        results = record.get_channel_results_dict()
        assert "discord" in results
        assert results["discord"]["success"] is True
        assert results["discord"]["message_id"] == "msg_123456"
        assert "timestamp" in results["discord"]

    def test_add_channel_result_failure(self):
        """测试添加失败的渠道结果"""
        record = MNotificationRecord(
            message_id="test",
            content="Content"
        )

        record.add_channel_result(
            channel="email",
            success=False,
            error="SMTP connection failed"
        )

        results = record.get_channel_results_dict()
        assert results["email"]["success"] is False
        assert results["email"]["error"] == "SMTP connection failed"

    def test_add_multiple_channel_results(self):
        """测试添加多个渠道结果"""
        record = MNotificationRecord(
            message_id="test",
            content="Content",
            channels=["discord", "email", "kafka"]
        )

        # 添加多个结果
        record.add_channel_result("discord", True, message_id="discord_msg_1")
        record.add_channel_result("email", True, message_id="email_msg_1")
        record.add_channel_result("kafka", False, error="Kafka broker unavailable")

        results = record.get_channel_results_dict()
        assert len(results) == 3
        assert results["discord"]["success"] is True
        assert results["email"]["success"] is True
        assert results["kafka"]["success"] is False


@pytest.mark.unit
class TestNotificationRecordTTL:
    """MNotificationRecord TTL 配置测试"""

    def test_get_ttl_index_config_default(self):
        """测试获取默认 TTL 配置"""
        record = MNotificationRecord(
            message_id="test",
            content="Content"
        )

        ttl_config = record.get_ttl_index_config()

        assert "create_at" in ttl_config
        assert ttl_config["expireAfterSeconds"] == 7 * 24 * 3600  # 7天

    def test_get_ttl_index_config_custom(self):
        """测试获取自定义 TTL 配置"""
        record = MNotificationRecord(
            message_id="test",
            content="Content",
            ttl_days=14
        )

        ttl_config = record.get_ttl_index_config()

        assert ttl_config["expireAfterSeconds"] == 14 * 24 * 3600  # 14天


@pytest.mark.unit
class TestNotificationRecordMongoDB:
    """MNotificationRecord MongoDB 转换测试"""

    def test_model_dump_mongo(self):
        """测试转换为 MongoDB 文档"""
        record = MNotificationRecord(
            message_id="test_msg",
            content="Test content",
            content_type="markdown",
            channels=["discord"],
            status=NOTIFICATION_STATUS_TYPES.SENT.value,
            priority=2,
            user_uuid="user_123",
            template_id="template_123"
        )

        doc = record.model_dump_mongo()

        assert doc["uuid"] == record.uuid
        assert doc["message_id"] == "test_msg"
        assert doc["content_type"] == "markdown"
        assert doc["channels"] == ["discord"]
        assert doc["priority"] == 2
        assert doc["user_uuid"] == "user_123"

    def test_from_mongo(self):
        """测试从 MongoDB 文档创建"""
        doc = {
            "uuid": "abc123" * 5,
            "message_id": "msg_123",
            "content": "Content",
            "content_type": "text",
            "channels": ["email"],
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

        record = MNotificationRecord.from_mongo(doc)

        assert record.message_id == "msg_123"
        assert record.status == NOTIFICATION_STATUS_TYPES.SENT.value

    def test_from_mongo_with_sent_at_string(self):
        """测试从字符串格式的 sent_at 创建"""
        sent_at_str = "2025-01-01T12:00:00"
        doc = {
            "uuid": "abc123" * 5,
            "message_id": "msg_123",
            "content": "Content",
            "content_type": "text",
            "channels": [],
            "status": NOTIFICATION_STATUS_TYPES.PENDING.value,
            "channel_results": "{}",
            "priority": 1,
            "user_uuid": None,
            "template_id": None,
            "error_message": None,
            "sent_at": sent_at_str,
            "ttl_days": 7,
            "meta": "{}",
            "desc": "",
            "create_at": "2025-01-01T12:00:00",
            "update_at": "2025-01-01T12:00:00",
            "is_del": False,
            "source": SOURCE_TYPES.OTHER.value
        }

        record = MNotificationRecord.from_mongo(doc)

        assert isinstance(record.sent_at, datetime)


@pytest.mark.unit
class TestNotificationRecordRepr:
    """MNotificationRecord 字符串表示测试"""

    def test_repr_sent(self):
        """测试已发送状态的字符串表示"""
        record = MNotificationRecord(
            message_id="test_msg",
            content="Content",
            status=NOTIFICATION_STATUS_TYPES.SENT.value,
            channels=["discord", "email"]
        )

        repr_str = repr(record)
        assert "MNotificationRecord" in repr_str
        assert "test_msg" in repr_str
        assert "SENT" in repr_str
        assert "discord" in repr_str

    def test_repr_failed(self):
        """测试失败状态的字符串表示"""
        record = MNotificationRecord(
            message_id="test_msg",
            content="Content",
            status=NOTIFICATION_STATUS_TYPES.FAILED.value,
            channels=["email"]
        )

        repr_str = repr(record)
        assert "FAILED" in repr_str
