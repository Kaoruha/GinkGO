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


# ===========================================================================
# migrate 命令（#5056）
# ===========================================================================


@pytest.mark.unit
@pytest.mark.cli
class TestSchedulerMigrateTarget:
    """#5056: 自动选节点未实现时，--target 应作为 CLI 必填项暴露。"""

    def test_migrate_without_target_fails_at_cli_validation(self, cli_runner):
        result = cli_runner.invoke(scheduler_cli.app, ["migrate", "portfolio-001", "--force"])

        assert result.exit_code == 2
        assert "--target" in result.output
        assert "Auto-selection not implemented" not in result.output
        assert "Error migrating portfolio" not in result.output


# ===========================================================================
# 输出转义（#6001）
# ===========================================================================

@pytest.mark.unit
@pytest.mark.cli
class TestSchedulerOutputEscape:
    """#6001: scheduler 系列命令输出不应含字面 ``\\n``（反斜杠+n 两字符）。

    根因：scheduler_cli.py 源码字符串字面量写成 ``\\\\n``（双反斜杠），
    Python 解析为字面「反斜杠+n」，rich console.print 原样输出；
    应为 ``\\n``（单反斜杠）→ 解析为真换行 LF。验收：输出无字面 \\n。
    """

    def test_nodes_no_literal_backslash_n(self, cli_runner):
        """#6001 tracer: nodes 输出 'Total healthy nodes' 行不含字面 \\n，应为真换行。"""
        mock_redis = MagicMock()
        mock_redis.keys.return_value = [b"heartbeat:node:node-1"]
        mock_redis.ttl.return_value = 30
        mock_redis.hgetall.return_value = {
            b'portfolio_count': b'1', b'queue_size': b'0', b'cpu_usage': b'5.0',
        }
        with patch("ginkgo.data.crud.RedisCRUD") as MockCRUD:
            MockCRUD.return_value.redis = mock_redis
            result = cli_runner.invoke(scheduler_cli.app, ["nodes"])

        assert result.exit_code == 0
        assert "Total healthy nodes" in result.output
        # 字面 \n（反斜杠+n）= 源码 \\n 双反斜杠误用所致，修复后必须消失
        assert "\\n" not in result.output, (
            f"nodes 输出含字面 \\n（应为真换行）: {repr(result.output[-120:])}"
        )

    def test_plan_no_literal_backslash_n(self, cli_runner):
        """#6001: plan 输出 'Total portfolios scheduled' 行不含字面 \\n。"""
        mock_redis = MagicMock()
        mock_redis.hgetall.return_value = {b"port-uuid-1": b"node-1"}
        with patch("ginkgo.data.crud.RedisCRUD") as MockCRUD:
            MockCRUD.return_value.redis = mock_redis
            result = cli_runner.invoke(scheduler_cli.app, ["plan"])

        assert result.exit_code == 0
        assert "Total portfolios scheduled" in result.output
        assert "\\n" not in result.output, (
            f"plan 输出含字面 \\n: {repr(result.output[-120:])}"
        )

    def test_reload_no_literal_backslash_n(self, cli_runner):
        """#6001: reload --force 输出 'Reload Plan' 不含字面 \\n。"""
        with patch("ginkgo.data.drivers.ginkgo_kafka.GinkgoProducer") as MockProducer:
            MockProducer.return_value.send.return_value = True
            result = cli_runner.invoke(
                scheduler_cli.app, ["reload", "port-uuid-1", "--force"]
            )

        assert result.exit_code == 0
        assert "Reload Plan" in result.output
        assert "\\n" not in result.output, (
            f"reload 输出含字面 \\n: {repr(result.output[-120:])}"
        )


# ===========================================================================
# plan 分页与过滤（#4992）
# ===========================================================================

@pytest.mark.unit
@pytest.mark.cli
class TestSchedulerPlanFilter:
    """#4992: scheduler plan 全量 hgetall 后无过滤/分页，组合多时刷屏。

    修复后应支持 --node 过滤（仅显示映射到指定节点的 portfolio）和
    --page/--page-size 分页（默认 page_size=50 防 OOM 刷屏）。
    """

    @staticmethod
    def _multi_node_plan_redis(n_node1: int = 60, n_node2: int = 30):
        """构造 RedisCRUD().redis 的 mock：返回 n_node1 条映射到 node-1 +
        n_node2 条映射到 node-2 的 schedule:plan hash（超出默认 page_size=50）。
        """
        mock_redis = MagicMock()
        plan = {}
        for i in range(n_node1):
            plan[f"port-{i:03d}".encode()] = b"node-1"
        for i in range(n_node1, n_node1 + n_node2):
            plan[f"port-{i:03d}".encode()] = b"node-2"
        mock_redis.hgetall.return_value = plan
        return mock_redis

    def test_node_filter_returns_only_matching_node(self, cli_runner):
        """#4992 tracer: `--node node-2` 只输出映射到 node-2 的 portfolio。"""
        with patch("ginkgo.data.crud.RedisCRUD") as MockCRUD:
            MockCRUD.return_value.redis = self._multi_node_plan_redis()
            result = cli_runner.invoke(scheduler_cli.app, ["plan", "--node", "node-2"])

        assert result.exit_code == 0
        # 只剩 node-2 的 30 条（用 "scheduled: N" 文案锚定过滤后总数）
        assert "node-2" in result.output
        assert "node-1" not in result.output
        assert "scheduled: 30" in result.output

    def test_default_page_size_truncates_to_50(self, cli_runner):
        """#4992: 默认 page_size=50，90 条映射只显示前 50（防 OOM 刷屏）。"""
        with patch("ginkgo.data.crud.RedisCRUD") as MockCRUD:
            MockCRUD.return_value.redis = self._multi_node_plan_redis()  # 60 + 30 = 90
            result = cli_runner.invoke(scheduler_cli.app, ["plan"])

        assert result.exit_code == 0
        # 总数仍是 90（过滤后），但本页只展示 1-50
        assert "scheduled: 90" in result.output
        assert "Page 1/2" in result.output
        assert "showing 1-50" in result.output

    def test_page_2_shows_remaining(self, cli_runner):
        """#4992: --page 2 显示第 51-90 条（90 条分 2 页：50+40）。"""
        with patch("ginkgo.data.crud.RedisCRUD") as MockCRUD:
            MockCRUD.return_value.redis = self._multi_node_plan_redis()
            result = cli_runner.invoke(scheduler_cli.app, ["plan", "--page", "2"])

        assert result.exit_code == 0
        assert "Page 2/2" in result.output
        assert "showing 51-90" in result.output

    def test_page_size_0_shows_all(self, cli_runner):
        """#4992: --page-size 0 关闭分页，全量展示（向后兼容逃生口）。"""
        with patch("ginkgo.data.crud.RedisCRUD") as MockCRUD:
            MockCRUD.return_value.redis = self._multi_node_plan_redis()
            result = cli_runner.invoke(
                scheduler_cli.app, ["plan", "--page-size", "0"]
            )

        assert result.exit_code == 0
        # 无 "Page X/Y" 行（unlimited 模式只输出总数）
        assert "Page" not in result.output
        assert "scheduled: 90" in result.output

    def test_node_filter_no_match_shows_friendly_message(self, cli_runner):
        """#4992: --node 不匹配任何节点时友好提示，不输出空表。"""
        with patch("ginkgo.data.crud.RedisCRUD") as MockCRUD:
            MockCRUD.return_value.redis = self._multi_node_plan_redis()
            result = cli_runner.invoke(
                scheduler_cli.app, ["plan", "--node", "nonexistent-node"]
            )

        assert result.exit_code == 0
        assert "No portfolios mapped to node nonexistent-node" in result.output

    def test_invalid_page_rejected(self, cli_runner):
        """#4992: --page 0 报错退出 1（page 必须 >= 1）。"""
        with patch("ginkgo.data.crud.RedisCRUD") as MockCRUD:
            MockCRUD.return_value.redis = self._multi_node_plan_redis()
            result = cli_runner.invoke(scheduler_cli.app, ["plan", "--page", "0"])

        assert result.exit_code == 1
        assert "--page must be >= 1" in result.output

    def test_invalid_page_size_rejected(self, cli_runner):
        """#4992: --page-size -1 报错退出 1（page_size 必须 >= 0）。"""
        with patch("ginkgo.data.crud.RedisCRUD") as MockCRUD:
            MockCRUD.return_value.redis = self._multi_node_plan_redis()
            result = cli_runner.invoke(
                scheduler_cli.app, ["plan", "--page-size", "-1"]
            )

        assert result.exit_code == 1
        assert "--page-size must be >= 0" in result.output
