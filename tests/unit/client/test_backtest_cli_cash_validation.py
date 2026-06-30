"""TDD tests for #6004: ginkgo backtest create --cash 无上下界校验。

create_task 应在 portfolio 校验前拒绝非正 cash（#5983 安全核心），
并对范围外（<1,000 或 >100亿）发出警告（#6004 合理范围）。
"""
import sys
from pathlib import Path

project_root = Path(__file__).parent.parent.parent.parent
_path = str(project_root / "src")
if _path not in sys.path:
    sys.path.insert(0, _path)

import re
from unittest.mock import MagicMock, patch
from typer.testing import CliRunner

runner = CliRunner()


def _strip_ansi(text: str) -> str:
    return re.sub(r"\x1b\[[0-9;]*m", "", text)


class TestBacktestCreateCashValidation:
    """#6004 backtest create --cash 校验"""

    @patch("ginkgo.data.containers.container")
    def test_create_rejects_nonpositive_cash(self, mock_container):
        """#5983/#6004 cash=0 与 cash=-1 应被拒绝（exit 1，消息提及 cash）"""
        from ginkgo.client.backtest_cli import app

        for bad_cash in ["0", "-1"]:
            result = runner.invoke(app, [
                "create", "--portfolio", "p-1",
                "--start", "2025-05-07", "--end", "2026-05-07",
                "--cash", bad_cash,
            ])
            assert result.exit_code == 1, f"cash={bad_cash} 应被拒绝（exit 1）"
            plain = _strip_ansi(result.output).lower()
            assert "cash" in plain, f"cash={bad_cash} 拒绝消息应提及 cash，实际：{plain!r}"

    @patch("ginkgo.workers.backtest_worker.task_helpers.load_portfolio_components")
    @patch("ginkgo.data.containers.container")
    def test_create_warns_extreme_high_cash(self, mock_container, mock_load):
        """#6004 极端高 cash（>100亿）应警告但仍创建"""
        from ginkgo.client.backtest_cli import app

        mock_ps = MagicMock()
        pr = MagicMock()
        pr.is_success.return_value = True
        mock_ps.get.return_value = pr
        mock_container.portfolio_service.return_value = mock_ps
        mock_load.return_value = None  # 组件加载成功

        mock_bs = MagicMock()
        cr = MagicMock()
        cr.is_success.return_value = True
        cr.data = MagicMock(uuid="bt-1")
        mock_bs.create.return_value = cr
        mock_container.backtest_task_service.return_value = mock_bs

        result = runner.invoke(app, [
            "create", "--portfolio", "p-1",
            "--start", "2025-05-07", "--end", "2026-05-07",
            "--cash", "999999999999",
        ])
        assert result.exit_code == 0, "极端 cash 应警告但仍创建"
        plain = _strip_ansi(result.output)
        assert "警告" in plain or "warn" in plain.lower(), f"极端 cash 应有警告，实际：{plain!r}"
