"""
Worker CLI 单元测试

测试 ginkgo.client.worker_cli 的所有命令：
- worker data run: 前台运行数据 worker
- worker data status: 查看数据 worker 状态
- worker backtest run: 前台运行回测 worker
- worker backtest status: 查看回测 worker 状态
"""

import os

os.environ["GINKGO_SKIP_DEBUG_CHECK"] = "1"

import json
from unittest.mock import patch, MagicMock

import pytest
from typer.testing import CliRunner

from ginkgo.client import worker_cli


@pytest.fixture
def cli_runner():
    return CliRunner()


# ============================================================================
# 1. Help 测试
# ============================================================================


@pytest.mark.unit
@pytest.mark.cli
class TestWorkerCLIHelp:
    """worker 命令帮助信息"""

    def test_root_help_shows_subgroups(self, cli_runner):
        """worker --help 显示 data 和 backtest 子命令组"""
        result = cli_runner.invoke(worker_cli.app, ["--help"])
        assert result.exit_code == 0
        assert "data" in result.output
        assert "backtest" in result.output

    def test_data_help_shows_commands(self, cli_runner):
        """worker data --help 显示 run 和 status 子命令"""
        result = cli_runner.invoke(worker_cli.app, ["data", "--help"])
        assert result.exit_code == 0
        assert "run" in result.output
        assert "status" in result.output


# ============================================================================
# 2. Main Commands Happy Path
# ============================================================================


@pytest.mark.unit
@pytest.mark.cli
class TestDataWorkerRun:
    """worker data run 命令"""

    def test_data_run_starts_worker(self, cli_runner):
        """data run 启动数据 worker 并成功退出"""
        mock_gtm = MagicMock()
        mock_gtm.run_data_worker.side_effect = KeyboardInterrupt

        with patch("ginkgo.libs.core.threading.GinkgoThreadManager", return_value=mock_gtm):
            result = cli_runner.invoke(worker_cli.app, ["data", "run"])
        assert result.exit_code == 0
        assert "Starting data worker" in result.output

    def test_data_run_debug_mode(self, cli_runner):
        """data run --debug 启用调试模式"""
        mock_gtm = MagicMock()
        mock_gtm.run_data_worker.side_effect = KeyboardInterrupt

        with patch("ginkgo.libs.core.threading.GinkgoThreadManager", return_value=mock_gtm), \
             patch("ginkgo.client.worker_cli.GLOG"):
            result = cli_runner.invoke(worker_cli.app, ["data", "run", "--debug"])
        assert result.exit_code == 0


@pytest.mark.unit
@pytest.mark.cli
class TestDataWorkerStatus:
    """worker data status 命令"""

    def test_data_status_shows_summary(self, cli_runner):
        """data status 显示 worker 汇总信息"""
        mock_gtm = MagicMock()
        mock_gtm.get_workers_status.return_value = [
            {"pid": "1001", "status": "running", "cpu_percent": 1.5, "memory_mb": 128.0, "tasks": 3},
            {"pid": "1002", "status": "idle", "cpu_percent": 0.0, "memory_mb": 64.0, "tasks": 0},
        ]

        with patch("ginkgo.libs.core.threading.GinkgoThreadManager", return_value=mock_gtm):
            result = cli_runner.invoke(worker_cli.app, ["data", "status"])
        assert result.exit_code == 0
        assert "Data Worker Status Summary" in result.output
        assert "Total Workers" in result.output

    def test_data_status_raw_outputs_json(self, cli_runner):
        """data status --raw 输出 JSON 格式"""
        mock_gtm = MagicMock()
        mock_gtm.get_workers_status.return_value = [
            {"pid": "1001", "status": "running"},
        ]

        with patch("ginkgo.libs.core.threading.GinkgoThreadManager", return_value=mock_gtm):
            result = cli_runner.invoke(worker_cli.app, ["data", "status", "--raw"])
        assert result.exit_code == 0
        assert "1001" in result.output
        assert "running" in result.output


@pytest.mark.unit
@pytest.mark.cli
class TestBacktestWorkerStatus:
    """worker backtest status 命令"""

    def test_backtest_status_no_workers(self, cli_runner):
        """backtest status 无活跃 worker 时显示提示"""
        mock_redis = MagicMock()
        mock_redis.keys.return_value = []

        with patch("ginkgo.data.drivers.create_redis_connection", return_value=mock_redis):
            result = cli_runner.invoke(worker_cli.app, ["backtest", "status"])
        assert result.exit_code == 0
        assert "No active BacktestWorkers" in result.output

    def test_backtest_status_with_worker(self, cli_runner):
        """backtest status 有活跃 worker 时显示状态"""
        mock_redis = MagicMock()
        worker_data = json.dumps({
            "worker_id": "worker_1",
            "status": "running",
            "running_tasks": 2,
            "max_tasks": 5,
            "last_heartbeat": "2026-03-29T10:00:00",
        })
        mock_redis.keys.return_value = [b"backtest:worker:worker_1"]
        mock_redis.get.return_value = worker_data

        with patch("ginkgo.data.drivers.create_redis_connection", return_value=mock_redis):
            result = cli_runner.invoke(worker_cli.app, ["backtest", "status"])
        assert result.exit_code == 0
        assert "BacktestWorker Status Summary" in result.output
        assert "worker_1" in result.output


# ============================================================================
# 3. Validation / Errors
# ============================================================================


@pytest.mark.unit
@pytest.mark.cli
class TestWorkerValidation:
    """worker 命令参数验证"""

    def test_data_status_pid_not_found(self, cli_runner):
        """data status --pid 查找不存在的 worker 时显示提示"""
        mock_gtm = MagicMock()
        mock_gtm.get_worker_status.return_value = None

        with patch("ginkgo.libs.core.threading.GinkgoThreadManager", return_value=mock_gtm):
            result = cli_runner.invoke(worker_cli.app, ["data", "status", "--pid", "99999"])
        assert result.exit_code == 0
        assert "not found" in result.output

    def test_backtest_status_worker_not_found(self, cli_runner):
        """backtest status --worker-id 查找不存在的 worker 时显示提示"""
        mock_redis = MagicMock()
        mock_redis.get.return_value = None

        with patch("ginkgo.data.drivers.create_redis_connection", return_value=mock_redis):
            result = cli_runner.invoke(worker_cli.app, ["backtest", "status", "--worker-id", "ghost"])
        assert result.exit_code == 0
        assert "not found" in result.output


# ============================================================================
# 4. Exception Handling
# ============================================================================


@pytest.mark.unit
@pytest.mark.cli
class TestWorkerExceptions:
    """worker 命令异常处理"""

    def test_data_run_worker_error_exits(self, cli_runner):
        """data run worker 运行出错时以 exit code 1 退出"""
        mock_gtm = MagicMock()
        mock_gtm.run_data_worker.side_effect = RuntimeError("Worker crashed")

        with patch("ginkgo.libs.core.threading.GinkgoThreadManager", return_value=mock_gtm):
            result = cli_runner.invoke(worker_cli.app, ["data", "run"])
        assert result.exit_code == 1
        assert "Worker error" in result.output

    def test_backtest_status_redis_error_exits(self, cli_runner):
        """backtest status Redis 连接失败时以 exit code 1 退出"""
        with patch("ginkgo.data.drivers.create_redis_connection", side_effect=Exception("Connection refused")):
            result = cli_runner.invoke(worker_cli.app, ["backtest", "status"])
        assert result.exit_code == 1
        assert "Error getting status" in result.output
