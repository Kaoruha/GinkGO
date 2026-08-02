"""TDD tests for epic slippage: CLI backtest create --fill-price-policy 暴露方案 B 选择。

epic 核心痛点 "--slippage 死参数": CLI 有 --slippage 但 (方案 B 前) 从不进 SimBroker,
interface 撒谎。方案 B 引入 fill_price_policy(attitude/slippage)分离"模型选择"与
"费率值"; CLI 须暴露 --fill-price-policy 让用户显式选 slippage 激活 --slippage,
interface 不再撒谎。

- 默认 attitude = 零回归 (态度采样, 移植原 scipy 逻辑)
- 显式 slippage 接通 DeterministicSlippage, --slippage 此时生效
"""
import json
import re
from unittest.mock import MagicMock, patch

from typer.testing import CliRunner

runner = CliRunner()


def _strip_ansi(s):
    return re.compile(r"\x1b\[[0-9;]*m").sub("", s)


class TestCreateFillPricePolicyOption:
    """epic: CLI create --fill-price-policy 暴露方案 B 显式选择。"""

    @patch("ginkgo.workers.backtest_worker.task_helpers.load_portfolio_components")
    @patch("ginkgo.data.containers.container")
    def test_slippage_policy_written_to_config_snapshot(self, mock_container, mock_load):
        """--fill-price-policy slippage 写入 config_snapshot (激活 --slippage)。"""
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
            "--start", "2025-05-07", "--end", "2026-05-07",
            "--fill-price-policy", "slippage",
        ])
        assert result.exit_code == 0, f"应成功创建: {_strip_ansi(result.output)!r}"
        _, kwargs = mock_bs.create.call_args
        assert kwargs["config_snapshot"]["fill_price_policy"] == "slippage", (
            "--fill-price-policy slippage 须写入 config_snapshot"
        )

    @patch("ginkgo.workers.backtest_worker.task_helpers.load_portfolio_components")
    @patch("ginkgo.data.containers.container")
    def test_default_policy_is_attitude_zero_regression(self, mock_container, mock_load):
        """不带 --fill-price-policy 默认 attitude (零回归基线)。"""
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
            "--start", "2025-05-07", "--end", "2026-05-07",
        ])
        assert result.exit_code == 0
        _, kwargs = mock_bs.create.call_args
        assert kwargs["config_snapshot"]["fill_price_policy"] == "attitude", (
            "默认 fill_price_policy=attitude (零回归)"
        )


class TestEditFillPricePolicyOption:
    """epic: CLI edit --fill-price-policy 与 create 对称 (避免新半接)。"""

    @patch("ginkgo.data.containers.container")
    def test_edit_updates_fill_price_policy(self, mock_container):
        """edit --fill-price-policy slippage 更新已存在 task 的 config_snapshot。"""
        from ginkgo.client.backtest_cli import app

        mock_bs = MagicMock()
        existing = MagicMock()
        existing.is_success.return_value = True
        existing.data = MagicMock(
            status="running",
            config_snapshot='{"start_date": "2025-01-01", "fill_price_policy": "attitude"}',
        )
        mock_bs.get_by_id.return_value = existing
        update_cr = MagicMock()
        update_cr.is_success.return_value = True
        mock_bs.update.return_value = update_cr
        mock_container.backtest_task_service.return_value = mock_bs

        result = runner.invoke(app, [
            "edit", "task-1", "--fill-price-policy", "slippage",
        ])
        assert result.exit_code == 0, f"应成功更新: {_strip_ansi(result.output)!r}"
        _, kwargs = mock_bs.update.call_args
        updated_snap = json.loads(kwargs["config_snapshot"])
        assert updated_snap["fill_price_policy"] == "slippage", (
            "edit --fill-price-policy slippage 须更新 config_snapshot"
        )
