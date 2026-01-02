# Upstream: None
# Downstream: None
# Role: KafkaHealthChecker单元测试验证Kafka健康检查功能


"""
KafkaHealthChecker Unit Tests

测试覆盖:
- 健康检查
- 连接超时检查
- Producer 初始化检查
- Broker 可达性检查
- 降级逻辑
"""

import pytest
import time
import threading
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime

from ginkgo.libs.utils.kafka_health_checker import (
    KafkaHealthChecker,
    is_kafka_available,
    should_degrade_to_sync
)


@pytest.mark.unit
class TestKafkaHealthCheckerInit:
    """KafkaHealthChecker 初始化测试"""

    @patch('ginkgo.data.crud.KafkaCRUD')
    def test_init_default(self, mock_kafka_crud_class):
        """测试默认初始化"""
        mock_kafka_crud = Mock()
        mock_kafka_crud_class.return_value = mock_kafka_crud

        checker = KafkaHealthChecker()

        assert checker.kafka_crud == mock_kafka_crud
        assert checker._is_healthy is None
        assert checker._consecutive_failures == 0

    @patch('ginkgo.data.crud.KafkaCRUD')
    def test_init_with_crud(self, mock_kafka_crud_class):
        """测试使用自定义 CRUD 初始化"""
        mock_kafka_crud = Mock()
        checker = KafkaHealthChecker(kafka_crud=mock_kafka_crud)

        assert checker.kafka_crud == mock_kafka_crud


@pytest.mark.unit
class TestKafkaHealthCheckerCheck:
    """KafkaHealthChecker 健康检查测试"""

    @patch('ginkgo.data.crud.KafkaCRUD')
    def test_check_health_all_success(self, mock_kafka_crud_class):
        """测试所有检查都成功"""
        mock_kafka_crud = Mock()
        mock_kafka_crud._test_connection.return_value = True
        mock_kafka_crud.producer.producer.config = {"bootstrap_servers": "kafka:9092"}
        mock_kafka_crud.get_topic_info.return_value = {"topic": "notifications"}

        checker = KafkaHealthChecker(kafka_crud=mock_kafka_crud)
        result = checker.check_health()

        assert result["healthy"] is True
        assert result["checks"]["connection"]["success"] is True
        assert result["checks"]["producer"]["success"] is True
        assert result["checks"]["broker"]["success"] is True
        assert checker._is_healthy is True
        assert checker._consecutive_failures == 0

    @patch('ginkgo.data.crud.KafkaCRUD')
    def test_check_health_connection_failed(self, mock_kafka_crud_class):
        """测试连接检查失败"""
        mock_kafka_crud = Mock()
        mock_kafka_crud._test_connection.return_value = False

        checker = KafkaHealthChecker(kafka_crud=mock_kafka_crud)
        result = checker.check_health()

        assert result["healthy"] is False
        assert result["checks"]["connection"]["success"] is False
        assert checker._consecutive_failures == 1

    @patch('ginkgo.data.crud.KafkaCRUD')
    def test_check_health_timeout(self, mock_kafka_crud_class):
        """测试连接超时"""
        mock_kafka_crud = Mock()
        mock_kafka_crud._test_connection.return_value = True

        # 模拟超时：_test_connection 花费超过 10 秒
        def slow_connection():
            time.sleep(11)  # 超过 CHECK_TIMEOUT (10s)
            return True

        mock_kafka_crud._test_connection = slow_connection

        checker = KafkaHealthChecker(kafka_crud=mock_kafka_crud)
        result = checker.check_health()

        assert result["healthy"] is False
        assert "timeout" in result["checks"]["connection"]["error"].lower()


@pytest.mark.unit
class TestKafkaHealthCheckerDegradation:
    """KafkaHealthChecker 降级逻辑测试"""

    @patch('ginkgo.data.crud.KafkaCRUD')
    def test_should_degrade_healthy(self, mock_kafka_crud_class):
        """测试健康状态不应降级"""
        mock_kafka_crud = Mock()
        mock_kafka_crud._test_connection.return_value = True

        checker = KafkaHealthChecker(kafka_crud=mock_kafka_crud)
        checker.check_health()

        assert checker.should_degrade() is False

    @patch('ginkgo.data.crud.KafkaCRUD')
    def test_should_degrade_unhealthy(self, mock_kafka_crud_class):
        """测试不健康状态应降级"""
        mock_kafka_crud = Mock()
        mock_kafka_crud._test_connection.return_value = False

        checker = KafkaHealthChecker(kafka_crud=mock_kafka_crud)
        checker.check_health()

        assert checker.should_degrade() is True

    @patch('ginkgo.data.crud.KafkaCRUD')
    def test_should_degrade_after_threshold(self, mock_kafka_crud_class):
        """测试连续失败超过阈值后应降级"""
        mock_kafka_crud = Mock()
        mock_kafka_crud._test_connection.return_value = False

        checker = KafkaHealthChecker(kafka_crud=mock_kafka_crud)

        # 连续失败 3 次（RETRY_THRESHOLD）
        for _ in range(3):
            checker.check_health()

        assert checker._consecutive_failures == 3
        assert checker.should_degrade() is True

    @patch('ginkgo.data.crud.KafkaCRUD')
    def test_should_degrade_recovery(self, mock_kafka_crud_class):
        """测试恢复后不应降级"""
        mock_kafka_crud = Mock()
        mock_kafka_crud._test_connection.return_value = False

        checker = KafkaHealthChecker(kafka_crud=mock_kafka_crud)
        checker.check_health()  # 第一次失败

        # 恢复
        mock_kafka_crud._test_connection.return_value = True
        mock_kafka_crud.producer.producer.config = {"bootstrap_servers": "kafka:9092"}
        checker.check_health()  # 第二次成功

        assert checker.should_degrade() is False
        assert checker._consecutive_failures == 0


@pytest.mark.unit
class TestKafkaHealthCheckerSummary:
    """KafkaHealthChecker 状态摘要测试"""

    @patch('ginkgo.data.crud.KafkaCRUD')
    def test_get_health_summary_healthy(self, mock_kafka_crud_class):
        """测试健康状态摘要"""
        mock_kafka_crud = Mock()
        mock_kafka_crud._test_connection.return_value = True

        checker = KafkaHealthChecker(kafka_crud=mock_kafka_crud)
        checker.check_health()

        summary = checker.get_health_summary()

        assert "Healthy" in summary
        assert "consecutive failures" not in summary.lower()

    @patch('ginkgo.data.crud.KafkaCRUD')
    def test_get_health_summary_degraded(self, mock_kafka_crud_class):
        """测试降级状态摘要"""
        mock_kafka_crud = Mock()
        mock_kafka_crud._test_connection.return_value = False

        checker = KafkaHealthChecker(kafka_crud=mock_kafka_crud)

        # 连续失败 3 次
        for _ in range(3):
            checker.check_health()

        summary = checker.get_health_summary()

        assert "Degraded" in summary
        assert "3 consecutive failures" in summary

    def test_get_health_summary_unknown(self):
        """测试未知状态摘要"""
        checker = KafkaHealthChecker(kafka_crud=None)

        summary = checker.get_health_summary()

        assert "Unknown" in summary


@pytest.mark.unit
class TestConvenienceFunctions:
    """便捷函数测试"""

    @patch('ginkgo.libs.utils.kafka_health_checker.KafkaHealthChecker')
    def test_is_kafka_available_true(self, mock_checker_class):
        """测试 is_kafka_available 返回 True"""
        mock_checker = Mock()
        mock_checker.is_healthy = True
        mock_checker_class.return_value = mock_checker

        result = is_kafka_available()

        assert result is True

    @patch('ginkgo.libs.utils.kafka_health_checker.KafkaHealthChecker')
    def test_should_degrade_to_sync_true(self, mock_checker_class):
        """测试 should_degrade_to_sync 返回 True"""
        mock_checker = Mock()
        mock_checker.should_degrade.return_value = True
        mock_checker_class.return_value = mock_checker

        result = should_degrade_to_sync()

        assert result is True
