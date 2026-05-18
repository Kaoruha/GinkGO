# Upstream: None
# Downstream: None
# Role: NotificationDeliveryService 单元测试验证通知交付服务业务逻辑
# Issue #3920

"""
NotificationDeliveryService Unit Tests

测试覆盖:
- 服务初始化和渠道注册
- 基本通知发送
- 批量用户通知
- 模板通知发送
- 通知历史查询
- 错误处理
- Kafka 降级机制
"""

import pytest
from unittest.mock import Mock, patch, MagicMock

from ginkgo.notifier.core.notification_service import NotificationDeliveryService
from ginkgo.notifier.channels.base_channel import ChannelResult
from ginkgo.data.services.base_service import ServiceResult
from ginkgo.enums import NOTIFICATION_STATUS_TYPES


def _make_service(**overrides):
    """构建测试用 NotificationDeliveryService 实例"""
    defaults = dict(
        notification_service=Mock(),
        template_engine=Mock(),
        user_service=Mock(),
        user_group_service=Mock(),
    )
    defaults.update(overrides)
    return NotificationDeliveryService(**defaults)


@pytest.mark.unit
class TestNotificationDeliveryServiceInit:
    """NotificationDeliveryService 初始化测试"""

    def test_init(self):
        notification_service = Mock()
        template_engine = Mock()
        user_service = Mock()
        user_group_service = Mock()

        service = NotificationDeliveryService(
            notification_service=notification_service,
            template_engine=template_engine,
            user_service=user_service,
            user_group_service=user_group_service
        )

        assert service._notification_service == notification_service
        assert service.template_engine == template_engine
        assert service.user_service == user_service
        assert service.user_group_service == user_group_service
        assert service._channels == {}


@pytest.mark.unit
class TestChannelRegistration:
    """渠道注册测试"""

    def test_register_channel(self):
        service = _make_service()
        mock_channel = Mock()
        mock_channel.channel_name = "test_channel"

        service.register_channel(mock_channel)

        assert "test_channel" in service._channels
        assert service.get_channel("test_channel") == mock_channel

    def test_get_channel_not_found(self):
        service = _make_service()
        assert service.get_channel("nonexistent") is None


@pytest.mark.unit
class TestSend:
    """通知发送测试"""

    def test_send_success_single_channel(self):
        notification_service = Mock()
        notification_service.create_record.return_value = ServiceResult.success({"uuid": "record_uuid_123"})
        notification_service.update_record_status.return_value = ServiceResult.success({"updated": True})

        service = _make_service(notification_service=notification_service)
        mock_channel = Mock()
        mock_channel.channel_name = "discord"
        mock_channel.send.return_value = ChannelResult(success=True, message_id="discord_msg_123")
        service.register_channel(mock_channel)

        result = service.send(content="Test message", channels="discord")

        assert result.success is True
        assert result.data["success_count"] == 1
        assert result.data["total_channels"] == 1
        notification_service.create_record.assert_called_once()
        notification_service.update_record_status.assert_called_once()

    def test_send_success_multiple_channels(self):
        notification_service = Mock()
        notification_service.create_record.return_value = ServiceResult.success({"uuid": "record_uuid_123"})
        notification_service.update_record_status.return_value = ServiceResult.success({"updated": True})

        service = _make_service(notification_service=notification_service)

        mock_discord = Mock()
        mock_discord.channel_name = "discord"
        mock_discord.send.return_value = ChannelResult(success=True, message_id="discord_msg")

        mock_email = Mock()
        mock_email.channel_name = "email"
        mock_email.send.return_value = ChannelResult(success=True, message_id="email_msg")

        service.register_channel(mock_discord)
        service.register_channel(mock_email)

        result = service.send(content="Test message", channels=["discord", "email"])

        assert result.success is True
        assert result.data["success_count"] == 2
        assert result.data["total_channels"] == 2

    def test_send_channel_not_found(self):
        notification_service = Mock()
        notification_service.create_record.return_value = ServiceResult.success({"uuid": "record_uuid_123"})
        notification_service.update_record_status.return_value = ServiceResult.success({"updated": True})

        service = _make_service(notification_service=notification_service)

        result = service.send(content="Test message", channels="nonexistent_channel")

        assert result.success is True
        assert result.data["success_count"] == 0

    def test_send_channel_failure(self):
        notification_service = Mock()
        notification_service.create_record.return_value = ServiceResult.success({"uuid": "record_uuid_123"})
        notification_service.update_record_status.return_value = ServiceResult.success({"updated": True})

        service = _make_service(notification_service=notification_service)
        mock_channel = Mock()
        mock_channel.channel_name = "discord"
        mock_channel.send.return_value = ChannelResult(success=False, error="Webhook timeout")
        service.register_channel(mock_channel)

        result = service.send(content="Test message", channels="discord")

        assert result.success is True
        assert result.data["success_count"] == 0
        assert result.data["channel_results"]["discord"]["success"] is False

    def test_send_record_creation_failure(self):
        notification_service = Mock()
        notification_service.create_record.return_value = ServiceResult.error("DB error")

        service = _make_service(notification_service=notification_service)

        result = service.send(content="Test message", channels="discord")

        assert result.success is False
        assert "Failed to create notification record" in result.error


@pytest.mark.unit
class TestSendToUsers:
    """批量发送测试"""

    def test_send_to_users(self):
        notification_service = Mock()
        notification_service.create_record.return_value = ServiceResult.success({"uuid": "test_uuid"})
        notification_service.update_record_status.return_value = ServiceResult.success({"updated": True})

        service = _make_service(notification_service=notification_service)
        mock_channel = Mock()
        mock_channel.channel_name = "test"
        mock_channel.send.return_value = Mock(success=True, message_id="test_msg", to_dict=lambda: {"success": True})
        service.register_channel(mock_channel)

        result = service.send_to_users(
            user_uuids=["user1", "user2", "user3"],
            content="Batch message",
            channels="test"
        )

        assert result.success is True
        assert result.data["total_users"] == 3
        assert result.data["success_count"] == 3


@pytest.mark.unit
class TestSendTemplate:
    """模板发送测试"""

    def test_send_template_success(self):
        notification_service = Mock()
        notification_service.create_record.return_value = ServiceResult.success({"uuid": "record_uuid_123"})
        notification_service.update_record_status.return_value = ServiceResult.success({"updated": True})

        template_engine = Mock()
        rendered_content = "Rendered content"
        template_engine.render_from_template_id.return_value = rendered_content
        template_engine.render.return_value = rendered_content

        mock_template = Mock()
        mock_template.subject = "Test Subject"
        mock_template.content = "Template raw content"
        mock_enum = Mock()
        mock_enum.name = "TEXT"
        mock_template.get_template_type_enum.return_value = mock_enum
        notification_service.get_template_by_id.return_value = ServiceResult.success(mock_template)

        service = _make_service(
            notification_service=notification_service,
            template_engine=template_engine,
        )

        mock_channel = Mock()
        mock_channel.channel_name = "discord"
        mock_channel.send.return_value = ChannelResult(success=True, message_id="discord_msg_123")
        service.register_channel(mock_channel)

        result = service.send_template(
            template_id="test_template",
            context={"name": "Test"},
            channels="discord"
        )

        assert result.success is True
        template_engine.render_from_template_id.assert_called_once()
        mock_channel.send.assert_called_once()
        call_kwargs = mock_channel.send.call_args
        assert call_kwargs.kwargs.get("content") == rendered_content
        assert call_kwargs.kwargs.get("title") == "Test Subject"

    def test_send_template_not_found(self):
        notification_service = Mock()
        notification_service.get_template_by_id.return_value = ServiceResult.error("Template not found")

        service = _make_service(notification_service=notification_service)

        result = service.send_template(
            template_id="nonexistent",
            context={},
            channels="discord"
        )

        assert result.success is False
        assert "not found" in result.error.lower()

    def test_send_template_render_error(self):
        template_engine = Mock()
        template_engine.render_from_template_id.side_effect = ValueError("Syntax error")

        service = _make_service(template_engine=template_engine)

        result = service.send_template(
            template_id="test_template",
            context={},
            channels="discord"
        )

        assert result.success is False
        assert "Template error" in result.error


@pytest.mark.unit
class TestGetHistory:
    """历史记录查询测试"""

    def test_get_notification_history(self):
        mock_records = [
            Mock(model_dump=lambda: {"message_id": "msg1"}),
            Mock(model_dump=lambda: {"message_id": "msg2"})
        ]
        notification_service = Mock()
        notification_service.get_records_by_user.return_value = ServiceResult.success(mock_records)

        service = _make_service(notification_service=notification_service)

        result = service.get_notification_history(user_uuid="user_123", limit=100)

        assert result.success is True
        assert result.data["count"] == 2
        assert result.data["user_uuid"] == "user_123"
        assert len(result.data["records"]) == 2

    def test_get_notification_history_with_status(self):
        mock_records = [Mock(model_dump=lambda: {"message_id": "msg1"})]
        notification_service = Mock()
        notification_service.get_records_by_user.return_value = ServiceResult.success(mock_records)

        service = _make_service(notification_service=notification_service)

        result = service.get_notification_history(
            user_uuid="user_123",
            limit=100,
            status=NOTIFICATION_STATUS_TYPES.FAILED.value
        )

        assert result.success is True
        notification_service.get_records_by_user.assert_called_once_with(
            user_uuid="user_123",
            limit=100,
            status=NOTIFICATION_STATUS_TYPES.FAILED.value
        )


@pytest.mark.unit
class TestGetFailed:
    """失败记录查询测试"""

    def test_get_failed_notifications(self):
        mock_records = [
            Mock(model_dump=lambda: {"message_id": "failed1"}),
            Mock(model_dump=lambda: {"message_id": "failed2"})
        ]
        notification_service = Mock()
        notification_service.get_recent_failed_records.return_value = ServiceResult.success(mock_records)

        service = _make_service(notification_service=notification_service)

        result = service.get_failed_notifications(limit=50)

        assert result.success is True
        assert result.data["count"] == 2
        notification_service.get_recent_failed_records.assert_called_once_with(limit=50)


@pytest.mark.unit
class TestKafkaDegradation:
    """Kafka 降级机制测试"""

    def test_kafka_degradation_on_unavailable(self):
        notification_service = Mock()
        notification_service.create_record.return_value = ServiceResult.success({"uuid": "record_1"})
        notification_service.update_record_status.return_value = ServiceResult.success({"updated": True})

        kafka_producer = Mock()
        kafka_health_checker = Mock()
        kafka_health_checker.should_degrade.return_value = True
        kafka_health_checker.get_health_summary.return_value = {"healthy": False, "reason": "No brokers available"}

        service = _make_service(
            notification_service=notification_service,
            kafka_producer=kafka_producer,
            kafka_health_checker=kafka_health_checker,
        )
        mock_channel = Mock()
        mock_channel.channel_name = "discord"
        mock_channel.send.return_value = ChannelResult(success=True, message_id="test_msg_1")
        service.register_channel(mock_channel)

        result = service.send_async(content="Test content", channels=["discord"])

        assert result.success is True
        kafka_producer.send_async.assert_not_called()
        kafka_health_checker.should_degrade.assert_called_once()
        kafka_health_checker.get_health_summary.assert_called_once()

    def test_kafka_no_degradation_when_healthy(self):
        kafka_producer = Mock()
        kafka_health_checker = Mock()
        kafka_health_checker.should_degrade.return_value = False
        kafka_producer.send_async.return_value = True
        kafka_producer.flush = Mock()

        service = _make_service(
            kafka_producer=kafka_producer,
            kafka_health_checker=kafka_health_checker,
        )

        result = service.send_async(content="Test content", channels=["discord"])

        assert result.success is True
        kafka_producer.send_async.assert_called_once()
        kafka_health_checker.should_degrade.assert_called_once()

    def test_kafka_force_async_fails_when_degraded(self):
        kafka_producer = Mock()
        kafka_health_checker = Mock()
        kafka_health_checker.should_degrade.return_value = True
        kafka_health_checker.get_health_summary.return_value = {"healthy": False, "reason": "Connection timeout"}

        service = _make_service(
            kafka_producer=kafka_producer,
            kafka_health_checker=kafka_health_checker,
        )

        result = service.send_async(
            content="Test content",
            channels=["discord"],
            force_async=True
        )

        assert result.success is False
        assert "Kafka unavailable" in result.error

    def test_kafka_send_async_failure_degrades_to_sync(self):
        notification_service = Mock()
        notification_service.create_record.return_value = ServiceResult.success({"uuid": "record_1"})
        notification_service.update_record_status.return_value = ServiceResult.success({"updated": True})

        kafka_producer = Mock()
        kafka_health_checker = Mock()
        kafka_health_checker.should_degrade.return_value = False
        kafka_producer.send_async.return_value = False

        service = _make_service(
            notification_service=notification_service,
            kafka_producer=kafka_producer,
            kafka_health_checker=kafka_health_checker,
        )
        mock_channel = Mock()
        mock_channel.channel_name = "discord"
        mock_channel.send.return_value = ChannelResult(success=True, message_id="test_msg_1")
        service.register_channel(mock_channel)

        result = service.send_async(content="Test content", channels=["discord"])

        assert result.success is True
        kafka_producer.send_async.assert_called_once()

    def test_kafka_health_check_methods(self):
        kafka_producer = Mock()
        kafka_health_checker = Mock()
        kafka_health_checker.check_health.return_value = {
            "healthy": True, "broker_reachable": True, "topic_exists": True
        }
        kafka_health_checker.get_health_summary.return_value = "All systems operational"
        kafka_health_checker.should_degrade.return_value = False

        service = _make_service(
            kafka_producer=kafka_producer,
            kafka_health_checker=kafka_health_checker,
        )

        health = service.check_kafka_health()
        assert health["healthy"] is True
        kafka_health_checker.check_health.assert_called_once()

        status = service.get_kafka_status()
        assert status["enabled"] is True
        assert status["healthy"] is True
        assert status["should_degrade"] is False
        assert status["health_summary"] == "All systems operational"

    def test_kafka_health_check_not_configured(self):
        service = _make_service(kafka_producer=None, kafka_health_checker=None)

        health = service.check_kafka_health()
        assert health["configured"] is False
        assert "not configured" in health["message"]

        status = service.get_kafka_status()
        assert status["enabled"] is False
