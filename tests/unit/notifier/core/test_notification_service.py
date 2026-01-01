# Upstream: None
# Downstream: None
# Role: NotificationService单元测试验证通知服务业务逻辑功能


"""
NotificationService Unit Tests

测试覆盖:
- 服务初始化和渠道注册
- 基本通知发送
- 批量用户通知
- 模板通知发送
- 通知历史查询
- 错误处理
"""

import pytest
from unittest.mock import Mock, patch, MagicMock

from ginkgo.notifier.core.notification_service import NotificationService
from ginkgo.notifier.channels.base_channel import ChannelResult
from ginkgo.data.models import MNotificationRecord
from ginkgo.enums import NOTIFICATION_STATUS_TYPES


@pytest.mark.unit
class TestNotificationServiceInit:
    """NotificationService 初始化测试"""

    def test_init(self):
        """测试初始化"""
        template_crud = Mock()
        record_crud = Mock()
        template_engine = Mock()

        service = NotificationService(
            user_service=Mock(),
            user_group_service=Mock(),
            template_crud=template_crud,
            record_crud=record_crud,
            template_engine=template_engine
        )

        assert service.template_crud == template_crud
        assert service.record_crud == record_crud
        assert service.template_engine == template_engine
        assert service._channels == {}


@pytest.mark.unit
class TestNotificationServiceChannelRegistration:
    """NotificationService 渠道注册测试"""

    def test_register_channel(self):
        """测试注册渠道"""
        template_crud = Mock()
        record_crud = Mock()
        template_engine = Mock()

        service = NotificationService(
            user_service=Mock(),
            user_group_service=Mock(),
            template_crud=template_crud,
            record_crud=record_crud,
            template_engine=template_engine
        )

        mock_channel = Mock()
        mock_channel.channel_name = "test_channel"

        service.register_channel(mock_channel)

        assert "test_channel" in service._channels
        assert service.get_channel("test_channel") == mock_channel

    def test_get_channel_not_found(self):
        """测试获取不存在的渠道"""
        template_crud = Mock()
        record_crud = Mock()
        template_engine = Mock()

        service = NotificationService(
            user_service=Mock(),
            user_group_service=Mock(),
            template_crud=template_crud,
            record_crud=record_crud,
            template_engine=template_engine
        )

        assert service.get_channel("nonexistent") is None


@pytest.mark.unit
class TestNotificationServiceSend:
    """NotificationService 发送测试"""

    def test_send_success_single_channel(self):
        """测试成功发送单个渠道"""
        template_crud = Mock()
        record_crud = Mock()
        template_engine = Mock()

        service = NotificationService(
            user_service=Mock(),
            user_group_service=Mock(),
            template_crud=template_crud,
            record_crud=record_crud,
            template_engine=template_engine
        )

        # Mock record_crud.add
        record_crud.add.return_value = "record_uuid_123"
        record_crud.update_status.return_value = 1

        # Mock channel
        mock_channel = Mock()
        mock_channel.channel_name = "discord"
        mock_channel.send.return_value = ChannelResult(
            success=True,
            message_id="discord_msg_123"
        )

        service.register_channel(mock_channel)

        result = service.send(
            content="Test message",
            channels="discord"
        )

        assert result.success is True
        assert result.data["success_count"] == 1
        assert result.data["total_channels"] == 1
        assert "message_id" in result.data

    def test_send_success_multiple_channels(self):
        """测试成功发送多个渠道"""
        template_crud = Mock()
        record_crud = Mock()
        template_engine = Mock()

        service = NotificationService(
            user_service=Mock(),
            user_group_service=Mock(),
            template_crud=template_crud,
            record_crud=record_crud,
            template_engine=template_engine
        )

        record_crud.add.return_value = "record_uuid_123"
        record_crud.update_status.return_value = 1

        # Mock channels
        mock_discord = Mock()
        mock_discord.channel_name = "discord"
        mock_discord.send.return_value = ChannelResult(
            success=True,
            message_id="discord_msg"
        )

        mock_email = Mock()
        mock_email.channel_name = "email"
        mock_email.send.return_value = ChannelResult(
            success=True,
            message_id="email_msg"
        )

        service.register_channel(mock_discord)
        service.register_channel(mock_email)

        result = service.send(
            content="Test message",
            channels=["discord", "email"]
        )

        assert result.success is True
        assert result.data["success_count"] == 2
        assert result.data["total_channels"] == 2

    def test_send_channel_not_found(self):
        """测试发送到不存在的渠道"""
        template_crud = Mock()
        record_crud = Mock()
        template_engine = Mock()

        service = NotificationService(
            user_service=Mock(),
            user_group_service=Mock(),
            template_crud=template_crud,
            record_crud=record_crud,
            template_engine=template_engine
        )

        record_crud.add.return_value = "record_uuid_123"
        record_crud.update_status.return_value = 1

        result = service.send(
            content="Test message",
            channels="nonexistent_channel"
        )

        assert result.success is True  # 部分成功视为成功
        assert result.data["success_count"] == 0

    def test_send_channel_failure(self):
        """测试渠道发送失败"""
        template_crud = Mock()
        record_crud = Mock()
        template_engine = Mock()

        service = NotificationService(
            user_service=Mock(),
            user_group_service=Mock(),
            template_crud=template_crud,
            record_crud=record_crud,
            template_engine=template_engine
        )

        record_crud.add.return_value = "record_uuid_123"
        record_crud.update_status.return_value = 1

        mock_channel = Mock()
        mock_channel.channel_name = "discord"
        mock_channel.send.return_value = ChannelResult(
            success=False,
            error="Webhook timeout"
        )

        service.register_channel(mock_channel)

        result = service.send(
            content="Test message",
            channels="discord"
        )

        assert result.success is True  # 记录已创建
        assert result.data["success_count"] == 0
        assert result.data["channel_results"]["discord"]["success"] is False

    def test_send_with_record_crud_failure(self):
        """测试记录创建失败"""
        template_crud = Mock()
        record_crud = Mock()
        template_engine = Mock()

        service = NotificationService(
            user_service=Mock(),
            user_group_service=Mock(),
            template_crud=template_crud,
            record_crud=record_crud,
            template_engine=template_engine
        )

        record_crud.add.return_value = None  # 创建失败

        result = service.send(
            content="Test message",
            channels="discord"
        )

        assert result.success is False
        assert "Failed to create notification record" in result.error


@pytest.mark.unit
class TestNotificationServiceSendToUsers:
    """NotificationService 批量发送测试"""

    def test_send_to_users(self):
        """测试向多个用户发送"""
        template_crud = Mock()
        record_crud = Mock()
        template_engine = Mock()

        service = NotificationService(
            user_service=Mock(),
            user_group_service=Mock(),
            template_crud=template_crud,
            record_crud=record_crud,
            template_engine=template_engine
        )

        # 注册一个测试渠道
        mock_channel = Mock()
        mock_channel.channel_name = "test"
        mock_channel.send.return_value = Mock(success=True, message_id="test_msg", to_dict=lambda: {"success": True})
        service.register_channel(mock_channel)

        # Mock CRUD operations
        record_crud.add.return_value = "test_uuid"
        record_crud.update_status.return_value = 1

        result = service.send_to_users(
            user_uuids=["user1", "user2", "user3"],
            content="Batch message",
            channels="test"
        )

        assert result.success is True
        assert result.data["total_users"] == 3
        # 验证每个用户都收到了通知（因为 mock_channel 总是返回 success）
        assert result.data["success_count"] == 3


@pytest.mark.unit
class TestNotificationServiceSendTemplate:
    """NotificationService 模板发送测试"""

    def test_send_template_success(self):
        """测试使用模板发送"""
        template_crud = Mock()
        record_crud = Mock()
        template_engine = Mock()

        service = NotificationService(
            user_service=Mock(),
            user_group_service=Mock(),
            template_crud=template_crud,
            record_crud=record_crud,
            template_engine=template_engine
        )

        # Mock template_engine
        template_engine.render_from_template_id.return_value = "Rendered content"

        # Mock template
        mock_template = Mock()
        mock_template.subject = "Test Subject"
        mock_template.get_template_type_enum.return_value = Mock(name="TEXT")

        template_crud.get_by_template_id.return_value = mock_template

        # Mock send
        service.send = Mock(return_value=Mock(
            success=True,
            data={"message_id": "msg123"}
        ))

        result = service.send_template(
            template_id="test_template",
            context={"name": "Test"},
            channels="discord"
        )

        assert result.success is True
        template_engine.render_from_template_id.assert_called_once()

    def test_send_template_not_found(self):
        """测试模板不存在"""
        template_crud = Mock()
        record_crud = Mock()
        template_engine = Mock()

        service = NotificationService(
            user_service=Mock(),
            user_group_service=Mock(),
            template_crud=template_crud,
            record_crud=record_crud,
            template_engine=template_engine
        )

        template_crud.get_by_template_id.return_value = None

        result = service.send_template(
            template_id="nonexistent",
            context={},
            channels="discord"
        )

        assert result.success is False
        assert "not found" in result.error.lower()

    def test_send_template_render_error(self):
        """测试模板渲染错误"""
        template_crud = Mock()
        record_crud = Mock()
        template_engine = Mock()

        service = NotificationService(
            user_service=Mock(),
            user_group_service=Mock(),
            template_crud=template_crud,
            record_crud=record_crud,
            template_engine=template_engine
        )

        template_engine.render_from_template_id.side_effect = ValueError("Syntax error")

        result = service.send_template(
            template_id="test_template",
            context={},
            channels="discord"
        )

        assert result.success is False
        assert "Template error" in result.error


@pytest.mark.unit
class TestNotificationServiceGetHistory:
    """NotificationService 历史记录测试"""

    def test_get_notification_history(self):
        """测试获取通知历史"""
        template_crud = Mock()
        record_crud = Mock()
        template_engine = Mock()

        service = NotificationService(
            user_service=Mock(),
            user_group_service=Mock(),
            template_crud=template_crud,
            record_crud=record_crud,
            template_engine=template_engine
        )

        mock_records = [
            Mock(model_dump=lambda: {"message_id": "msg1"}),
            Mock(model_dump=lambda: {"message_id": "msg2"})
        ]
        record_crud.get_by_user.return_value = mock_records

        result = service.get_notification_history(
            user_uuid="user_123",
            limit=100
        )

        assert result.success is True
        assert result.data["count"] == 2
        assert result.data["user_uuid"] == "user_123"
        assert len(result.data["records"]) == 2

    def test_get_notification_history_with_status(self):
        """测试带状态过滤的历史查询"""
        template_crud = Mock()
        record_crud = Mock()
        template_engine = Mock()

        service = NotificationService(
            user_service=Mock(),
            user_group_service=Mock(),
            template_crud=template_crud,
            record_crud=record_crud,
            template_engine=template_engine
        )

        mock_records = [Mock(model_dump=lambda: {"message_id": "msg1"})]
        record_crud.get_by_user.return_value = mock_records

        result = service.get_notification_history(
            user_uuid="user_123",
            limit=100,
            status=NOTIFICATION_STATUS_TYPES.FAILED.value
        )

        assert result.success is True
        record_crud.get_by_user.assert_called_once_with(
            user_uuid="user_123",
            limit=100,
            status=NOTIFICATION_STATUS_TYPES.FAILED.value
        )


@pytest.mark.unit
class TestNotificationServiceGetFailed:
    """NotificationService 失败记录测试"""

    def test_get_failed_notifications(self):
        """测试获取失败通知"""
        template_crud = Mock()
        record_crud = Mock()
        template_engine = Mock()

        service = NotificationService(
            user_service=Mock(),
            user_group_service=Mock(),
            template_crud=template_crud,
            record_crud=record_crud,
            template_engine=template_engine
        )

        mock_records = [
            Mock(model_dump=lambda: {"message_id": "failed1"}),
            Mock(model_dump=lambda: {"message_id": "failed2"})
        ]
        record_crud.get_recent_failed.return_value = mock_records

        result = service.get_failed_notifications(limit=50)

        assert result.success is True
        assert result.data["count"] == 2
        record_crud.get_recent_failed.assert_called_once_with(limit=50)
