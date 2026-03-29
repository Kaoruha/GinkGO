# tests/unit/workers/test_paper_trading_worker.py
import pytest
from unittest.mock import MagicMock


class TestPaperTradingWorker:
    def test_on_paper_trading_command_calls_all_controllers(self):
        """收到 paper_trading 命令时应调用所有 controller"""
        from ginkgo.workers.paper_trading_worker import PaperTradingWorker

        worker = PaperTradingWorker.__new__(PaperTradingWorker)
        worker._controllers = {
            "p1": MagicMock(),
            "p2": MagicMock(),
        }
        worker._lock = MagicMock()

        worker._handle_command("paper_trading", {})

        worker._controllers["p1"].run_daily_cycle.assert_called_once()
        worker._controllers["p2"].run_daily_cycle.assert_called_once()

    def test_register_controller_stores_controller(self):
        """register_controller 应存储 controller 到内部字典"""
        from ginkgo.workers.paper_trading_worker import PaperTradingWorker

        worker = PaperTradingWorker.__new__(PaperTradingWorker)
        worker._controllers = {}
        worker._lock = MagicMock()

        mock_controller = MagicMock()
        worker.register_controller("portfolio_123", mock_controller)

        assert "portfolio_123" in worker._controllers
        assert worker._controllers["portfolio_123"] is mock_controller

    def test_unregister_controller_removes_controller(self):
        """unregister_controller 应移除 controller"""
        from ginkgo.workers.paper_trading_worker import PaperTradingWorker

        worker = PaperTradingWorker.__new__(PaperTradingWorker)
        worker._controllers = {"portfolio_123": MagicMock()}
        worker._lock = MagicMock()

        worker.unregister_controller("portfolio_123")

        assert "portfolio_123" not in worker._controllers

    def test_handle_unknown_command_returns_false(self):
        """未知命令应返回 False"""
        from ginkgo.workers.paper_trading_worker import PaperTradingWorker

        worker = PaperTradingWorker()
        result = worker._handle_command("unknown_cmd", {})
        assert result is False
