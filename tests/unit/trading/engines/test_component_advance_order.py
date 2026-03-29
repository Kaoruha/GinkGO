# tests/unit/trading/engines/test_component_advance_order.py
import pytest
from unittest.mock import MagicMock, patch
from datetime import datetime


class TestComponentAdvanceOrder:
    def test_advance_time_to_allows_paper_mode(self):
        """验证 PAPER 模式可以调用 advance_time_to"""
        from ginkgo.trading.engines.time_controlled_engine import TimeControlledEventEngine
        from ginkgo.enums import EXECUTION_MODE

        engine = TimeControlledEventEngine(
            name="test_paper_mode",
            mode=EXECUTION_MODE.PAPER,
            logical_time_start=datetime(2026, 3, 30, 9, 30),
            timer_interval=0.01,
        )

        engine.start()
        result = engine.advance_time_to(datetime(2026, 3, 31, 15, 0))
        engine.stop()

        assert result is True, "PAPER mode should allow advance_time_to"

    def test_advance_time_to_allows_paper_auto_mode(self):
        """验证 PAPER_AUTO 模式可以调用 advance_time_to"""
        from ginkgo.trading.engines.time_controlled_engine import TimeControlledEventEngine
        from ginkgo.enums import EXECUTION_MODE

        engine = TimeControlledEventEngine(
            name="test_paper_auto_mode",
            mode=EXECUTION_MODE.PAPER_AUTO,
            logical_time_start=datetime(2026, 3, 30, 9, 30),
            timer_interval=0.01,
        )

        engine.start()
        result = engine.advance_time_to(datetime(2026, 3, 31, 15, 0))
        engine.stop()

        assert result is True, "PAPER_AUTO mode should allow advance_time_to"

    def test_feeder_advances_before_portfolio(self):
        """验证 feeder 在 portfolio 之前推进"""
        from ginkgo.trading.engines.time_controlled_engine import TimeControlledEventEngine
        from ginkgo.enums import EXECUTION_MODE

        engine = TimeControlledEventEngine(
            name="test_order",
            mode=EXECUTION_MODE.BACKTEST,
            logical_time_start=datetime(2026, 3, 30, 9, 30),
            timer_interval=0.01,
        )

        call_order = []

        mock_feeder = MagicMock()
        mock_feeder.advance_time = MagicMock(side_effect=lambda t: call_order.append("feeder"))

        mock_portfolio = MagicMock()
        mock_portfolio.advance_time = MagicMock(side_effect=lambda t: call_order.append("portfolio"))

        engine._datafeeder = mock_feeder
        engine._portfolios = [mock_portfolio]

        engine.start()
        engine.advance_time_to(datetime(2026, 3, 31, 15, 0))

        import time
        time.sleep(0.5)

        # feeder 必须在 portfolio 之前被调用
        assert len(call_order) >= 2
        feeder_idx = call_order.index("feeder")
        portfolio_idx = call_order.index("portfolio")
        assert feeder_idx < portfolio_idx, (
            f"Expected feeder before portfolio, got order: {call_order}"
        )

        engine.stop()
