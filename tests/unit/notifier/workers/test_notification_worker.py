# Upstream: None
# Downstream: None
# Role: NotificationWorker单元测试验证Kafka Worker功能


"""
NotificationWorker Unit Tests

测试覆盖：
- Worker 初始化
- Worker 启动和停止
- 消息处理（Discord/Email）
- 重试逻辑
- 结果记录
- 统计信息
"""

import pytest
import time
import threading
from unittest.mock import Mock, patch, MagicMock, call
from datetime import datetime

from ginkgo.notifier.workers.notification_worker import (
    NotificationWorker,
    WorkerStatus,
    create_notification_worker
)


@pytest.mark.unit
class TestNotificationWorkerInit:
    """NotificationWorker 初始化测试"""

    def test_init_default(self):
        """测试默认初始化"""
        record_crud = Mock()

        worker = NotificationWorker(record_crud=record_crud)

        assert worker.record_crud == record_crud
        assert worker._group_id == "notification_worker_group"
        assert worker.status == WorkerStatus.STOPPED
        assert worker.is_running is False

    def test_init_with_group_id(self):
        """测试使用自定义 group_id"""
        record_crud = Mock()

        worker = NotificationWorker(
            record_crud=record_crud,
            group_id="custom_group"
        )

        assert worker._group_id == "custom_group"

    def test_stats_initial(self):
        """测试初始统计信息"""
        record_crud = Mock()
        worker = NotificationWorker(record_crud=record_crud)

        stats = worker.stats

        assert stats["messages_consumed"] == 0
        assert stats["messages_sent"] == 0
        assert stats["messages_failed"] == 0
        assert stats["messages_retried"] == 0


@pytest.mark.unit
class TestNotificationWorkerLifecycle:
    """NotificationWorker 生命周期测试"""

    @patch('ginkgo.notifier.workers.notification_worker.GinkgoConsumer')
    def test_start_success(self, mock_consumer_class):
        """测试成功启动 Worker"""
        record_crud = Mock()

        # Mock consumer
        mock_consumer = Mock()
        mock_consumer.consumer.poll.return_value = {}
        mock_consumer_class.return_value = mock_consumer

        worker = NotificationWorker(record_crud=record_crud)

        result = worker.start()

        assert result is True
        assert worker.status == WorkerStatus.RUNNING
        assert worker.is_running is True
        mock_consumer_class.assert_called_once()

    def test_start_when_running(self):
        """测试重复启动"""
        record_crud = Mock()
        worker = NotificationWorker(record_crud=record_crud)

        # 模拟正在运行
        worker._status = WorkerStatus.RUNNING

        result = worker.start()

        assert result is False

    @patch('ginkgo.notifier.workers.notification_worker.GinkgoConsumer')
    def test_stop_success(self, mock_consumer_class):
        """测试成功停止 Worker"""
        record_crud = Mock()

        # Mock consumer
        mock_consumer = Mock()
        mock_consumer.consumer.poll.return_value = {}
        mock_consumer_class.return_value = mock_consumer

        worker = NotificationWorker(record_crud=record_crud)
        worker.start()

        # 等待线程启动
        time.sleep(0.1)

        result = worker.stop(timeout=1.0)

        assert result is True
        assert worker.status == WorkerStatus.STOPPED

    def test_stop_when_not_running(self):
        """测试停止未运行的 Worker"""
        record_crud = Mock()
        worker = NotificationWorker(record_crud=record_crud)

        result = worker.stop()

        assert result is False


@pytest.mark.unit
class TestNotificationWorkerProcessMessage:
    """NotificationWorker 消息处理测试"""

    def test_process_message_webhook_success(self):
        """测试处理 Webhook 消息成功"""
        record_crud = Mock()
        worker = NotificationWorker(record_crud=record_crud)

        message = {
            "message_id": "msg_123",
            "content": "Test webhook message",
            "channels": ["webhook"],
            "metadata": {
                "title": "Test Title"
            },
            "kwargs": {
                "webhook_url": "https://example.com/webhook"
            }
        }

        # Mock record_crud.update_status
        record_crud.update_status.return_value = 1

        with patch('ginkgo.notifier.workers.notification_worker.WebhookChannel') as mock_channel_class:
            mock_channel = Mock()
            mock_channel.send.return_value = Mock(
                success=True,
                to_dict=lambda: {"success": True}
            )
            mock_channel_class.return_value = mock_channel

            result = worker._process_message(message)

            assert result is True
            mock_channel.send.assert_called_once()

    def test_process_message_email_success(self):
        """测试处理 Email 消息成功"""
        record_crud = Mock()
        worker = NotificationWorker(record_crud=record_crud)

        message = {
            "message_id": "msg_456",
            "content": "Test email message",
            "channels": ["email"],
            "metadata": {
                "title": "Test Email"
            },
            "kwargs": {
                "to": "test@example.com"
            }
        }

        # Mock record_crud.update_status
        record_crud.update_status.return_value = 1

        with patch('ginkgo.notifier.workers.notification_worker.EmailChannel') as mock_channel_class:
            mock_channel = Mock()
            mock_channel.send.return_value = Mock(
                success=True,
                to_dict=lambda: {"success": True}
            )
            mock_channel_class.return_value = mock_channel

            result = worker._process_message(message)

            assert result is True
            mock_channel.send.assert_called_once()

    def test_process_message_multiple_channels(self):
        """测试处理多渠道消息"""
        record_crud = Mock()
        worker = NotificationWorker(record_crud=record_crud)

        message = {
            "message_id": "msg_789",
            "content": "Test multi-channel message",
            "channels": ["webhook", "email"],
            "metadata": {},
            "kwargs": {
                "webhook_url": "https://example.com/webhook",
                "to": "test@example.com"
            }
        }

        # Mock record_crud.update_status
        record_crud.update_status.return_value = 1

        with patch('ginkgo.notifier.workers.notification_worker.WebhookChannel') as mock_webhook_class, \
             patch('ginkgo.notifier.workers.notification_worker.EmailChannel') as mock_email_class:

            mock_webhook = Mock()
            mock_webhook.send.return_value = Mock(
                success=True,
                to_dict=lambda: {"success": True}
            )
            mock_webhook_class.return_value = mock_webhook

            mock_email = Mock()
            mock_email.send.return_value = Mock(
                success=True,
                to_dict=lambda: {"success": True}
            )
            mock_email_class.return_value = mock_email

            result = worker._process_message(message)

            assert result is True
            mock_webhook.send.assert_called_once()
            mock_email.send.assert_called_once()

    def test_process_message_invalid(self):
        """测试处理无效消息"""
        record_crud = Mock()
        worker = NotificationWorker(record_crud=record_crud)

        message = {
            "message_id": "msg_invalid",
            "channels": ["webhook"]
            # 缺少 content
        }

        result = worker._process_message(message)

        assert result is False


@pytest.mark.unit
class TestNotificationWorkerSendToChannel:
    """NotificationWorker 渠道发送测试"""

    def test_send_to_webhook(self):
        """测试发送到 Webhook"""
        record_crud = Mock()
        worker = NotificationWorker(record_crud=record_crud)

        with patch('ginkgo.notifier.workers.notification_worker.WebhookChannel') as mock_channel_class:
            mock_channel = Mock()
            mock_channel.send.return_value = Mock(success=True)
            mock_channel_class.return_value = mock_channel

            result = worker._send_to_channel(
                channel_name="webhook",
                content="Test content",
                webhook_url="https://example.com/webhook"
            )

            assert result.success is True
            mock_channel.send.assert_called_once()

    def test_send_to_email(self):
        """测试发送到 Email"""
        record_crud = Mock()
        worker = NotificationWorker(record_crud=record_crud)

        with patch('ginkgo.notifier.workers.notification_worker.EmailChannel') as mock_channel_class:
            mock_channel = Mock()
            mock_channel.send.return_value = Mock(success=True)
            mock_channel_class.return_value = mock_channel

            result = worker._send_to_channel(
                channel_name="email",
                content="Test content",
                to="test@example.com"
            )

            assert result.success is True
            mock_channel.send.assert_called_once()

    def test_send_to_unknown_channel(self):
        """测试发送到未知渠道"""
        record_crud = Mock()
        worker = NotificationWorker(record_crud=record_crud)

        result = worker._send_to_channel(
            channel_name="unknown",
            content="Test content"
        )

        assert result.success is False
        assert "Unknown channel" in result.error


@pytest.mark.unit
class TestNotificationWorkerUpdateRecord:
    """NotificationWorker 记录更新测试"""

    def test_update_record_all_success(self):
        """测试更新记录（全部成功）"""
        record_crud = Mock()
        worker = NotificationWorker(record_crud=record_crud)

        worker._update_record_status(
            message_id="msg_123",
            channel_results={"webhook": {"success": True}},
            success_count=1,
            total_channels=1
        )

        record_crud.update_status.assert_called_once()
        call_args = record_crud.update_status.call_args
        assert call_args[1]["status"] == 1  # SENT

    def test_update_record_all_failed(self):
        """测试更新记录（全部失败）"""
        record_crud = Mock()
        worker = NotificationWorker(record_crud=record_crud)

        worker._update_record_status(
            message_id="msg_456",
            channel_results={"webhook": {"success": False}},
            success_count=0,
            total_channels=1
        )

        record_crud.update_status.assert_called_once()
        call_args = record_crud.update_status.call_args
        assert call_args[1]["status"] == 2  # FAILED


@pytest.mark.unit
class TestNotificationWorkerHealthStatus:
    """NotificationWorker 健康状态测试"""

    def test_get_health_status_stopped(self):
        """测试获取健康状态（已停止）"""
        record_crud = Mock()
        worker = NotificationWorker(record_crud=record_crud)

        status = worker.get_health_status()

        assert status["status"] == "STOPPED"
        assert status["is_running"] is False
        assert status["messages_consumed"] == 0

    @patch('ginkgo.notifier.workers.notification_worker.GinkgoConsumer')
    def test_get_health_status_running(self, mock_consumer_class):
        """测试获取健康状态（运行中）"""
        record_crud = Mock()

        # Mock consumer
        mock_consumer = Mock()
        mock_consumer.consumer.poll.return_value = {}
        mock_consumer_class.return_value = mock_consumer

        worker = NotificationWorker(record_crud=record_crud)
        worker.start()

        # 等待线程启动
        time.sleep(0.1)

        status = worker.get_health_status()

        assert status["status"] == "RUNNING"
        assert status["is_running"] is True
        assert status["group_id"] == "notification_worker_group"

        worker.stop(timeout=1.0)


@pytest.mark.unit
class TestConvenienceFunctions:
    """便捷函数测试"""

    def test_create_notification_worker(self):
        """测试创建 Worker 便捷函数"""
        record_crud = Mock()

        worker = create_notification_worker(record_crud=record_crud)

        assert isinstance(worker, NotificationWorker)
        assert worker.record_crud == record_crud

    def test_create_notification_worker_with_group_id(self):
        """测试创建 Worker 便捷函数（带 group_id）"""
        record_crud = Mock()

        worker = create_notification_worker(
            record_crud=record_crud,
            group_id="custom_group"
        )

        assert isinstance(worker, NotificationWorker)
        assert worker._group_id == "custom_group"
