# Upstream: None
# Downstream: None
# Role: MessageQueue单元测试验证消息队列功能


"""
MessageQueue Unit Tests

测试覆盖:
- 消息队列初始化
- 发送通知到 Kafka
- 批量发送
- Kafka 可用性检查
- 消息序列化
"""

import pytest
from unittest.mock import Mock, patch, MagicMock, PropertyMock
from datetime import datetime

from ginkgo.notifier.core.message_queue import MessageQueue, NotificationPriority, send_notification_to_queue


@pytest.mark.unit
class TestMessageQueueInit:
    """MessageQueue 初始化测试"""

    @patch('ginkgo.data.crud.KafkaCRUD')
    def test_init_default(self, mock_kafka_crud_class):
        """测试默认初始化"""
        mock_instance = Mock()
        mock_kafka_crud_class.return_value = mock_instance

        queue = MessageQueue()

        assert queue.kafka_crud == mock_instance
        assert queue._kafka_available is None

    def test_init_with_crud(self):
        """测试使用自定义 CRUD 初始化"""
        mock_crud = Mock()
        queue = MessageQueue(kafka_crud=mock_crud)

        assert queue.kafka_crud == mock_crud


@pytest.mark.unit
class TestMessageQueueSend:
    """MessageQueue 发送测试"""

    def test_send_notification_success(self):
        """测试成功发送通知"""
        mock_crud = Mock()
        mock_crud.send_message.return_value = True
        mock_crud._test_connection.return_value = True

        queue = MessageQueue(kafka_crud=mock_crud)

        result = queue.send_notification(
            content="Test message",
            channels=["email"],
            user_uuid="user-123"
        )

        assert result is True
        mock_crud.send_message.assert_called_once()
        call_args = mock_crud.send_message.call_args
        assert call_args[1]["topic"] == "notifications"
        assert call_args[1]["key"] == "user-123"

    def test_send_notification_kafka_unavailable(self):
        """测试 Kafka 不可用"""
        mock_crud = Mock()
        mock_crud._test_connection.return_value = False

        queue = MessageQueue(kafka_crud=mock_crud)

        result = queue.send_notification(
            content="Test message",
            channels=["email"],
            user_uuid="user-123"
        )

        assert result is False
        mock_crud.send_message.assert_not_called()

    def test_send_notification_failure(self):
        """测试发送失败"""
        mock_crud = Mock()
        mock_crud.send_message.return_value = False
        mock_crud._test_connection.return_value = True

        queue = MessageQueue(kafka_crud=mock_crud)

        result = queue.send_notification(
            content="Test message",
            channels=["email"],
            user_uuid="user-123"
        )

        assert result is False

    def test_send_batch_success(self):
        """测试批量发送成功"""
        mock_crud = Mock()
        mock_crud.send_batch_messages.return_value = 3
        mock_crud._test_connection.return_value = True

        queue = MessageQueue(kafka_crud=mock_crud)

        notifications = [
            {
                "content": f"Message {i}",
                "channels": ["email"],
                "user_uuid": f"user-{i}"
            }
            for i in range(3)
        ]

        result = queue.send_batch(notifications)

        assert result == 3
        mock_crud.send_batch_messages.assert_called_once()


@pytest.mark.unit
class TestMessageQueueBuildMessage:
    """MessageQueue 消息构建测试"""

    def test_build_message_basic(self):
        """测试基本消息构建"""
        mock_crud = Mock()
        queue = MessageQueue(kafka_crud=mock_crud)

        message = queue._build_message(
            content="Test content",
            channels=["email", "discord"],
            user_uuid="user-123",
            content_type="text",
            priority=1
        )

        assert "content" in message
        assert message["content"] == "Test content"
        assert message["channels"] == ["email", "discord"]
        assert message["metadata"]["user_uuid"] == "user-123"
        assert message["priority"] == 1
        assert "message_id" in message
        assert "timestamp" in message

    def test_build_message_with_template(self):
        """测试带模板的消息构建"""
        mock_crud = Mock()
        queue = MessageQueue(kafka_crud=mock_crud)

        message = queue._build_message(
            content="Signal: {{symbol}}",
            channels=["discord"],
            user_uuid="user-123",
            template_id="trading_signal",
            title="Trading Signal",
            symbol="AAPL",
            price=150.0
        )

        assert message["metadata"]["template_id"] == "trading_signal"
        assert message["metadata"]["title"] == "Trading Signal"
        assert message["kwargs"]["symbol"] == "AAPL"
        assert message["kwargs"]["price"] == 150.0


@pytest.mark.unit
class TestMessageQueueAvailability:
    """MessageQueue 可用性测试"""

    def test_is_available_true(self):
        """测试 Kafka 可用"""
        mock_crud = Mock()
        mock_crud._test_connection.return_value = True

        queue = MessageQueue(kafka_crud=mock_crud)

        assert queue.is_available is True
        assert queue._kafka_available is True

    def test_is_available_false(self):
        """测试 Kafka 不可用"""
        mock_crud = Mock()
        mock_crud._test_connection.return_value = False

        queue = MessageQueue(kafka_crud=mock_crud)

        assert queue.is_available is False
        assert queue._kafka_available is False


@pytest.mark.unit
class TestMessageQueueStatus:
    """MessageQueue 状态测试"""

    def test_get_queue_status_available(self):
        """测试获取队列状态（可用）"""
        mock_crud = Mock()
        mock_crud._test_connection.return_value = True
        mock_crud.get_topic_info.return_value = {"topic": "notifications"}
        mock_crud.get_message_count.return_value = 100

        queue = MessageQueue(kafka_crud=mock_crud)

        status = queue.get_queue_status()

        assert status["topic"] == "notifications"
        assert status["available"] is True
        assert status["topic_exists"] is True
        assert status["message_count"] == 100

    def test_get_queue_status_unavailable(self):
        """测试获取队列状态（不可用）"""
        mock_crud = Mock()
        mock_crud._test_connection.return_value = False

        queue = MessageQueue(kafka_crud=mock_crud)

        status = queue.get_queue_status()

        assert status["topic"] == "notifications"
        assert status["available"] is False
        assert status["message_count"] == 0


@pytest.mark.unit
class TestMessageQueuePriority:
    """NotificationPriority 枚举测试"""

    def test_priority_values(self):
        """测试优先级枚举值"""
        assert NotificationPriority.LOW == 0
        assert NotificationPriority.NORMAL == 1
        assert NotificationPriority.HIGH == 2
        assert NotificationPriority.URGENT == 3


@pytest.mark.unit
class TestConvenienceFunctions:
    """便捷函数测试"""

    def test_send_notification_to_queue(self):
        """测试便捷函数"""
        with patch('ginkgo.notifier.core.message_queue.MessageQueue') as mock_queue_class:
            mock_queue = Mock()
            mock_queue.send_notification.return_value = True
            mock_queue_class.return_value = mock_queue

            result = send_notification_to_queue(
                content="Test",
                channels=["email"],
                user_uuid="user-123"
            )

            assert result is True
            mock_queue.send_notification.assert_called_once()
