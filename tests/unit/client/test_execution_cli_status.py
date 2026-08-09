# coding:utf-8
"""execution_cli status 命令单元测试。

#5519: status 查所有 ExecutionNode 时用 scan_iter（游标式非阻塞），非 keys
（O(N) 阻塞 Redis 单线程）。收口后（#6300）scan_iter 下沉至 redis_service
.scan_execution_node_ids；CLI 层调用该方法，#5519 的 scan_iter-vs-keys 不变量
在 service 层断言（见 tests/unit/data/services/test_redis_service_execution_nodes.py）。
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


def _mock_services(node_ids=None, heartbeat_ttl=30, metrics=None):
    """构造 mock ginkgo.services：scan_execution_node_ids / get_node_heartbeat_ttl /
    get_execution_node_metrics 预设返回（service 层已 decode 为 str）。"""
    m = MagicMock()
    svc = m.data.redis_service.return_value
    svc.scan_execution_node_ids.return_value = ServiceResult.success(
        data=node_ids or [], message=str(len(node_ids or []))
    )
    svc.get_node_heartbeat_ttl.return_value = ServiceResult.success(
        data=heartbeat_ttl, message=f"TTL={heartbeat_ttl}"
    )
    svc.get_execution_node_metrics.return_value = ServiceResult.success(
        data=metrics or {}, message=str(len(metrics or {}))
    )
    return m


@pytest.mark.unit
@pytest.mark.cli
class TestExecutionStatusScanIter:
    """#5519 status 查所有节点经 redis_service.scan_execution_node_ids（内部 scan_iter 非阻塞）。"""

    def test_status_all_uses_scan_service_not_keys(self, cli_runner):
        """无 --node-id（查所有节点）时调 scan_execution_node_ids（#5519 scan 路径）。"""
        with patch("ginkgo.services", _mock_services(node_ids=[])) as mock_services:
            result = cli_runner.invoke(execution_cli.app, ["status"])

        assert result.exit_code == 0
        svc = mock_services.data.redis_service.return_value
        # 核心：走 scan-based service 方法（#5519 非阻塞扫描），CLI 层不碰 keys
        svc.scan_execution_node_ids.assert_called_once()

    def test_status_all_limit_passes_to_scan(self, cli_runner):
        """--limit 作为 scan_execution_node_ids 的 limit（COUNT hint + 结果上限，AC2）。"""
        with patch("ginkgo.services", _mock_services(node_ids=[])) as mock_services:
            result = cli_runner.invoke(execution_cli.app, ["status", "--limit", "50"])

        assert result.exit_code == 0
        svc = mock_services.data.redis_service.return_value
        svc.scan_execution_node_ids.assert_called_once_with(limit=50)
