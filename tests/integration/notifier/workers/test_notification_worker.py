# Upstream: None
# Downstream: None
# Role: NotificationWorker单元测试验证Kafka Worker功能


"""
NotificationWorker Unit Tests

测试覆盖：
- Worker 初始化
- Worker 启动和停止
- 消息处理（通过 NotificationService）
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
        notification_service = Mock()
        record_crud = Mock()

        worker = NotificationWorker(
            notification_service=notification_service,
            record_crud=record_crud
        )

        assert worker.notification_service == notification_service
        assert worker.record_crud == record_crud
        assert worker._group_id == "notification_worker_group"
        assert worker.status == WorkerStatus.STOPPED
        assert worker.is_running is False

    def test_init_with_group_id(self):
        """测试使用自定义 group_id"""
        notification_service = Mock()
        record_crud = Mock()

        worker = NotificationWorker(
            notification_service=notification_service,
            record_crud=record_crud,
            group_id="custom_group"
        )

        assert worker._group_id == "custom_group"

    def test_stats_initial(self):
        """测试初始统计信息"""
        notification_service = Mock()
        record_crud = Mock()
        worker = NotificationWorker(
            notification_service=notification_service,
            record_crud=record_crud
        )

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
        notification_service = Mock()
        record_crud = Mock()

        # Mock consumer
        mock_consumer = Mock()
        mock_consumer.is_connected = True
        mock_consumer.consumer.poll.return_value = {}
        mock_consumer_class.return_value = mock_consumer

        worker = NotificationWorker(
            notification_service=notification_service,
            record_crud=record_crud
        )

        result = worker.start()

        assert result is True
        assert worker.status == WorkerStatus.RUNNING
        assert worker.is_running is True
        mock_consumer_class.assert_called_once()

        # 清理
        worker.stop(timeout=1.0)

    def test_start_when_running(self):
        """测试重复启动"""
        notification_service = Mock()
        record_crud = Mock()
        worker = NotificationWorker(
            notification_service=notification_service,
            record_crud=record_crud
        )

        # 模拟正在运行
        worker._status = WorkerStatus.RUNNING

        result = worker.start()

        assert result is False

    @patch('ginkgo.notifier.workers.notification_worker.GinkgoConsumer')
    def test_stop_success(self, mock_consumer_class):
        """测试成功停止 Worker"""
        notification_service = Mock()
        record_crud = Mock()

        # Mock consumer
        mock_consumer = Mock()
        mock_consumer.is_connected = True
        mock_consumer.consumer.poll.return_value = {}
        mock_consumer_class.return_value = mock_consumer

        worker = NotificationWorker(
            notification_service=notification_service,
            record_crud=record_crud
        )
        worker.start()

        # 等待线程启动
        time.sleep(0.1)

        result = worker.stop(timeout=1.0)

        assert result is True
        assert worker.status == WorkerStatus.STOPPED

    def test_stop_when_not_running(self):
        """测试停止未运行的 Worker"""
        notification_service = Mock()
        record_crud = Mock()
        worker = NotificationWorker(
            notification_service=notification_service,
            record_crud=record_crud
        )

        result = worker.stop()

        assert result is False


@pytest.mark.unit
class TestNotificationWorkerProcessMessage:
    """NotificationWorker 消息处理测试"""

    def test_process_message_simple_success(self):
        """测试处理 simple 消息成功"""
        notification_service = Mock()
        record_crud = Mock()
        worker = NotificationWorker(
            notification_service=notification_service,
            record_crud=record_crud
        )

        message = {
            "message_type": "simple",
            "message_id": "msg_123",
            "user_uuid": "user_123",
            "content": "Test webhook message",
            "title": "Test Title"
        }

        # Mock notification_service.send_to_user
        notification_service.send_to_user.return_value = Mock(success=True)

        result = worker._process_message(message)

        assert result is True
        notification_service.send_to_user.assert_called_once_with(
            user_uuid="user_123",
            content="Test webhook message",
            title="Test Title",
            channels=None,
            priority=1
        )

    def test_process_message_template_success(self):
        """测试处理 template 消息成功"""
        notification_service = Mock()
        record_crud = Mock()
        worker = NotificationWorker(
            notification_service=notification_service,
            record_crud=record_crud
        )

        message = {
            "message_type": "template",
            "message_id": "msg_456",
            "user_uuid": "user_456",
            "template_id": "test_template",
            "context": {"name": "Test User"}
        }

        # Mock notification_service.send_template_to_user
        notification_service.send_template_to_user.return_value = Mock(success=True)

        result = worker._process_message(message)

        assert result is True
        notification_service.send_template_to_user.assert_called_once_with(
            user_uuid="user_456",
            template_id="test_template",
            context={"name": "Test User"},
            priority=1
        )

    def test_process_message_trading_signal(self):
        """测试处理交易信号消息"""
        notification_service = Mock()
        record_crud = Mock()
        worker = NotificationWorker(
            notification_service=notification_service,
            record_crud=record_crud
        )

        message = {
            "message_type": "trading_signal",
            "message_id": "msg_signal",
            "user_uuid": "user_signal",
            "direction": "LONG",
            "code": "AAPL",
            "price": 150.0,
            "volume": 100
        }

        # Mock notification_service.send_trading_signal
        notification_service.send_trading_signal.return_value = Mock(success=True)

        result = worker._process_message(message)

        assert result is True
        notification_service.send_trading_signal.assert_called_once()

    def test_process_message_system_notification(self):
        """测试处理系统通知消息"""
        notification_service = Mock()
        record_crud = Mock()
        worker = NotificationWorker(
            notification_service=notification_service,
            record_crud=record_crud
        )

        message = {
            "message_type": "system_notification",
            "message_id": "msg_sys",
            "user_uuid": "user_sys",
            "content": "System alert",
            "level": "ERROR"
        }

        # Mock notification_service.send_system_notification
        notification_service.send_system_notification.return_value = Mock(success=True)

        result = worker._process_message(message)

        assert result is True
        notification_service.send_system_notification.assert_called_once()

    def test_process_message_invalid(self):
        """测试处理无效消息"""
        notification_service = Mock()
        record_crud = Mock()
        worker = NotificationWorker(
            notification_service=notification_service,
            record_crud=record_crud
        )

        message = {
            "message_id": "msg_invalid",
            # 缺少 message_type
        }

        result = worker._process_message(message)

        assert result is False


@pytest.mark.unit
class TestNotificationWorkerGroupMessaging:
    """NotificationWorker 组消息测试"""

    def test_process_simple_message_to_group(self):
        """测试发送 simple 消息到用户组"""
        notification_service = Mock()
        record_crud = Mock()
        worker = NotificationWorker(
            notification_service=notification_service,
            record_crud=record_crud
        )

        message = {
            "message_type": "simple",
            "message_id": "msg_group",
            "group_name": "test_group",
            "content": "Group test message"
        }

        # Mock notification_service.send_to_group
        notification_service.send_to_group.return_value = Mock(success=True)

        result = worker._process_message(message)

        assert result is True
        notification_service.send_to_group.assert_called_once_with(
            group_name="test_group",
            content="Group test message",
            title=None,
            channels=None,
            priority=1
        )


@pytest.mark.unit
class TestNotificationWorkerHealthStatus:
    """NotificationWorker 健康状态测试"""

    def test_get_health_status_stopped(self):
        """测试获取健康状态（已停止）"""
        notification_service = Mock()
        record_crud = Mock()
        worker = NotificationWorker(
            notification_service=notification_service,
            record_crud=record_crud
        )

        status = worker.get_health_status()

        assert status["status"] == "STOPPED"
        assert status["is_running"] is False
        assert status["messages_consumed"] == 0

    @patch('ginkgo.notifier.workers.notification_worker.GinkgoConsumer')
    def test_get_health_status_running(self, mock_consumer_class):
        """测试获取健康状态（运行中）"""
        notification_service = Mock()
        record_crud = Mock()

        # Mock consumer
        mock_consumer = Mock()
        mock_consumer.is_connected = True
        mock_consumer.consumer.poll.return_value = {}
        mock_consumer_class.return_value = mock_consumer

        worker = NotificationWorker(
            notification_service=notification_service,
            record_crud=record_crud
        )
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
        notification_service = Mock()
        record_crud = Mock()

        worker = create_notification_worker(
            notification_service=notification_service,
            record_crud=record_crud
        )

        assert isinstance(worker, NotificationWorker)
        assert worker.notification_service == notification_service
        assert worker.record_crud == record_crud

    def test_create_notification_worker_with_group_id(self):
        """测试创建 Worker 便捷函数（带 group_id）"""
        notification_service = Mock()
        record_crud = Mock()

        worker = create_notification_worker(
            notification_service=notification_service,
            record_crud=record_crud,
            group_id="custom_group"
        )

        assert isinstance(worker, NotificationWorker)
        assert worker._group_id == "custom_group"
