# #5329 backtest cat 输出提示 result show 用法
import sys
from pathlib import Path

project_root = Path(__file__).parent.parent.parent.parent
_path = str(project_root / "src")
if _path not in sys.path:
    sys.path.insert(0, _path)

import re
import pytest
from unittest.mock import MagicMock, patch
from typer.testing import CliRunner

runner = CliRunner()


def _strip_ansi(text: str) -> str:
    """去除 ANSI 转义码"""
    return re.sub(r"\x1b\[[0-9;]*m", "", text)


def _mock_task():
    """构造一个 mock backtest task 对象"""
    task = MagicMock()
    task.uuid = "abc123456789"
    task.task_id = "task-run-id-001"
    task.name = "Test Backtest"
    task.portfolio_id = "port-001"
    task.engine_id = "engine-001"
    task.status = "completed"
    task.progress = 100
    task.create_at = "2025-01-01"
    task.start_time = "2025-01-01T10:00:00"
    task.end_time = "2025-01-01T10:05:00"
    task.duration_seconds = "300"
    task.error_message = None
    task.config_snapshot = None
    # metrics（float 属性，0.0 跳过展示块）
    task.final_portfolio_value = 0.0
    task.total_pnl = 0.0
    task.max_drawdown = 0.0
    task.sharpe_ratio = 0.0
    task.annual_return = 0.0
    task.win_rate = 0.0
    # stats（int 属性，0 跳过展示块）
    task.total_signals = 0
    task.total_orders = 0
    task.total_positions = 0
    task.total_events = 0
    return task


class TestBacktestCatResultHint:
    """#5329 backtest cat 应提示 result show 用法"""

    @patch("ginkgo.data.containers.container")
    def test_cat_shows_result_show_hint(self, mock_container):
        """#5329 backtest cat 输出应包含 result show --run-id 提示"""
        from ginkgo.client.backtest_cli import app

        mock_service = MagicMock()
        result = MagicMock()
        result.is_success.return_value = True
        result.data = _mock_task()
        mock_service.get_by_id.return_value = result
        mock_container.backtest_task_service.return_value = mock_service

        invoke_result = runner.invoke(app, ["cat", "task-run-id-001"])
        assert invoke_result.exit_code == 0

        plain = _strip_ansi(invoke_result.output)
        # 应包含提示，指引用户使用 result show --run-id
        assert "result show --run-id" in plain
        # 提示应包含实际的 task_id
        assert "task-run-id-001" in plain


class TestBacktestListProgressFormat:
    """#5323 list 命令 progress 格式化应为 N% 而非 N00%"""

    @patch("ginkgo.data.containers.container")
    def test_list_shows_correct_progress_percentage(self, mock_container):
        """#5323 progress=50 应显示 50% 而非 5000%"""
        from ginkgo.client.backtest_cli import app

        task = _mock_task()
        task.progress = 50

        mock_service = MagicMock()
        list_result = MagicMock()
        list_result.is_success.return_value = True
        list_result.data = {"data": [task], "total": 1}
        mock_service.list.return_value = list_result
        mock_container.backtest_task_service.return_value = mock_service

        invoke_result = runner.invoke(app, ["list"])
        assert invoke_result.exit_code == 0

        plain = _strip_ansi(invoke_result.output)
        # progress=50 应显示 "50%" 而非 "5000%"
        assert "50%" in plain
        assert "5000%" not in plain

    @patch("ginkgo.data.containers.container")
    def test_list_shows_100_percent_on_completed(self, mock_container):
        """#5323 completed 任务 progress=100 应显示 100%"""
        from ginkgo.client.backtest_cli import app

        task = _mock_task()
        task.progress = 100
        task.status = "completed"

        mock_service = MagicMock()
        list_result = MagicMock()
        list_result.is_success.return_value = True
        list_result.data = {"data": [task], "total": 1}
        mock_service.list.return_value = list_result
        mock_container.backtest_task_service.return_value = mock_service

        invoke_result = runner.invoke(app, ["list"])
        assert invoke_result.exit_code == 0

        plain = _strip_ansi(invoke_result.output)
        assert "100%" in plain
        assert "10000%" not in plain


class TestBacktestCatNoTradesWarning:
    """#5322 completed 回测无交易时应显示警告"""

    @patch("ginkgo.data.containers.container")
    def test_cat_shows_no_trades_warning_when_zero_stats(self, mock_container):
        """#5322 completed 回测 stats 全为 0 时应显示 'No trades' 提示"""
        from ginkgo.client.backtest_cli import app

        task = _mock_task()
        task.status = "completed"
        # stats 全为 0（默认值）
        task.total_signals = 0
        task.total_orders = 0
        task.total_positions = 0
        task.total_events = 0

        mock_service = MagicMock()
        result = MagicMock()
        result.is_success.return_value = True
        result.data = task
        mock_service.get_by_id.return_value = result
        mock_container.backtest_task_service.return_value = mock_service

        invoke_result = runner.invoke(app, ["cat", "abc123456789"])
        assert invoke_result.exit_code == 0

        plain = _strip_ansi(invoke_result.output)
        assert "No trades" in plain or "未产生" in plain or "no trades" in plain.lower()
