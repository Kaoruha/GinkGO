# #6083 backtest create 日期校验（#5981/#5993/#5994/#6009）
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


class TestBacktestCreateDateValidation:
    """#6083 backtest create --start/--end 日期校验"""

    @patch("ginkgo.data.containers.container")
    def test_create_rejects_invalid_date_format(self, mock_container):
        """#5994 无效日期格式应被拒绝（exit 1，消息提及日期）"""
        from ginkgo.client.backtest_cli import app

        for bad_date in ["invalid", "2025-13-45", "2025/05/07"]:
            result = runner.invoke(app, [
                "create", "--portfolio", "p-1",
                "--start", bad_date, "--end", "2026-05-07",
                "--cash", "100000",
            ])
            assert result.exit_code == 1, f"start={bad_date!r} 应被拒绝（exit 1）"
            plain = _strip_ansi(result.output)
            assert "日期" in plain or "date" in plain.lower(), (
                f"start={bad_date!r} 拒绝消息应提及日期，实际：{plain!r}"
            )

    @patch("ginkgo.data.containers.container")
    def test_create_rejects_end_before_start(self, mock_container):
        """#5993 end < start 应被拒绝（exit 1）"""
        from ginkgo.client.backtest_cli import app

        result = runner.invoke(app, [
            "create", "--portfolio", "p-1",
            "--start", "2026-05-07", "--end", "2025-05-07",
            "--cash", "100000",
        ])
        assert result.exit_code == 1, "end < start 应被拒绝"
        plain = _strip_ansi(result.output)
        assert "结束" in plain or "开始" in plain or "end" in plain.lower() or "start" in plain.lower(), (
            f"end<start 拒绝消息应说明起止关系，实际：{plain!r}"
        )

    @patch("ginkgo.workers.backtest_worker.task_helpers.load_portfolio_components")
    @patch("ginkgo.data.containers.container")
    def test_create_warns_future_date(self, mock_container, mock_load):
        """#6009 未来日期应警告但仍创建"""
        from ginkgo.client.backtest_cli import app

        mock_ps = MagicMock()
        pr = MagicMock()
        pr.is_success.return_value = True
        mock_ps.get.return_value = pr
        mock_container.portfolio_service.return_value = mock_ps
        mock_load.return_value = None

        mock_bs = MagicMock()
        cr = MagicMock()
        cr.is_success.return_value = True
        cr.data = MagicMock(uuid="bt-1")
        mock_bs.create.return_value = cr
        mock_container.backtest_task_service.return_value = mock_bs

        result = runner.invoke(app, [
            "create", "--portfolio", "p-1",
            "--start", "2030-01-01", "--end", "2031-01-01",
            "--cash", "100000",
        ])
        assert result.exit_code == 0, "未来日期应警告但仍创建"
        plain = _strip_ansi(result.output)
        assert "警告" in plain or "warn" in plain.lower(), (
            f"未来日期应有警告，实际：{plain!r}"
        )
