"""
TDD tests for execution cleanup 命令（#5980）。

#5980: execution cleanup 硬编码 node_id="execution_node_1"，但实际节点用
hostname/自定义 ID，cleanup 不带 --node-id 时永远清不存在的节点。

修复：
- 提取 _cleanup_node(redis_client, node_id) deep module（清单个节点）
- cleanup 默认 node_id=None → 扫描所有 heartbeat keys（复用 status 的
  RedisKeyPattern.EXECUTION_NODE_HEARTBEAT_ALL）逐个清理
- 指定 --node-id 时只清该节点
"""

import os

os.environ["GINKGO_SKIP_DEBUG_CHECK"] = "1"

import pytest
from unittest.mock import MagicMock, patch
from typer.testing import CliRunner

from ginkgo.client.execution_cli import _cleanup_node, app
from ginkgo.data.redis_schema import (
    RedisKeyPattern,
    RedisKeyPrefix,
)


@pytest.fixture
def cli_runner():
    return CliRunner()


# ---------------------------------------------------------------------------
# _cleanup_node deep module
# ---------------------------------------------------------------------------


@pytest.mark.unit
@pytest.mark.cli
class TestCleanupNode:
    """_cleanup_node：清单个节点的 heartbeat + metrics，返回删除标志。"""

    def test_deletes_heartbeat_and_metrics_when_exist(self):
        redis = MagicMock()
        redis.exists.return_value = 1  # heartbeat 与 metrics 两次 exists 均命中
        hb_deleted, mt_deleted = _cleanup_node(redis, "node-a")
        assert hb_deleted is True
        assert mt_deleted is True
        assert redis.delete.call_count == 2

    def test_no_data_returns_false_and_skips_delete(self):
        redis = MagicMock()
        redis.exists.return_value = 0
        hb_deleted, mt_deleted = _cleanup_node(redis, "node-x")
        assert hb_deleted is False
        assert mt_deleted is False
        redis.delete.assert_not_called()

    def test_heartbeat_only_deletes_heartbeat(self):
        redis = MagicMock()
        redis.exists.side_effect = [1, 0]  # heartbeat 存在, metrics 不存在
        hb_deleted, mt_deleted = _cleanup_node(redis, "node-hb")
        assert hb_deleted is True
        assert mt_deleted is False
        assert redis.delete.call_count == 1


# ---------------------------------------------------------------------------
# cleanup 命令端到端（#5980：默认 node_id 应扫描所有节点，非硬编码 execution_node_1）
# ---------------------------------------------------------------------------


@pytest.mark.unit
@pytest.mark.cli
class TestCleanupCommand:
    """cleanup 命令：不带 --node-id 扫描所有节点；指定 --node-id 只清该节点。"""

    def test_no_node_id_scans_all_nodes(self, cli_runner):
        """#5980: 不带 --node-id 应扫描所有 heartbeat keys 逐个清理（非硬编码 execution_node_1）"""
        redis = MagicMock()
        prefix = f"{RedisKeyPrefix.EXECUTION_NODE_HEARTBEAT}:"
        redis.keys.return_value = [
            f"{prefix}node-a".encode(),
            f"{prefix}node-b".encode(),
        ]
        redis.exists.return_value = 1  # 每节点 heartbeat+metrics 均存在

        with patch("ginkgo.data.crud.RedisCRUD") as MockCRUD:
            MockCRUD.return_value.redis = redis
            result = cli_runner.invoke(app, ["cleanup"])

        assert result.exit_code == 0
        redis.keys.assert_called_once_with(RedisKeyPattern.EXECUTION_NODE_HEARTBEAT_ALL)
        # 2 节点 × (heartbeat + metrics) = 4 次 delete
        assert redis.delete.call_count == 4
        assert "node-a" in result.output
        assert "node-b" in result.output

    def test_with_node_id_cleans_only_specified(self, cli_runner):
        """指定 --node-id 只清该节点，不扫描所有"""
        redis = MagicMock()
        redis.exists.return_value = 1

        with patch("ginkgo.data.crud.RedisCRUD") as MockCRUD:
            MockCRUD.return_value.redis = redis
            result = cli_runner.invoke(app, ["cleanup", "--node-id", "my-host"])

        assert result.exit_code == 0
        redis.keys.assert_not_called()
        assert redis.delete.call_count == 2  # heartbeat + metrics
        assert "my-host" in result.output

    def test_no_nodes_found_shows_warning(self, cli_runner):
        """无节点时提示，不崩溃"""
        redis = MagicMock()
        redis.keys.return_value = []

        with patch("ginkgo.data.crud.RedisCRUD") as MockCRUD:
            MockCRUD.return_value.redis = redis
            result = cli_runner.invoke(app, ["cleanup"])

        assert result.exit_code == 0
        assert "No ExecutionNodes" in result.output or "no heartbeat" in result.output.lower()
