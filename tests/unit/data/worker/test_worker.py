# Unit tests for Data Worker
# Tests: src/ginkgo/data/worker/worker.py

import pytest
import threading
import time
from unittest.mock import Mock, MagicMock, patch, call
from typing import Dict, Any
import json

import sys
import os
# Add src to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../../..'))

from ginkgo.data.worker.worker import DataWorker
from ginkgo.enums import WORKER_STATUS_TYPES


@pytest.fixture
def mock_logger():
    """Mock GinkgoLogger for tests"""
    with patch('ginkgo.data.worker.worker.GinkgoLogger') as mock:
        mock_logger_instance = MagicMock()
        mock.return_value.get_logger.return_value = mock_logger_instance
        yield mock_logger_instance


@pytest.fixture
def mock_bar_crud():
    """Mock BarCRUD for tests"""
    return Mock()


@pytest.fixture
def worker(mock_bar_crud, mock_logger):
    """Create a DataWorker instance for testing"""
    return DataWorker(bar_crud=mock_bar_crud)


@pytest.mark.tdd
class TestDataWorkerConstruction:
    """测试DataWorker构造和初始化"""

    def test_init_with_default_params(self, worker):
        """TDD Red阶段：测试默认参数初始化"""
        assert worker._bar_crud is not None
        assert worker._group_id == "data_worker_group"
        assert worker._auto_offset_reset == "earliest"
        assert worker._status == WORKER_STATUS_TYPES.STOPPED
        assert worker._consumer is None
        assert worker._heartbeat_thread is None
        assert worker._stats["messages_processed"] == 0
        assert worker._stats["bars_written"] == 0
        assert worker._stats["errors"] == 0

    def test_init_with_custom_params(self, mock_logger):
        """TDD Red阶段：测试自定义参数初始化"""
        mock_bar_crud = Mock()
        worker = DataWorker(
            bar_crud=mock_bar_crud,
            group_id="custom_group",
            auto_offset_reset="latest",
            node_id="test_node_1"
        )

        assert worker._group_id == "custom_group"
        assert worker._auto_offset_reset == "latest"
        assert worker._node_id == "test_node_1"

    def test_init_generates_node_id_if_not_provided(self, worker):
        """TDD Red阶段：测试未提供node_id时自动生成"""
        assert worker._node_id.startswith("data_worker_")
        assert len(worker._node_id) > len("data_worker_")


@pytest.mark.tdd
class TestDataWorkerProperties:
    """测试DataWorker属性访问"""

    def test_is_running_property_when_stopped(self, worker):
        """TDD Red阶段：测试is_running属性在停止状态"""
        assert worker.is_running is False

    def test_is_running_property_when_running(self, worker):
        """TDD Red阶段：测试is_running属性在运行状态"""
        worker._status = WORKER_STATUS_TYPES.RUNNING
        assert worker.is_running is True

    def test_is_healthy_property(self, worker):
        """TDD Red阶段：测试is_healthy属性"""
        # When stopped, not healthy
        worker._status = WORKER_STATUS_TYPES.STOPPED
        worker._stop_event.clear()
        assert worker.is_healthy is False

        # When running and stop event not set, healthy
        worker._status = WORKER_STATUS_TYPES.RUNNING
        assert worker.is_healthy is True


@pytest.mark.tdd
class TestDataWorkerLifecycle:
    """测试DataWorker生命周期管理"""

    @patch('ginkgo.data.drivers.ginkgo_kafka.GinkgoConsumer')
    def test_start_success(self, mock_consumer_class, worker):
        """TDD Red阶段：测试成功启动Worker"""
        mock_consumer = MagicMock()
        mock_consumer_class.return_value = mock_consumer

        # Mock the thread start to avoid actually running
        with patch.object(threading.Thread, 'start'):
            result = worker.start()

        assert result is True
        assert worker._status == WORKER_STATUS_TYPES.RUNNING
        assert worker._consumer is not None

    def test_start_when_already_started(self, worker):
        """TDD Red阶段：测试重复启动失败"""
        worker._status = WORKER_STATUS_TYPES.RUNNING

        result = worker.start()

        assert result is False

    @patch('ginkgo.data.worker.worker.threading.Thread.join')
    def test_stop_success(self, mock_join, worker):
        """TDD Red阶段：测试成功停止Worker"""
        worker._status = WORKER_STATUS_TYPES.RUNNING
        mock_consumer = MagicMock()
        worker._consumer = mock_consumer

        result = worker.stop(timeout=1.0)

        assert result is True
        assert worker._status == WORKER_STATUS_TYPES.STOPPED
        mock_consumer.close.assert_called_once()

    def test_stop_when_not_running(self, worker):
        """TDD Red阶段：测试停止未运行的Worker"""
        worker._status = WORKER_STATUS_TYPES.STOPPED

        result = worker.stop()

        assert result is False


@pytest.mark.tdd
class TestDataWorkerStats:
    """测试DataWorker统计信息"""

    def test_get_stats_returns_copy(self, worker):
        """TDD Red阶段：测试get_stats返回副本而非引用"""
        stats1 = worker.get_stats()
        stats2 = worker.get_stats()

        assert stats1 is not stats2
        assert stats1 == stats2

    def test_stats_are_updated(self, worker):
        """TDD Red阶段：测试统计信息更新"""
        with worker._lock:
            worker._stats["messages_processed"] = 100
            worker._stats["bars_written"] = 5000

        stats = worker.get_stats()

        assert stats["messages_processed"] == 100
        assert stats["bars_written"] == 5000


@pytest.mark.tdd
class TestDataWorkerKafkaIntegration:
    """测试DataWorker Kafka集成"""

    @patch('ginkgo.data.drivers.ginkgo_kafka.GinkgoConsumer')
    def test_init_consumer_creates_consumer(self, mock_consumer_class, worker):
        """TDD Red阶段：测试Kafka消费者初始化"""
        mock_consumer = MagicMock()
        mock_consumer_class.return_value = mock_consumer

        worker._init_consumer()

        assert worker._consumer is not None
        mock_consumer.subscribe.assert_called_once_with(["ginkgo.live.control.commands"])

    @patch('os.environ.get')
    def test_get_kafka_bootstrap_servers_from_env(self, mock_environ_get, worker):
        """TDD Red阶段：测试从环境变量读取Kafka配置"""
        mock_environ_get.side_effect = lambda k, d: {
            "GINKGO_KAFKA_HOST": "kafka-test",
            "GINKGO_KAFKA_PORT": "9093"
        }.get(k, d)

        result = worker._get_kafka_bootstrap_servers()

        assert result == "kafka-test:9093"

    @patch('os.environ.get')
    def test_get_kafka_bootstrap_servers_defaults(self, mock_environ_get, worker):
        """TDD Red阶段：测试Kafka配置默认值"""
        mock_environ_get.side_effect = lambda k, d: d  # Return default

        result = worker._get_kafka_bootstrap_servers()

        assert result == "localhost:9092"


@pytest.mark.tdd
class TestDataWorkerCommandProcessing:
    """测试DataWorker命令处理"""

    def test_process_kafka_message_valid_json(self, worker):
        """TDD Red阶段：测试解析有效JSON消息"""
        # Mock _process_command to avoid actual processing
        worker._process_command = Mock(return_value=True)

        message = b'{"command": "heartbeat_test", "source": "test", "timestamp": "2025-01-23T10:00:00Z", "params": {}}'

        worker._process_kafka_message(message)

        worker._process_command.assert_called_once_with(
            command="heartbeat_test",
            payload={}
        )

    def test_process_kafka_message_invalid_json(self, worker):
        """TDD Red阶段：测试解析无效JSON消息"""
        invalid_message = b'{"invalid json'

        worker._process_kafka_message(invalid_message)

        assert worker._stats["errors"] == 1

    def test_process_command_routes_bar_snapshot(self, worker):
        """TDD Red阶段：测试bar_snapshot命令路由"""
        worker._handle_bar_snapshot = Mock(return_value=True)

        result = worker._process_command("bar_snapshot", {"code": "000001.SZ"})

        assert result is True
        worker._handle_bar_snapshot.assert_called_once_with({"code": "000001.SZ"})

    def test_process_command_unknown_command(self, worker):
        """TDD Red阶段：测试未知命令处理"""
        result = worker._process_command("unknown_command", {})

        assert result is False


@pytest.mark.tdd
class TestDataWorkerCommandHandlers:
    """测试DataWorker命令处理器"""

    @patch('ginkgo.service_hub')
    def test_handle_bar_snapshot_incremental_sync(self, mock_service_hub, worker):
        """TDD Red阶段：测试增量同步处理"""
        mock_bar_service = MagicMock()
        mock_result = MagicMock()
        mock_result.success = True
        mock_result.data.records_processed = 100
        mock_bar_service.sync_smart.return_value = mock_result
        mock_service_hub.data.services.bar.return_value = mock_bar_service

        payload = {"code": "000001.SZ", "force": False, "full": False}

        result = worker._handle_bar_snapshot(payload)

        assert result is True
        mock_bar_service.sync_smart.assert_called_once_with(code="000001.SZ", fast_mode=True)

    @patch('ginkgo.service_hub')
    def test_handle_bar_snapshot_full_sync(self, mock_service_hub, worker):
        """TDD Red阶段：测试全量同步处理"""
        mock_bar_service = MagicMock()
        mock_result = MagicMock()
        mock_result.success = True
        mock_bar_service.sync_range.return_value = mock_result
        mock_service_hub.data.services.bar.return_value = mock_bar_service

        payload = {"code": "000001.SZ", "force": True, "full": True}

        result = worker._handle_bar_snapshot(payload)

        assert result is True
        mock_bar_service.sync_range.assert_called_once()

    @patch('ginkgo.service_hub')
    def test_handle_bar_snapshot_sync_failure(self, mock_service_hub, worker):
        """TDD Red阶段：测试同步失败处理"""
        mock_bar_service = MagicMock()
        mock_result = MagicMock()
        mock_result.success = False
        mock_result.error = "API Error"
        mock_bar_service.sync_smart.return_value = mock_result
        mock_service_hub.data.services.bar.return_value = mock_bar_service

        payload = {"code": "000001.SZ", "force": False, "full": False}

        result = worker._handle_bar_snapshot(payload)

        assert result is False

    def test_handle_update_selector(self, worker):
        """TDD Red阶段：测试update_selector命令处理"""
        result = worker._handle_update_selector({})

        assert result is True

    def test_handle_update_data_delegates_to_bar_snapshot(self, worker):
        """TDD Red阶段：测试update_data委托给bar_snapshot"""
        worker._handle_bar_snapshot = Mock(return_value=True)
        payload = {"code": "000001.SZ"}

        result = worker._handle_update_data(payload)

        assert result is True
        worker._handle_bar_snapshot.assert_called_once_with(payload)

    def test_handle_heartbeat_test(self, worker):
        """TDD Red阶段：测试heartbeat_test命令处理"""
        result = worker._handle_heartbeat_test({})

        assert result is True


@pytest.mark.tdd
class TestDataWorkerHeartbeat:
    """测试DataWorker心跳机制"""

    @patch('threading.Thread')
    @patch('ginkgo.service_hub')
    def test_heartbeat_thread_created(self, mock_service_hub, mock_thread_class, worker):
        """TDD Red阶段：测试心跳线程创建"""
        mock_redis_client = MagicMock()
        mock_service_hub.data.redis.return_value = mock_redis_client

        mock_thread = MagicMock()
        mock_thread_class.return_value = mock_thread

        worker._start_heartbeat_thread()

        assert worker._heartbeat_thread is not None
        mock_thread.start.assert_called_once()


@pytest.mark.tdd
class TestDataWorkerThreadSafety:
    """测试DataWorker线程安全"""

    def test_stats_access_is_thread_safe(self, worker):
        """TDD Red阶段：测试统计信息访问的线程安全性"""
        # Multiple threads accessing stats
        def update_stats():
            for _ in range(100):
                with worker._lock:
                    worker._stats["messages_processed"] += 1

        threads = [threading.Thread(target=update_stats) for _ in range(5)]

        for t in threads:
            t.start()
        for t in threads:
            t.join()

        stats = worker.get_stats()
        assert stats["messages_processed"] == 500


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
