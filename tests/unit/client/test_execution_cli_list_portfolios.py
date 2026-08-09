# coding:utf-8
"""execution_cli list-portfolios 命令单元测试 (#5177)。

list-portfolios 从 schedule:plan Redis hash ({portfolio_id -> node_id})
读取并反查指定节点已加载的 portfolio 列表。数据源与调度器反查节点
portfolio 的同一来源 (scheduler.py _send_status_report)。

#6300/#6115: 收口后经 redis_service.get_schedule_plan / get_node_heartbeat_ttl，
CLI 层不再直连 RedisCRUD（数据由 service 层 decode 为 str dict）。
"""

import os

os.environ["GINKGO_SKIP_DEBUG_CHECK"] = "1"

import pytest
from unittest.mock import MagicMock, patch
from typer.testing import CliRunner

from ginkgo.client import execution_cli
from ginkgo.data.services.base_service import ServiceResult


@pytest.fixture
def cli_runner():
    return CliRunner()


def _mock_services(plan: dict, heartbeat_ttl: int = 25):
    """构造 mock ginkgo.services：
    get_schedule_plan 返回 plan（str dict），get_node_heartbeat_ttl 返回 ttl。
    """
    m = MagicMock()
    svc = m.data.redis_service.return_value
    svc.get_schedule_plan.return_value = ServiceResult.success(
        data=plan, message=str(len(plan))
    )
    svc.get_node_heartbeat_ttl.return_value = ServiceResult.success(
        data=heartbeat_ttl, message=f"TTL={heartbeat_ttl}"
    )
    return m


@pytest.mark.unit
@pytest.mark.cli
class TestExecutionListPortfolios:
    """#5177 list-portfolios 读 schedule:plan hash 反查节点 portfolio（#6300 收口经 service）。"""

    def test_list_portfolios_filters_by_node_id(self, cli_runner):
        """schedule:plan 含多节点分配时，--node-id 仅显示分配给该节点的 portfolio。"""
        plan = {
            "portfolio_aaa": "node_1",
            "portfolio_bbb": "node_2",
            "portfolio_ccc": "node_1",
        }
        with patch("ginkgo.services", _mock_services(plan)):
            result = cli_runner.invoke(
                execution_cli.app, ["list-portfolios", "--node-id", "node_1"]
            )

        assert result.exit_code == 0
        assert "portfolio_aaa" in result.output
        assert "portfolio_ccc" in result.output
        # portfolio_bbb 分配给 node_2，不应出现
        assert "portfolio_bbb" not in result.output

    def test_list_portfolios_empty_plan_friendly_message(self, cli_runner):
        """schedule:plan 为空（无分配）时打印友好提示，exit 0（AC: 空列表提示）。"""
        with patch("ginkgo.services", _mock_services({}, heartbeat_ttl=25)):
            result = cli_runner.invoke(
                execution_cli.app, ["list-portfolios", "--node-id", "node_1"]
            )

        assert result.exit_code == 0
        # 友好提示包含节点 id 与"No portfolios"
        assert "node_1" in result.output
        assert "No portfolios" in result.output
        # 不应崩溃成 traceback
        assert "Traceback" not in result.output

    def test_list_portfolios_node_offline_shows_heartbeat_hint(self, cli_runner):
        """节点无心跳（TTL<0）且无分配时，额外提示心跳未检出（信息性，不阻断）。"""
        # TTL=-2 表示心跳键不存在（节点未运行）
        with patch("ginkgo.services", _mock_services({}, heartbeat_ttl=-2)):
            result = cli_runner.invoke(
                execution_cli.app, ["list-portfolios", "--node-id", "ghost_node"]
            )

        assert result.exit_code == 0
        assert "No portfolios" in result.output
        # 信息性心跳提示
        assert "ghost_node" in result.output
        assert "心跳" in result.output
