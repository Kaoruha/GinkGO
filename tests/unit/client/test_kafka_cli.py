"""
性能: 221MB RSS, 1.99s, 16 tests [PASS]
Unit tests for kafka_cli.py commands: status, reset, purge, monitor, health,
consumer-groups, reset-offsets.

Mock strategy:
  - Patch "ginkgo.data.containers.container" for KafkaService access.
  - Patch "ginkgo.libs.core.threading.GinkgoThreadManager" for worker ops.
  - Use ServiceResult.success() / ServiceResult.error() for return values.
"""

import pytest
from unittest.mock import MagicMock, patch

from ginkgo.client import kafka_cli
from ginkgo.data.services.base_service import ServiceResult


# ============================================================================
# 1. Help tests (2)
# ============================================================================


@pytest.mark.unit
@pytest.mark.cli
class TestKafkaCLIHelp:
    """Verify help output for kafka commands."""

    def test_root_help_shows_all_commands(self, cli_runner):
        result = cli_runner.invoke(kafka_cli.app, ["--help"])
        assert result.exit_code == 0
        for name in ("status", "reset", "purge", "monitor", "health", "consumer-groups", "reset-offsets"):
            assert name in result.output

    def test_no_args_shows_help(self, cli_runner):
        result = cli_runner.invoke(kafka_cli.app, [])
        assert result.exit_code != 0
        # no_args_is_help=True should show help and exit with code != 0
        assert "KAFKA" in result.output.upper() or "kafka" in result.output.lower()


# ============================================================================
# 2. Main commands happy path (6)
# ============================================================================


@pytest.mark.unit
@pytest.mark.cli
class TestStatus:
    """Tests for the 'status' command."""

    def test_status_connected(self, cli_runner):
        mock_service = MagicMock()
        mock_service.get_statistics.return_value = ServiceResult.success(data={
            "kafka_connection": {"connected": True, "producer_active": True, "active_consumers": 2},
            "send_statistics": {"total_sent": 100, "failed_sends": 0},
            "receive_statistics": {"total_received": 50},
            "active_subscriptions": 1,
            "running_consumers": 1,
            "subscription_details": [],
        })
        mock_service.health_check.return_value = ServiceResult.success(data={"status": "healthy"})

        with patch("ginkgo.data.containers.container") as mock_container:
            mock_container.kafka_service.return_value = mock_service
            result = cli_runner.invoke(kafka_cli.app, ["status"])

        assert result.exit_code == 0
        assert "Connected" in result.output or "connected" in result.output.lower()

    def test_status_disconnected(self, cli_runner):
        mock_service = MagicMock()
        mock_service.get_statistics.return_value = ServiceResult.success(data={
            "kafka_connection": {"connected": False, "producer_active": False, "active_consumers": 0},
            "send_statistics": {"total_sent": 0, "failed_sends": 0},
            "receive_statistics": {"total_received": 0},
            "active_subscriptions": 0,
            "running_consumers": 0,
            "subscription_details": [],
        })
        mock_service.health_check.return_value = ServiceResult.success(data={"status": "unhealthy"})

        with patch("ginkgo.data.containers.container") as mock_container:
            mock_container.kafka_service.return_value = mock_service
            result = cli_runner.invoke(kafka_cli.app, ["status"])

        assert result.exit_code == 0


@pytest.mark.unit
@pytest.mark.cli
class TestReset:
    """Tests for the 'reset' command."""

    def test_reset_force(self, cli_runner):
        mock_gtm = MagicMock()
        mock_gtm.get_worker_count.return_value = 0

        with patch("ginkgo.data.containers.container"), \
             patch("ginkgo.libs.core.threading.GinkgoThreadManager", return_value=mock_gtm), \
             patch("ginkgo.data.drivers.ginkgo_kafka.kafka_topic_set"), \
             patch("ginkgo.libs.GLOG"):
            result = cli_runner.invoke(kafka_cli.app, ["reset", "--force"])

        assert result.exit_code == 0
        assert "reset" in result.output.lower() or "Resetting" in result.output

    def test_reset_specific_queue(self, cli_runner):
        mock_gtm = MagicMock()
        mock_gtm.get_worker_count.return_value = 0

        with patch("ginkgo.data.containers.container"), \
             patch("ginkgo.libs.core.threading.GinkgoThreadManager", return_value=mock_gtm), \
             patch("ginkgo.data.drivers.ginkgo_kafka.kafka_topic_set"), \
             patch("ginkgo.libs.GLOG"):
            result = cli_runner.invoke(kafka_cli.app, ["reset", "--queue-name", "ginkgo_data_update", "--force"])

        assert result.exit_code == 0


@pytest.mark.unit
@pytest.mark.cli
class TestPurge:
    """Tests for the 'purge' command."""

    def test_purge_with_confirm(self, cli_runner):
        mock_service = MagicMock()
        mock_service.topic_exists.return_value = True
        mock_service.get_message_count.return_value = 10
        mock_crud = MagicMock()
        mock_crud.consume_messages.return_value = []  # 避免无限循环
        mock_service._crud_repo = mock_crud

        with patch("ginkgo.data.containers.container") as mock_container:
            mock_container.kafka_service.return_value = mock_service
            result = cli_runner.invoke(kafka_cli.app, ["purge", "test_topic", "--yes"])

        assert result.exit_code == 0


@pytest.mark.unit
@pytest.mark.cli
class TestHealth:
    """Tests for the 'health' command."""

    def test_health_check_healthy(self, cli_runner):
        mock_kafka = MagicMock()
        mock_kafka.health_check.return_value = {"status": "healthy", "kafka_connection": True}
        mock_kafka.get_topic_status.return_value = {"exists": True}
        mock_redis = MagicMock()
        mock_redis.get_redis_info.return_value = {"connected": True, "version": "7.0"}
        mock_gtm = MagicMock()
        mock_gtm.get_worker_count.return_value = 0
        mock_gtm.get_workers_status.return_value = {}

        with patch("ginkgo.data.containers.container") as mock_container:
            mock_container.kafka_service.return_value = mock_kafka
            mock_container.redis_service.return_value = mock_redis
            with patch("ginkgo.libs.core.threading.GinkgoThreadManager", return_value=mock_gtm), \
                 patch("ginkgo.libs.GLOG"):
                result = cli_runner.invoke(kafka_cli.app, ["health"])

        assert result.exit_code == 0
        assert "HEALTHY" in result.output.upper() or "healthy" in result.output.lower()

    def test_health_tip_references_real_worker_commands(self, cli_runner):
        """kafka health 提示必须指向真实存在的 worker 子命令（防回归 #4891）。

        旧提示 'ginkgo worker status' 无效——worker 顶层无 status 子命令，
        status 是 data/backtest 各自的子命令（worker_cli.py:65 / :266）。
        """
        mock_kafka = MagicMock()
        mock_kafka.health_check.return_value = {"status": "healthy", "kafka_connection": True}
        mock_kafka.get_topic_status.return_value = {"exists": True}
        mock_redis = MagicMock()
        mock_redis.get_redis_info.return_value = {"connected": True, "version": "7.0"}
        mock_gtm = MagicMock()
        mock_gtm.get_worker_count.return_value = 0
        mock_gtm.get_workers_status.return_value = {}

        with patch("ginkgo.data.containers.container") as mock_container:
            mock_container.kafka_service.return_value = mock_kafka
            mock_container.redis_service.return_value = mock_redis
            with patch("ginkgo.libs.core.threading.GinkgoThreadManager", return_value=mock_gtm), \
                 patch("ginkgo.libs.GLOG"):
                result = cli_runner.invoke(kafka_cli.app, ["health"])

        assert result.exit_code == 0, result.output
        # 回归断言：旧的无效命令必须消失
        assert "'ginkgo worker status'" not in result.output
        # 正向断言：指向两个真实存在的 worker status 子命令
        assert "ginkgo worker data status" in result.output
        assert "ginkgo worker backtest status" in result.output


@pytest.mark.unit
@pytest.mark.cli
class TestConsumerGroups:
    """Tests for the 'consumer-groups' command."""

    def test_consumer_groups_lists_broker_groups(self, cli_runner):
        """consumer-groups 命令走 service 列出 broker 端 consumer groups 并渲染表格。

        回归 #5310：原 `_list_consumer_groups` 是 pass 桩函数，命令打印标题后无输出。
        """
        mock_service = MagicMock()
        mock_service.list_consumer_groups.return_value = ServiceResult.success(data=[
            {"name": "ginkgo_data_worker", "state": "Stable", "protocol_type": "consumer", "type": "classic"},
            {"name": "ginkgo_backtest_worker", "state": "Empty", "protocol_type": "consumer", "type": "classic"},
        ])

        with patch("ginkgo.data.containers.container") as mock_container:
            mock_container.kafka_service.return_value = mock_service
            result = cli_runner.invoke(kafka_cli.app, ["consumer-groups"])

        assert result.exit_code == 0, result.output
        mock_service.list_consumer_groups.assert_called_once()
        assert "ginkgo_data_worker" in result.output
        assert "ginkgo_backtest_worker" in result.output

    def test_consumer_groups_empty(self, cli_runner):
        """service 返回空列表时打印友好提示，不渲染空表。"""
        mock_service = MagicMock()
        mock_service.list_consumer_groups.return_value = ServiceResult.success(data=[])

        with patch("ginkgo.data.containers.container") as mock_container:
            mock_container.kafka_service.return_value = mock_service
            result = cli_runner.invoke(kafka_cli.app, ["consumer-groups"])

        assert result.exit_code == 0, result.output
        assert "No active consumer groups" in result.output

    def test_consumer_groups_service_error(self, cli_runner):
        """service 返回 error 时打印错误信息、不挂死（回归 #5310 友好退出）。"""
        mock_service = MagicMock()
        mock_service.list_consumer_groups.return_value = ServiceResult.error("connection refused")

        with patch("ginkgo.data.containers.container") as mock_container:
            mock_container.kafka_service.return_value = mock_service
            result = cli_runner.invoke(kafka_cli.app, ["consumer-groups"])

        assert result.exit_code == 0, result.output
        assert "Failed to list consumer groups" in result.output
        assert "connection refused" in result.output

    def test_consumer_groups_timeout_friendly_exit(self, cli_runner):
        """service 阻塞超过硬超时时打印友好提示、不挂死（回归 #5310「挂住」核心诉求）。

        直接调用底层函数（绕过 typer），用极小 timeout 触发超时分支；
        断言函数在远小于 service sleep 的时长内返回（即未挂等 service）。
        """
        import time as _time

        service_sleep = 5.0  # 模拟 broker 不可达阻塞
        max_wait = 2.0       # 远小于 service_sleep；超过即说明挂死

        def _slow_service():
            _time.sleep(service_sleep)
            return ServiceResult.success(data=[])

        slow_service = MagicMock()
        slow_service.list_consumer_groups.side_effect = _slow_service

        start = _time.monotonic()
        with patch("ginkgo.data.containers.container") as mock_container:
            mock_container.kafka_service.return_value = slow_service
            kafka_cli._list_consumer_groups(timeout_seconds=0.2)
        elapsed = _time.monotonic() - start

        assert elapsed < max_wait, f"命令挂等 service（elapsed={elapsed:.1f}s），超时安全网失效"


@pytest.mark.unit
@pytest.mark.cli
class TestResetOffsets:
    """Tests for the 'reset-offsets' command."""

    def test_reset_offsets_stub(self, cli_runner):
        result = cli_runner.invoke(kafka_cli.app, ["reset-offsets", "test-group", "--strategy", "earliest"])
        # _reset_consumer_offsets is a stub (pass), so no error expected
        assert result.exit_code == 0


# ============================================================================
# 3. Validation / errors (4)
# ============================================================================


@pytest.mark.unit
@pytest.mark.cli
class TestKafkaCLIValidation:
    """Validation tests for kafka commands."""

    def test_purge_missing_queue_name(self, cli_runner):
        result = cli_runner.invoke(kafka_cli.app, ["purge"])
        assert result.exit_code != 0

    def test_reset_kafka_topic_failure(self, cli_runner):
        mock_gtm = MagicMock()
        mock_gtm.get_worker_count.return_value = 0

        with patch("ginkgo.data.containers.container"), \
             patch("ginkgo.libs.core.threading.GinkgoThreadManager", return_value=mock_gtm), \
             patch("ginkgo.data.drivers.ginkgo_kafka.kafka_topic_set", side_effect=Exception("Kafka connection failed")), \
             patch("ginkgo.libs.GLOG"):
            result = cli_runner.invoke(kafka_cli.app, ["reset", "--force"])

        assert result.exit_code == 0
        assert "Error" in result.output or "error" in result.output.lower() or "Kafka connection failed" in result.output

    def test_status_service_exception(self, cli_runner):
        mock_container = MagicMock()
        mock_container.kafka_service.side_effect = Exception("connection refused")

        with patch("ginkgo.data.containers.container", mock_container):
            result = cli_runner.invoke(kafka_cli.app, ["status"])

        # _check_queue_status catches exceptions and prints them, exit_code stays 0
        assert result.exit_code == 0
        assert "connection refused" in result.output

    def test_health_redis_unhealthy(self, cli_runner):
        mock_kafka = MagicMock()
        mock_kafka.health_check.return_value = {"status": "healthy", "kafka_connection": True}
        mock_kafka.get_topic_status.return_value = {"exists": True}
        mock_redis = MagicMock()
        mock_redis.get_redis_info.return_value = {"connected": False, "error": "Connection refused"}
        mock_gtm = MagicMock()
        mock_gtm.get_worker_count.return_value = 0
        mock_gtm.get_workers_status.return_value = {}

        with patch("ginkgo.data.containers.container") as mock_container:
            mock_container.kafka_service.return_value = mock_kafka
            mock_container.redis_service.return_value = mock_redis
            with patch("ginkgo.libs.core.threading.GinkgoThreadManager", return_value=mock_gtm), \
                 patch("ginkgo.libs.GLOG"):
                result = cli_runner.invoke(kafka_cli.app, ["health"])

        assert result.exit_code == 0
        assert "ATTENTION" in result.output or "Redis" in result.output


# ============================================================================
# 4. Exception handling (2)
# ============================================================================


@pytest.mark.unit
@pytest.mark.cli
class TestKafkaCLIExceptions:
    """Exception handling tests for kafka commands."""

    def test_health_check_kafka_exception(self, cli_runner):
        mock_kafka = MagicMock()
        mock_kafka.health_check.side_effect = Exception("timeout")
        mock_redis = MagicMock()
        mock_redis.get_redis_info.return_value = {"connected": True, "version": "7.0"}
        mock_gtm = MagicMock()
        mock_gtm.get_worker_count.return_value = 0
        mock_gtm.get_workers_status.return_value = {}

        with patch("ginkgo.data.containers.container") as mock_container:
            mock_container.kafka_service.return_value = mock_kafka
            mock_container.redis_service.return_value = mock_redis
            with patch("ginkgo.libs.core.threading.GinkgoThreadManager", return_value=mock_gtm), \
                 patch("ginkgo.libs.GLOG"):
                result = cli_runner.invoke(kafka_cli.app, ["health"])

        assert result.exit_code == 0
        assert "Error" in result.output or "ATTENTION" in result.output

    def test_purge_topic_not_exists(self, cli_runner):
        mock_service = MagicMock()
        mock_service.topic_exists.return_value = False

        with patch("ginkgo.data.containers.container") as mock_container:
            mock_container.kafka_service.return_value = mock_service
            result = cli_runner.invoke(kafka_cli.app, ["purge", "nonexistent_topic", "--yes"])

        assert result.exit_code == 0
        assert "does not exist" in result.output.lower()
