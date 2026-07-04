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

from ginkgo.client.execution_cli import _cleanup_node, _is_node_active, app
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
    """_cleanup_node：清单个节点的 heartbeat + metrics。

    返回三元组 (skipped_active, hb_deleted, mt_deleted)：
    - 活跃节点（fresh heartbeat）默认拒绝（skipped_active=True），除非 force=True。
    - stale/无数据节点正常处理（skipped_active=False）。
    """

    @staticmethod
    def _make_exists(hb: int, mt: int):
        """key-aware exists side_effect：按 key 名区分 heartbeat/metrics，不依赖调用顺序。"""
        def fake(key):
            k = key.decode() if isinstance(key, bytes) else key
            return hb if "heartbeat" in k else mt
        return fake

    def test_stale_node_deletes_heartbeat_and_metrics(self):
        """stale 节点（heartbeat 存在但 TTL 已很小）→ 正常删除 heartbeat + metrics"""
        redis = MagicMock()
        redis.exists.side_effect = self._make_exists(hb=1, mt=1)
        redis.ttl.return_value = 0  # stale
        skipped, hb_deleted, mt_deleted = _cleanup_node(redis, "node-a")
        assert skipped is False
        assert hb_deleted is True and mt_deleted is True
        assert redis.delete.call_count == 2

    def test_no_data_returns_false_and_skips_delete(self):
        """无任何数据 → 不删"""
        redis = MagicMock()
        redis.exists.side_effect = self._make_exists(hb=0, mt=0)
        skipped, hb_deleted, mt_deleted = _cleanup_node(redis, "node-x")
        assert skipped is False
        assert hb_deleted is False and mt_deleted is False
        redis.delete.assert_not_called()

    def test_stale_node_heartbeat_only_deletes_heartbeat(self):
        """stale 节点且只有 heartbeat → 只删 heartbeat"""
        redis = MagicMock()
        redis.exists.side_effect = self._make_exists(hb=1, mt=0)
        redis.ttl.return_value = 0  # stale
        skipped, hb_deleted, mt_deleted = _cleanup_node(redis, "node-hb")
        assert skipped is False
        assert hb_deleted is True and mt_deleted is False
        assert redis.delete.call_count == 1

    def test_active_node_rejected_without_force(self):
        """#4945: 活跃节点（fresh heartbeat）默认拒绝清理，不删任何 key"""
        redis = MagicMock()
        redis.exists.side_effect = self._make_exists(hb=1, mt=1)
        redis.ttl.return_value = 20  # 活跃（≥ 阈值 5）
        skipped, hb_deleted, mt_deleted = _cleanup_node(redis, "node-a")
        assert skipped is True
        assert hb_deleted is False and mt_deleted is False
        redis.delete.assert_not_called()

    def test_active_node_force_overrides_guard(self):
        """#4945: force=True 强制清理活跃节点"""
        redis = MagicMock()
        redis.exists.side_effect = self._make_exists(hb=1, mt=1)
        redis.ttl.return_value = 20  # 活跃
        skipped, hb_deleted, mt_deleted = _cleanup_node(redis, "node-a", force=True)
        assert skipped is False
        assert hb_deleted is True and mt_deleted is True
        assert redis.delete.call_count == 2

    def test_never_expire_node_rejected_without_force(self):
        """#4945 review: TTL=-1（永不过期异常 heartbeat）默认拒绝清理，与 heartbeat_manager 保守口径一致。"""
        redis = MagicMock()
        redis.exists.side_effect = self._make_exists(hb=1, mt=1)
        redis.ttl.return_value = -1  # 永不过期（异常）
        skipped, hb_deleted, mt_deleted = _cleanup_node(redis, "node-a")
        assert skipped is True
        assert hb_deleted is False and mt_deleted is False
        redis.delete.assert_not_called()


# ---------------------------------------------------------------------------
# cleanup 命令端到端（#5980：默认 node_id 应扫描所有节点，非硬编码 execution_node_1）
# ---------------------------------------------------------------------------


@pytest.mark.unit
@pytest.mark.cli
class TestCleanupCommand:
    """cleanup 命令：扫描/指定节点清理 + #4945 活跃守卫。"""

    def test_no_node_id_scans_all_stale_nodes(self, cli_runner):
        """#5980: 不带 --node-id 应扫描所有 heartbeat keys 逐个清理（stale 节点）"""
        redis = MagicMock()
        prefix = f"{RedisKeyPrefix.EXECUTION_NODE_HEARTBEAT}:"
        redis.keys.return_value = [
            f"{prefix}node-a".encode(),
            f"{prefix}node-b".encode(),
        ]
        redis.exists.return_value = 1  # 每节点 heartbeat+metrics 均存在
        redis.ttl.return_value = 0  # stale，可清理

        with patch("ginkgo.data.crud.RedisCRUD") as MockCRUD:
            MockCRUD.return_value.redis = redis
            result = cli_runner.invoke(app, ["cleanup"])

        assert result.exit_code == 0
        redis.keys.assert_called_once_with(RedisKeyPattern.EXECUTION_NODE_HEARTBEAT_ALL)
        # 2 节点 × (heartbeat + metrics) = 4 次 delete
        assert redis.delete.call_count == 4
        assert "node-a" in result.output
        assert "node-b" in result.output

    def test_with_node_id_cleans_stale(self, cli_runner):
        """指定 --node-id 清 stale 节点"""
        redis = MagicMock()
        redis.exists.return_value = 1
        redis.ttl.return_value = 0  # stale

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

    # --- #4945: 活跃守卫命令级行为 ---

    def test_active_node_with_id_refused_without_force(self, cli_runner):
        """#4945: --node-id 指定活跃节点 → 拒绝清理，不删任何 key"""
        redis = MagicMock()
        redis.exists.return_value = 1
        redis.ttl.return_value = 20  # 活跃

        with patch("ginkgo.data.crud.RedisCRUD") as MockCRUD:
            MockCRUD.return_value.redis = redis
            result = cli_runner.invoke(app, ["cleanup", "--node-id", "live-host"])

        assert result.exit_code == 0  # 拒绝但非错误退出
        redis.delete.assert_not_called()
        out = result.output.lower()
        assert "running" in out or "fresh" in out  # 明确告知节点在运行
        # #4945 表象：拒绝时绝不能出现"调度器会判定它离线"的误导语（那正是 bug）
        assert "will detect" not in out and "detect this node as offline" not in out

    def test_active_node_with_id_force_cleans(self, cli_runner):
        """#4945: --force 强制清理活跃节点"""
        redis = MagicMock()
        redis.exists.return_value = 1
        redis.ttl.return_value = 20  # 活跃

        with patch("ginkgo.data.crud.RedisCRUD") as MockCRUD:
            MockCRUD.return_value.redis = redis
            result = cli_runner.invoke(app, ["cleanup", "--node-id", "live-host", "--force"])

        assert result.exit_code == 0
        assert redis.delete.call_count == 2  # force 跳过守卫，正常删
        assert "live-host" in result.output

    def test_scan_all_skips_active_and_cleans_stale(self, cli_runner):
        """#4945: scan-all 混合场景——活跃节点跳过 + stale 节点清理 + 统计 skipped"""
        redis = MagicMock()
        prefix = f"{RedisKeyPrefix.EXECUTION_NODE_HEARTBEAT}:"
        redis.keys.return_value = [
            f"{prefix}stale-node".encode(),
            f"{prefix}live-node".encode(),
        ]
        redis.exists.return_value = 1  # 所有 key 存在

        def fake_ttl(key):
            k = key.decode() if isinstance(key, bytes) else key
            return 20 if "live" in k else 3  # live 活跃，stale 即将过期

        redis.ttl.side_effect = fake_ttl

        with patch("ginkgo.data.crud.RedisCRUD") as MockCRUD:
            MockCRUD.return_value.redis = redis
            result = cli_runner.invoke(app, ["cleanup"])

        assert result.exit_code == 0
        # stale-node: hb+mt = 2 delete；live-node: 0 delete
        assert redis.delete.call_count == 2
        out = result.output.lower()
        assert "stale-node" in result.output
        assert "live-node" in result.output
        # 活跃跳过提示
        assert "running" in out or "skipped" in out


# ---------------------------------------------------------------------------
# _is_node_active deep module (#4945：cleanup 删前必须判活)
# ---------------------------------------------------------------------------


@pytest.mark.unit
@pytest.mark.cli
class TestIsNodeActive:
    """_is_node_active：查 heartbeat TTL 判断节点是否活跃（复用 status 命令阈值）。"""

    def test_fresh_heartbeat_is_active(self):
        """TTL ≥ 阈值 → 活跃（运行中，不应清理）"""
        redis = MagicMock()
        redis.exists.return_value = 1
        redis.ttl.return_value = 20  # 30s TTL 还剩 20s，刚刷新
        assert _is_node_active(redis, "node-a") is True

    def test_stale_heartbeat_is_not_active(self):
        """TTL < 阈值（即将过期）→ 不活跃（可清理）"""
        redis = MagicMock()
        redis.exists.return_value = 1
        redis.ttl.return_value = 3  # < 5s 阈值，stale
        assert _is_node_active(redis, "node-a") is False

    def test_no_heartbeat_is_not_active(self):
        """heartbeat 不存在 → 不活跃"""
        redis = MagicMock()
        redis.exists.return_value = 0
        assert _is_node_active(redis, "node-a") is False
        redis.ttl.assert_not_called()  # 短路，不查 TTL

    def test_never_expire_heartbeat_is_active(self):
        """TTL=-1（key 存在但永不过期，异常情况）→ 保守判活（#4945 review）。

        与 heartbeat_manager._check_node_id_in_use 口径一致：永不过期的 heartbeat
        视为"被占用=有实例运行"，cleanup 拒绝清理（需 --force），避免清掉可能的活跃节点。
        """
        redis = MagicMock()
        redis.exists.return_value = 1
        redis.ttl.return_value = -1  # Redis: key 存在但无过期时间
        assert _is_node_active(redis, "node-a") is True
