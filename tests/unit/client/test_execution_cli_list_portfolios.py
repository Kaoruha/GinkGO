# coding:utf-8
"""execution_cli list-portfolios 命令单元测试 (#5177)。

list-portfolios 从 schedule:plan Redis hash ({portfolio_id -> node_id})
读取并反查指定节点已加载的 portfolio 列表。数据源与调度器反查节点
portfolio 的同一来源 (scheduler.py _send_status_report)。
"""

import os

os.environ["GINKGO_SKIP_DEBUG_CHECK"] = "1"

import pytest
from unittest.mock import MagicMock, patch
from typer.testing import CliRunner

from ginkgo.client import execution_cli


@pytest.fixture
def cli_runner():
    return CliRunner()


@pytest.mark.unit
@pytest.mark.cli
class TestExecutionListPortfolios:
    """#5177 list-portfolios 读 schedule:plan hash 反查节点 portfolio。"""

    def test_list_portfolios_filters_by_node_id(self, cli_runner):
        """schedule:plan 含多节点分配时，--node-id 仅显示分配给该节点的 portfolio。"""
        mock_redis = MagicMock()
        # schedule:plan hash: {portfolio_id -> node_id} (redis-py 返回 bytes)
        mock_redis.hgetall.return_value = {
            b"portfolio_aaa": b"node_1",
            b"portfolio_bbb": b"node_2",
            b"portfolio_ccc": b"node_1",
        }
        # heartbeat 存活（TTL > 0 表示有心跳）
        mock_redis.ttl.return_value = 25
        mock_crud = MagicMock()
        mock_crud.redis = mock_redis

        with patch("ginkgo.data.crud.RedisCRUD", return_value=mock_crud):
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
        mock_redis = MagicMock()
        mock_redis.hgetall.return_value = {}
        mock_redis.ttl.return_value = 25  # 节点在线，只是无分配
        mock_crud = MagicMock()
        mock_crud.redis = mock_redis

        with patch("ginkgo.data.crud.RedisCRUD", return_value=mock_crud):
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
        mock_redis = MagicMock()
        mock_redis.hgetall.return_value = {}
        # TTL=-2 表示心跳键不存在（节点未运行）
        mock_redis.ttl.return_value = -2
        mock_crud = MagicMock()
        mock_crud.redis = mock_redis

        with patch("ginkgo.data.crud.RedisCRUD", return_value=mock_crud):
            result = cli_runner.invoke(
                execution_cli.app, ["list-portfolios", "--node-id", "ghost_node"]
            )

        assert result.exit_code == 0
        assert "No portfolios" in result.output
        # 信息性心跳提示
        assert "ghost_node" in result.output
        assert "心跳" in result.output
