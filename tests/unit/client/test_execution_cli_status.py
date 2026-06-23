# coding:utf-8
"""execution_cli status 命令单元测试。

#5519: status 查所有 ExecutionNode 时用 redis.keys()（O(N) 阻塞 Redis 单线程），
应改 scan_iter（游标式非阻塞）。
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
class TestExecutionStatusScanIter:
    """#5519 status 查所有节点用 scan_iter（非阻塞）而非 keys（阻塞 Redis）。"""

    def test_status_all_uses_scan_iter_not_keys(self, cli_runner):
        """无 --node-id（查所有节点）时用 scan_iter，不调用 keys（阻塞命令）。"""
        mock_redis = MagicMock()
        # scan_iter 返回空迭代 → status 优雅打印 "No ExecutionNodes" 后 return
        mock_redis.scan_iter.return_value = iter([])
        mock_crud = MagicMock()
        mock_crud.redis = mock_redis

        with patch("ginkgo.data.crud.RedisCRUD", return_value=mock_crud):
            result = cli_runner.invoke(execution_cli.app, ["status"])

        assert result.exit_code == 0
        assert not isinstance(result.exception, TypeError)
        # 核心：不用 keys（O(N) 阻塞 Redis 单线程）
        mock_redis.keys.assert_not_called()
        # 改用 scan_iter（游标式非阻塞）
        mock_redis.scan_iter.assert_called_once()

    def test_status_all_limit_passes_scan_count_hint(self, cli_runner):
        """--limit 作为 scan_iter count hint（限制扫描批次大小，AC2）。"""
        mock_redis = MagicMock()
        mock_redis.scan_iter.return_value = iter([])
        mock_crud = MagicMock()
        mock_crud.redis = mock_redis

        with patch("ginkgo.data.crud.RedisCRUD", return_value=mock_crud):
            result = cli_runner.invoke(execution_cli.app, ["status", "--limit", "50"])

        assert result.exit_code == 0
        assert mock_redis.scan_iter.call_args.kwargs.get("count") == 50
