"""
Scheduler CLI 单元测试

测试 ginkgo.client.scheduler_cli 的查询类命令（status / plan / nodes / schedule / recalculate）。

覆盖 issue：
- #5174: status 只发 Kafka 不回显 → 改为读 RedisService.get_scheduler_status() 同步显示
- #5987: schedule:plan 是 HASH，误用 get() 触发 WRONGTYPE
- #6300/#6115: plan/nodes/recalculate/schedule 消除 RedisCRUD 直连，统一走 redis_service
  （get_schedule_plan / get_execution_nodes_detail）；start/serve 的 raw client 保留为 DI 例外

Mock 策略：
  - 查询类命令经 services.data.redis_service() → patch "ginkgo.services"
  - 隔离真实 Kafka IO → patch "ginkgo.data.drivers.ginkgo_kafka.GinkgoProducer"
  - service 返回 ServiceResult（真实数据流，数据已 decode 为 str）
"""

import os

os.environ["GINKGO_SKIP_DEBUG_CHECK"] = "1"

import re
import pytest
from typer.testing import CliRunner
from unittest.mock import patch, MagicMock

from ginkgo.client import scheduler_cli
from ginkgo.data.services.base_service import ServiceResult

# Rich Console 在 CliRunner 捕获的输出里嵌入 ANSI 转义码（[bold]N[/bold] → \x1b[1;36mN\x1b[0m），
# 会打断跨样式边界的子串匹配；断言前统一剥离。
_ANSI = re.compile(r"\x1b\[[0-9;]*m")


def _clean(s: str) -> str:
    """剥离 rich ANSI 颜色码，返回纯文本供稳定子串断言。"""
    return _ANSI.sub("", s)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def cli_runner():
    return CliRunner()


@pytest.fixture
def mock_services():
    """Mock ginkgo.services，预设 redis_service 各查询方法默认空返回。"""
    m = MagicMock()
    svc = m.data.redis_service.return_value
    svc.get_scheduler_status.return_value = ServiceResult.success(data=[], message="0")
    svc.get_schedule_plan.return_value = ServiceResult.success(data={}, message="0")
    svc.get_execution_nodes_detail.return_value = ServiceResult.success(data=[], message="0")
    return m


def _node_detail(node_id="node-1", ttl=30, portfolio_count=1, queue_size=0, cpu_usage=5.0):
    """构造单个 ExecutionNode 详情 dict（get_execution_nodes_detail 的元素形态）。"""
    return {
        "node_id": node_id,
        "ttl": ttl,
        "portfolio_count": portfolio_count,
        "queue_size": queue_size,
        "cpu_usage": cpu_usage,
    }


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
        assert "sent successfully" not in result.output.lower()
        mock_producer.return_value.send.assert_not_called()
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
# plan / nodes / schedule / recalculate 收口（#6300 + #6115 + #5987-b）
# ===========================================================================

@pytest.mark.unit
@pytest.mark.cli
class TestSchedulePlanRead:
    """#5987-b + #6300/#6115: 收口后 schedule/recalculate 经 redis_service.get_schedule_plan()
    读 schedule:plan hash（内部 hgetall），CLI 层不再直连 RedisCRUD。
    """

    def test_recalculate_reads_plan_via_service(self, cli_runner, mock_services):
        """recalculate 调 redis_service.get_schedule_plan，不再碰 RedisCRUD（#6300）。"""
        svc = mock_services.data.redis_service.return_value
        svc.get_execution_nodes_detail.return_value = ServiceResult.success(
            data=[_node_detail(ttl=30)], message="1",
        )
        svc.get_schedule_plan.return_value = ServiceResult.success(
            data={"port-uuid-1": "node1"}, message="1",
        )
        with patch("ginkgo.services", mock_services), \
             patch("ginkgo.data.drivers.ginkgo_kafka.GinkgoProducer"):
            result = cli_runner.invoke(scheduler_cli.app, ["recalculate", "--dry-run"])

        # dry_run 正常退出（收口后 except typer.Exit: raise 守卫，exit=0 不再被吞）
        assert result.exit_code == 0
        svc.get_schedule_plan.assert_called_once()
        svc.get_execution_nodes_detail.assert_called_once()

    def test_schedule_reads_plan_via_service(self, cli_runner, mock_services):
        """schedule 调 redis_service.get_schedule_plan（#6300）。"""
        svc = mock_services.data.redis_service.return_value
        svc.get_execution_nodes_detail.return_value = ServiceResult.success(
            data=[_node_detail(ttl=30)], message="1",
        )
        svc.get_schedule_plan.return_value = ServiceResult.success(
            data={"port-uuid-1": "node1"}, message="1",
        )
        mock_services.data.portfolio_service.return_value.get.return_value = ServiceResult.success(
            data=[], message="0",
        )
        with patch("ginkgo.services", mock_services), \
             patch("ginkgo.data.drivers.ginkgo_kafka.GinkgoProducer"):
            result = cli_runner.invoke(scheduler_cli.app, ["schedule", "--force"])

        # 无 unassigned → 正常退出 0
        assert result.exit_code == 0
        svc.get_schedule_plan.assert_called_once()

    def test_recalculate_no_healthy_nodes_exits_loud(self, cli_runner, mock_services):
        """无健康节点时 exit 1（收口后 raise typer.Exit 不被 except 吞）。"""
        svc = mock_services.data.redis_service.return_value
        svc.get_execution_nodes_detail.return_value = ServiceResult.success(
            data=[_node_detail(ttl=-1)], message="0",  # ttl<=0 不健康
        )
        with patch("ginkgo.services", mock_services):
            result = cli_runner.invoke(scheduler_cli.app, ["recalculate", "--force"])

        assert result.exit_code == 1
        assert "No healthy nodes" in result.output


# ===========================================================================
# migrate 命令（#5056）
# ===========================================================================


@pytest.mark.unit
@pytest.mark.cli
class TestSchedulerMigrateTarget:
    """#5056: 自动选节点未实现时，--target 应作为 CLI 必填项暴露。"""

    def test_migrate_without_target_fails_at_cli_validation(self, cli_runner):
        result = cli_runner.invoke(scheduler_cli.app, ["migrate", "portfolio-001", "--force"])

        # typer 缺必填 --target → 参数解析错误 exit 2（非运行时 exit 1）
        assert result.exit_code == 2
        out = _clean(result.output)
        assert "Auto-selection not implemented" not in out
        assert "Error migrating portfolio" not in out


# ===========================================================================
# 输出转义（#6001）
# ===========================================================================

@pytest.mark.unit
@pytest.mark.cli
class TestSchedulerOutputEscape:
    """#6001: scheduler 系列命令输出不应含字面 ``\\n``（反斜杠+n 两字符）。
    收口后（#6300）nodes/plan 经 redis_service，仍保留此输出不变量。
    """

    def test_nodes_no_literal_backslash_n(self, cli_runner, mock_services):
        """#6001 tracer: nodes 输出 'Total healthy nodes' 行不含字面 \\n。"""
        mock_services.data.redis_service.return_value.get_execution_nodes_detail.return_value = ServiceResult.success(
            data=[_node_detail(node_id="node-1", ttl=30, portfolio_count=1, queue_size=0, cpu_usage=5.0)],
            message="1",
        )
        with patch("ginkgo.services", mock_services):
            result = cli_runner.invoke(scheduler_cli.app, ["nodes"])

        assert result.exit_code == 0
        assert "Total healthy nodes" in result.output
        assert "\\n" not in result.output, (
            f"nodes 输出含字面 \\n（应为真换行）: {repr(result.output[-120:])}"
        )

    def test_plan_no_literal_backslash_n(self, cli_runner, mock_services):
        """#6001: plan 输出 'Total portfolios scheduled' 行不含字面 \\n。"""
        mock_services.data.redis_service.return_value.get_schedule_plan.return_value = ServiceResult.success(
            data={"port-uuid-1": "node-1"}, message="1",
        )
        with patch("ginkgo.services", mock_services):
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
# plan 分页与过滤（#4992）—— 收口后经 redis_service.get_schedule_plan
# ===========================================================================

@pytest.mark.unit
@pytest.mark.cli
class TestSchedulerPlanFilter:
    """#4992: scheduler plan 经 redis_service.get_schedule_plan 全量读取后，
    支持 --node 过滤 + --page/--page-size 分页（默认 page_size=50 防 OOM 刷屏）。
    """

    @staticmethod
    def _multi_node_plan(n_node1: int = 60, n_node2: int = 30):
        """构造 str dict：n_node1 条映射 node-1 + n_node2 条映射 node-2（service 已 decode 形态）。"""
        plan = {}
        for i in range(n_node1):
            plan["port-%03d" % i] = "node-1"
        for i in range(n_node1, n_node1 + n_node2):
            plan["port-%03d" % i] = "node-2"
        return plan

    def _invoke_with_plan(self, cli_runner, mock_services, plan, *args):
        mock_services.data.redis_service.return_value.get_schedule_plan.return_value = ServiceResult.success(
            data=plan, message=str(len(plan)),
        )
        with patch("ginkgo.services", mock_services):
            return cli_runner.invoke(scheduler_cli.app, ["plan", *args])

    def test_node_filter_returns_only_matching_node(self, cli_runner, mock_services):
        """#4992 tracer: `--node node-2` 只输出映射到 node-2 的 portfolio。"""
        result = self._invoke_with_plan(
            cli_runner, mock_services, self._multi_node_plan(), "--node", "node-2"
        )
        out = _clean(result.output)

        assert result.exit_code == 0
        assert "node-2" in out
        assert "node-1" not in out
        assert "scheduled: 30" in out

    def test_default_page_size_truncates_to_50(self, cli_runner, mock_services):
        """#4992: 默认 page_size=50，90 条映射只显示前 50（防 OOM 刷屏）。"""
        result = self._invoke_with_plan(
            cli_runner, mock_services, self._multi_node_plan()  # 60 + 30 = 90
        )
        out = _clean(result.output)

        assert result.exit_code == 0
        assert "scheduled: 90" in out
        assert "Page 1/2" in out
        assert "showing 1-50" in out

    def test_page_2_shows_remaining(self, cli_runner, mock_services):
        """#4992: --page 2 显示第 51-90 条（90 条分 2 页：50+40）。"""
        result = self._invoke_with_plan(
            cli_runner, mock_services, self._multi_node_plan(), "--page", "2"
        )
        out = _clean(result.output)

        assert result.exit_code == 0
        assert "Page 2/2" in out
        assert "showing 51-90" in out

    def test_page_size_0_shows_all(self, cli_runner, mock_services):
        """#4992: --page-size 0 关闭分页，全量展示（向后兼容逃生口）。"""
        result = self._invoke_with_plan(
            cli_runner, mock_services, self._multi_node_plan(), "--page-size", "0"
        )
        out = _clean(result.output)

        assert result.exit_code == 0
        assert "Page" not in out
        assert "scheduled: 90" in out

    def test_node_filter_no_match_shows_friendly_message(self, cli_runner, mock_services):
        """#4992: --node 不匹配任何节点时友好提示，不输出空表。"""
        result = self._invoke_with_plan(
            cli_runner, mock_services, self._multi_node_plan(), "--node", "nonexistent-node"
        )

        assert result.exit_code == 0
        assert "No portfolios mapped to node nonexistent-node" in _clean(result.output)

    def test_invalid_page_rejected(self, cli_runner, mock_services):
        """#4992: --page 0 报错退出 1（page 必须 >= 1）。"""
        result = self._invoke_with_plan(
            cli_runner, mock_services, self._multi_node_plan(), "--page", "0"
        )

        assert result.exit_code == 1
        assert "--page must be >= 1" in _clean(result.output)

    def test_invalid_page_size_rejected(self, cli_runner, mock_services):
        """#4992: --page-size -1 报错退出 1（page_size 必须 >= 0）。"""
        result = self._invoke_with_plan(
            cli_runner, mock_services, self._multi_node_plan(), "--page-size", "-1"
        )

        assert result.exit_code == 1
        assert "--page-size must be >= 0" in _clean(result.output)
