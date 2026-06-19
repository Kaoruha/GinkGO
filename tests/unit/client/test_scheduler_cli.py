"""
Scheduler CLI 单元测试

测试 ginkgo.client.scheduler_cli 的查询类命令（status / schedule / recalculate）。

覆盖 issue：
- #5174: status 只发 Kafka 不回显 → 改为读 RedisService.get_scheduler_status() 同步显示
- #5987: status 发 Kafka datetime 序列化失败（随 #5174 改读 Redis 一并消解）；
         schedule/recalculate 对 hash key schedule:plan 误用 get() → WRONGTYPE

Mock 策略：
  - status 修复后用 services.data.redis_service().get_scheduler_status() -> patch "ginkgo.services"
  - 隔离真实 Kafka IO -> patch "ginkgo.data.drivers.ginkgo_kafka.GinkgoProducer"
  - get_scheduler_status 返回 ServiceResult（真实数据流）
"""

import os

os.environ["GINKGO_SKIP_DEBUG_CHECK"] = "1"

import pytest
from typer.testing import CliRunner
from unittest.mock import patch, MagicMock

from ginkgo.client import scheduler_cli
from ginkgo.data.services.base_service import ServiceResult


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def cli_runner():
    return CliRunner()


@pytest.fixture
def mock_services():
    """Mock ginkgo.services，预设 redis_service.get_scheduler_status 默认无 scheduler。"""
    m = MagicMock()
    m.data.redis_service.return_value.get_scheduler_status.return_value = ServiceResult.success(
        data=[], message="Found 0 schedulers"
    )
    return m


# ===========================================================================
# status 命令（#5174 + #5987-a）
# ===========================================================================

@pytest.mark.unit
@pytest.mark.cli
class TestSchedulerStatus:
    """status 子命令应同步读 Redis 展示，不发 Kafka。"""

    def test_no_scheduler_shows_not_running_and_no_kafka(self, cli_runner, mock_services):
        """#5174 tracer: 无 Scheduler 心跳时，显示未启动提示，且绝不发 Kafka 命令。"""
        with patch("ginkgo.services", mock_services), \
             patch("ginkgo.data.drivers.ginkgo_kafka.GinkgoProducer") as mock_producer:
            result = cli_runner.invoke(scheduler_cli.app, ["status"])

        assert result.exit_code == 0
        # 查询不该走命令通道
        assert "sent successfully" not in result.output.lower()
        mock_producer.return_value.send.assert_not_called()
        # 应同步读取 Scheduler 状态
        mock_services.data.redis_service.return_value.get_scheduler_status.assert_called_once()

    def test_with_scheduler_shows_status_table(self, cli_runner, mock_services):
        """#5174: 有 Scheduler 心跳时，显示 node_id / status / 任务数 / 心跳。"""
        mock_services.data.redis_service.return_value.get_scheduler_status.return_value = ServiceResult.success(
            data=[{
                "node_id": "sched-1",
                "status": "running",
                "running_tasks": 3,
                "pending_tasks": 1,
                "last_heartbeat": "2026-06-20T10:00:00",
            }],
            message="Found 1 schedulers",
        )
        with patch("ginkgo.services", mock_services):
            result = cli_runner.invoke(scheduler_cli.app, ["status"])

        assert result.exit_code == 0
        assert "sched-1" in result.output
        assert "running" in result.output.lower()

    def test_service_error_reports_and_exits(self, cli_runner, mock_services):
        """get_scheduler_status 失败时显示错误并 exit 1（而非吞掉）。"""
        mock_services.data.redis_service.return_value.get_scheduler_status.return_value = ServiceResult.error(
            error="Redis unavailable"
        )
        with patch("ginkgo.services", mock_services):
            result = cli_runner.invoke(scheduler_cli.app, ["status"])

        assert result.exit_code == 1
        assert "Error" in result.output


# ===========================================================================
# schedule / recalculate 命令（#5987-b）
# ===========================================================================

@pytest.mark.unit
@pytest.mark.cli
class TestSchedulePlanRead:
    """#5987-b: schedule:plan 是 Redis HASH（publisher.hset / plan_manager.hgetall / plan 命令均用 hash）。
    schedule / recalculate 读端误用 get()（string 语义）会触发 WRONGTYPE。
    修复后必须用 hgetall() 读 hash。
    """

    def _mock_hash_plan_redis(self):
        """构造 RedisCRUD().redis 的 mock：1 个 healthy node + schedule:plan hash 视图。"""
        mock_redis = MagicMock()
        mock_redis.keys.return_value = [b"heartbeat:node:node1"]
        mock_redis.ttl.return_value = 30
        # schedule:plan 的 hash 真实形态（bytes 字段）
        mock_redis.hgetall.return_value = {b"port-uuid-1": b"node1"}
        # 误用 get() 时让 plan 视为「不存在」，隔离 WRONGTYPE 根因断言
        mock_redis.get.return_value = None
        return mock_redis

    def test_recalculate_reads_plan_via_hgetall(self, cli_runner):
        """recalculate 用 hgetall 读 schedule:plan，绝不用 get。

        注：recalculate 的 except Exception 会吞掉 typer.Exit(0)（dry-run 正常退出），
        属独立缺陷，不在此断 exit_code；本测试只锁 #5987-b 根因（读 hash 用对方法）。
        """
        # RedisCRUD 在 scheduler_cli 函数体内 from ginkgo.data.crud import，patch 源头
        with patch("ginkgo.data.crud.RedisCRUD") as MockCRUD:
            MockCRUD.return_value.redis = self._mock_hash_plan_redis()
            cli_runner.invoke(scheduler_cli.app, ["recalculate", "--dry-run"])

        mock_redis = MockCRUD.return_value.redis
        mock_redis.hgetall.assert_any_call("schedule:plan")
        get_calls = [
            c for c in mock_redis.get.call_args_list
            if c.args and c.args[0] == "schedule:plan"
        ]
        assert get_calls == [], "schedule:plan 是 hash，用 get() 会触发 WRONGTYPE"

    def test_schedule_reads_plan_via_hgetall(self, cli_runner):
        """schedule 用 hgetall 读 schedule:plan，绝不用 get。

        schedule 的 except Exception 同样会吞 typer.Exit，本测试只锁 #5987-b 根因。
        portfolio_service 返回空 → unassigned=0 → 命令在读取 plan 之后正常退出。
        """
        with patch("ginkgo.data.crud.RedisCRUD") as MockCRUD, \
             patch("ginkgo.data.drivers.ginkgo_kafka.GinkgoProducer"), \
             patch("ginkgo.services") as MockSvc:
            MockCRUD.return_value.redis = self._mock_hash_plan_redis()
            MockSvc.data.portfolio_service.return_value.get.return_value = ServiceResult.success(
                data=[], message="Found 0 live portfolios"
            )
            cli_runner.invoke(scheduler_cli.app, ["schedule", "--force"])

        mock_redis = MockCRUD.return_value.redis
        mock_redis.hgetall.assert_any_call("schedule:plan")
        get_calls = [
            c for c in mock_redis.get.call_args_list
            if c.args and c.args[0] == "schedule:plan"
        ]
        assert get_calls == [], "schedule:plan 是 hash，用 get() 会触发 WRONGTYPE"
