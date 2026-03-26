"""Integration test for multi-data-feeder support

This test demonstrates that the multi-feeder support is backward compatible
and works correctly with the existing engine infrastructure.
"""
import pytest
from unittest.mock import MagicMock, Mock
from ginkgo.trading.engines.time_controlled_engine import TimeControlledEventEngine
from ginkgo.enums import EXECUTION_MODE, SOURCE_TYPES


class TestMultiFeederIntegration:
    """Integration tests for multi-feeder functionality"""

    def test_backward_compat_set_data_feeder(self):
        """Verify set_data_feeder still works for existing code"""
        engine = TimeControlledEventEngine(name="BackwardCompat", mode=EXECUTION_MODE.BACKTEST)

        # Create a mock feeder
        feeder = MagicMock()
        feeder.name = "LegacyFeeder"

        # Use the old API
        engine.set_data_feeder(feeder)

        # Verify it works
        assert engine._datafeeder == feeder
        assert len(engine._data_feeders) == 1
        assert engine._data_feeders[0] == feeder

    def test_new_api_add_multiple_feeders(self):
        """Verify add_data_feeder supports multiple feeders"""
        engine = TimeControlledEventEngine(name="MultiFeeder", mode=EXECUTION_MODE.BACKTEST)

        # Create multiple mock feeders
        feeder1 = MagicMock()
        feeder1.name = "Feeder1"
        feeder2 = MagicMock()
        feeder2.name = "Feeder2"
        feeder3 = MagicMock()
        feeder3.name = "Feeder3"

        # Add them using the new API
        engine.add_data_feeder(feeder1)
        engine.add_data_feeder(feeder2)
        engine.add_data_feeder(feeder3)

        # Verify all are stored
        assert len(engine._data_feeders) == 3
        assert engine._data_feeders == [feeder1, feeder2, feeder3]

        # Verify backward compat: last feeder is the main one
        assert engine._datafeeder == feeder3

    def test_feeder_propagation_to_multiple_portfolios(self):
        """Verify feeders are propagated to all portfolios"""
        engine = TimeControlledEventEngine(name="MultiPortfolio", mode=EXECUTION_MODE.BACKTEST)

        # Create multiple portfolios
        portfolio1 = MagicMock()
        portfolio1.name = "Portfolio1"
        portfolio1.bind_data_feeder = MagicMock()

        portfolio2 = MagicMock()
        portfolio2.name = "Portfolio2"
        portfolio2.bind_data_feeder = MagicMock()

        engine.add_portfolio(portfolio1)
        engine.add_portfolio(portfolio2)

        # Add a feeder
        feeder = MagicMock()
        feeder.name = "SharedFeeder"
        engine.add_data_feeder(feeder)

        # Verify feeder propagated to both portfolios
        portfolio1.bind_data_feeder.assert_called_once_with(feeder)
        portfolio2.bind_data_feeder.assert_called_once_with(feeder)

    def test_set_data_feeder_clears_previous_feeders(self):
        """Verify set_data_feeder clears existing feeders"""
        engine = TimeControlledEventEngine(name="ClearFeeder", mode=EXECUTION_MODE.BACKTEST)

        # Add multiple feeders
        feeder1 = MagicMock()
        feeder1.name = "Feeder1"
        feeder2 = MagicMock()
        feeder2.name = "Feeder2"

        engine.add_data_feeder(feeder1)
        engine.add_data_feeder(feeder2)
        assert len(engine._data_feeders) == 2

        # Use set_data_feeder should clear and add only the new one
        feeder3 = MagicMock()
        feeder3.name = "Feeder3"
        engine.set_data_feeder(feeder3)

        assert len(engine._data_feeders) == 1
        assert engine._data_feeders[0] == feeder3
