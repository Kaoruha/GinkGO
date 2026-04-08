"""
性能: 157MB RSS, 0.96s, 6 tests [PASS]
"""

import pytest
from unittest.mock import MagicMock
from ginkgo.trading.engines.time_controlled_engine import TimeControlledEventEngine
from ginkgo.enums import EXECUTION_MODE


class TestMultiDataFeeder:
    """Test multiple data feeder support in TimeControlledEventEngine"""

    def test_add_data_feeder_stores_multiple(self):
        """Test that multiple feeders can be added and stored"""
        engine = TimeControlledEventEngine(name="TestMulti", mode=EXECUTION_MODE.PAPER)
        feeder1 = MagicMock(name="Feeder1")
        feeder1.name = "Feeder1"
        feeder2 = MagicMock(name="Feeder2")
        feeder2.name = "Feeder2"
        engine.add_data_feeder(feeder1)
        engine.add_data_feeder(feeder2)
        assert len(engine._data_feeders) == 2
        assert engine._data_feeders[0] == feeder1
        assert engine._data_feeders[1] == feeder2

    def test_set_data_feeder_still_works(self):
        """Test that set_data_feeder still works for backward compatibility"""
        engine = TimeControlledEventEngine(name="TestSingle", mode=EXECUTION_MODE.PAPER)
        feeder = MagicMock(name="SingleFeeder")
        feeder.name = "SingleFeeder"
        engine.set_data_feeder(feeder)
        assert len(engine._data_feeders) == 1
        assert engine._data_feeders[0] == feeder

    def test_add_data_feeder_binds_engine_and_publisher(self):
        """Test that add_data_feeder binds engine and event publisher"""
        engine = TimeControlledEventEngine(name="TestBinding", mode=EXECUTION_MODE.PAPER)
        feeder = MagicMock(name="BoundFeeder")
        feeder.name = "BoundFeeder"
        engine.add_data_feeder(feeder)
        feeder.bind_engine.assert_called_once_with(engine)
        feeder.set_event_publisher.assert_called_once_with(engine.put)

    def test_add_data_feeder_propagates_to_portfolios(self):
        """Test that add_data_feeder propagates feeder to portfolios"""
        engine = TimeControlledEventEngine(name="TestProp", mode=EXECUTION_MODE.PAPER)
        feeder = MagicMock(name="PropFeeder")
        feeder.name = "PropFeeder"
        portfolio = MagicMock(name="TestPortfolio")
        portfolio.bind_data_feeder = MagicMock()
        engine.add_portfolio(portfolio)
        engine.add_data_feeder(feeder)
        portfolio.bind_data_feeder.assert_called_with(feeder)

    def test_set_data_feeder_clears_existing(self):
        """Test that set_data_feeder clears existing feeders before adding"""
        engine = TimeControlledEventEngine(name="TestClear", mode=EXECUTION_MODE.PAPER)
        feeder1 = MagicMock(name="Feeder1")
        feeder1.name = "Feeder1"
        feeder2 = MagicMock(name="Feeder2")
        feeder2.name = "Feeder2"
        engine.add_data_feeder(feeder1)
        engine.add_data_feeder(feeder2)
        assert len(engine._data_feeders) == 2
        engine.set_data_feeder(feeder1)
        assert len(engine._data_feeders) == 1
        assert engine._data_feeders[0] == feeder1

    def test_add_data_feeder_propagates_time_provider(self):
        """Test that add_data_feeder propagates _time_provider to feeder"""
        engine = TimeControlledEventEngine(name="TestTime", mode=EXECUTION_MODE.PAPER)
        feeder = MagicMock(name="TimeFeeder")
        feeder.name = "TimeFeeder"
        engine.add_data_feeder(feeder)
        feeder.set_time_provider.assert_called_once_with(engine._time_provider)
