# tests/unit/client/test_paper_trading_cli.py
import pytest
from unittest.mock import MagicMock, patch
from typer.testing import CliRunner


class TestPaperTradingDeployCLI:
    def test_deploy_command_exists(self):
        """deploy 命令应在 CLI 中注册"""
        from ginkgo.client.portfolio_cli import app

        # 检查 deploy 命令在已注册命令列表中
        registered = [cmd for cmd in app.registered_commands if cmd.name == "deploy"]
        assert len(registered) > 0, "deploy command should be registered"

    def test_stop_command_exists(self):
        """stop 命令应在 CLI 中注册"""
        from ginkgo.client.portfolio_cli import app

        registered = [cmd for cmd in app.registered_commands if cmd.name == "stop"]
        assert len(registered) > 0, "stop command should be registered"

    def test_deploy_command_creates_portfolio_and_engine(self):
        """deploy 应调用 _deploy_paper_trading 函数"""
        from ginkgo.client.portfolio_cli import app, _deploy_paper_trading

        original = _deploy_paper_trading
        try:
            from ginkgo.client import portfolio_cli
            portfolio_cli._deploy_paper_trading = lambda source_portfolio_id, capital: "paper_portfolio_123"

            runner = CliRunner()
            result = runner.invoke(app, [
                "deploy",
                "--source", "backtest_portfolio_456",
                "--capital", "100000",
            ])
        finally:
            portfolio_cli._deploy_paper_trading = original

        assert result.exit_code == 0
        assert "paper_portfolio_123" in result.output
