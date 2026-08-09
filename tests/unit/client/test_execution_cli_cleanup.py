"""
execution cleanup 命令端到端测试（#5980/#4945/#5519/#6300）。

收口后（#6300/#6115）cleanup 命令不再直连 Redis：
- 节点枚举走 redis_service.scan_execution_node_ids（#5519 scan_iter 非阻塞）
- 清理逻辑（判活 #4945 + 删除 #5980 + dry-run）走 redis_service.cleanup_execution_node

故本文件只断言命令的**编排/输出**（scan→per-node cleanup→统计/提示），删除/判活的
底层不变量（活跃守卫、force、dry-run 不删）下沉至 service 层测试
（见 tests/unit/data/services/test_redis_service_execution_nodes.py）。
"""

import os

os.environ["GINKGO_SKIP_DEBUG_CHECK"] = "1"

import pytest
from unittest.mock import MagicMock, patch
from typer.testing import CliRunner

from ginkgo.client.execution_cli import app
from ginkgo.data.services.base_service import ServiceResult


@pytest.fixture
def cli_runner():
    return CliRunner()


# ---------------------------------------------------------------------------
# ServiceResult 构造 helper（与 service 层 cleanup_execution_node 返回契约一致）
# ---------------------------------------------------------------------------


def _cleaned(hb=True, mt=True):
    """清理成功（skipped_active=False）：heartbeat/metrics 按存在性置删除标志。"""
    return ServiceResult.success(
        data={"skipped_active": False, "heartbeat_deleted": hb, "metrics_deleted": mt}
    )


def _skipped():
    """活跃守卫拒绝（fresh heartbeat，#4945）：跳过，不删任何 key。"""
    return ServiceResult.success(
        data={"skipped_active": True, "heartbeat_deleted": False, "metrics_deleted": False}
    )


def _mock_services():
    """构造 mock ginkgo.services，返回其 redis_service mock 供各 test 精细配置。"""
    m = MagicMock()
    svc = m.data.redis_service.return_value
    return m, svc


# ---------------------------------------------------------------------------
# cleanup 命令端到端（#5980：默认扫描所有节点；#4945：活跃守卫；#5519：scan 枚举）
# ---------------------------------------------------------------------------


@pytest.mark.unit
@pytest.mark.cli
class TestCleanupCommand:
    """cleanup 命令：scan/指定节点清理 + #4945 活跃守卫（经 redis_service，不直连 Redis）。"""

    def test_no_node_id_scans_all_stale_nodes(self, cli_runner):
        """#5980/#5519: 不带 --node-id 调 scan_execution_node_ids 逐个清理（stale 节点）。"""
        mock_services, svc = _mock_services()
        svc.scan_execution_node_ids.return_value = ServiceResult.success(data=["node-a", "node-b"])
        svc.cleanup_execution_node.return_value = _cleaned()

        with patch("ginkgo.services", mock_services):
            result = cli_runner.invoke(app, ["cleanup"])

        assert result.exit_code == 0
        # #5519: 节点枚举走 scan service（CLI 不再 keys）
        svc.scan_execution_node_ids.assert_called_once()
        # 2 个节点各调一次 cleanup service
        assert svc.cleanup_execution_node.call_count == 2
        assert "node-a" in result.output
        assert "node-b" in result.output
        # 实清非 dry-run → 打印调度器将判定离线
        assert "will detect" in result.output.lower()

    def test_with_node_id_cleans_stale(self, cli_runner):
        """指定 --node-id 清 stale 节点（不 scan，单点 cleanup service）。"""
        mock_services, svc = _mock_services()
        svc.cleanup_execution_node.return_value = _cleaned()

        with patch("ginkgo.services", mock_services):
            result = cli_runner.invoke(app, ["cleanup", "--node-id", "my-host"])

        assert result.exit_code == 0
        svc.scan_execution_node_ids.assert_not_called()
        svc.cleanup_execution_node.assert_called_once()
        assert svc.cleanup_execution_node.call_args.args[0] == "my-host"
        assert "my-host" in result.output
        assert "heartbeat" in result.output.lower()

    def test_no_nodes_found_shows_warning(self, cli_runner):
        """scan 返回空 → 提示，不调 cleanup service。"""
        mock_services, svc = _mock_services()
        svc.scan_execution_node_ids.return_value = ServiceResult.success(data=[])

        with patch("ginkgo.services", mock_services):
            result = cli_runner.invoke(app, ["cleanup"])

        assert result.exit_code == 0
        svc.cleanup_execution_node.assert_not_called()
        assert "No ExecutionNodes" in result.output or "no heartbeat" in result.output.lower()

    # --- #4945: 活跃守卫命令级行为 ---

    def test_active_node_with_id_refused_without_force(self, cli_runner):
        """#4945: --node-id 指定活跃节点 → service 返回 skipped_active，命令拒绝，不删。"""
        mock_services, svc = _mock_services()
        svc.cleanup_execution_node.return_value = _skipped()

        with patch("ginkgo.services", mock_services):
            result = cli_runner.invoke(app, ["cleanup", "--node-id", "live-host"])

        assert result.exit_code == 0  # 拒绝但非错误退出
        svc.cleanup_execution_node.assert_called_once()
        out = result.output.lower()
        assert "running" in out or "fresh" in out  # 明确告知节点在运行
        # #4945 表象：拒绝时绝不能出现"调度器会判定它离线"的误导语（那正是 bug）
        assert "will detect" not in out and "detect this node as offline" not in out

    def test_active_node_with_id_force_cleans(self, cli_runner):
        """#4945: --force 透传 service，强制清理活跃节点。"""
        mock_services, svc = _mock_services()
        svc.cleanup_execution_node.return_value = _cleaned()

        with patch("ginkgo.services", mock_services):
            result = cli_runner.invoke(app, ["cleanup", "--node-id", "live-host", "--force"])

        assert result.exit_code == 0
        svc.cleanup_execution_node.assert_called_once()
        assert svc.cleanup_execution_node.call_args.kwargs.get("force") is True
        assert "live-host" in result.output

    def test_scan_all_skips_active_and_cleans_stale(self, cli_runner):
        """#4945: scan-all 混合——活跃节点跳过 + stale 节点清理 + 统计 skipped。"""
        mock_services, svc = _mock_services()
        svc.scan_execution_node_ids.return_value = ServiceResult.success(data=["stale-node", "live-node"])

        def cleanup_side(node_id, **kw):
            return _skipped() if node_id == "live-node" else _cleaned()

        svc.cleanup_execution_node.side_effect = cleanup_side

        with patch("ginkgo.services", mock_services):
            result = cli_runner.invoke(app, ["cleanup"])

        assert result.exit_code == 0
        # 两节点都进了 cleanup service（守卫判定在 service 内）
        assert svc.cleanup_execution_node.call_count == 2
        assert "stale-node" in result.output
        assert "live-node" in result.output
        # 活跃跳过提示
        out = result.output.lower()
        assert "running" in out or "skipped" in out
