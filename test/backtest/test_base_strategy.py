"""
BaseStrategy tests using pytest framework.
Tests cover strategy initialization, data feeder binding, signal generation,
and strategy polymorphism.
"""

import pytest
import pandas as pd
from datetime import datetime
from unittest.mock import Mock

from ginkgo.trading.strategies.base_strategy import BaseStrategy
from ginkgo.trading.entities import Signal
from ginkgo.enums import DIRECTION_TYPES, SOURCE_TYPES


# ========== Fixtures ==========

@pytest.fixture
def base_strategy():
    """Create a StrategyBase instance for testing."""
    strategy = BaseStrategy("test_strategy")
    test_time = datetime(2024, 1, 1, 10, 0, 0)
    strategy.on_time_goes_by(test_time)
    return strategy


@pytest.fixture
def portfolio_info():
    """Create a portfolio_info dict for testing."""
    return {"cash": 100000, "positions": {}, "net_value": 100000}


@pytest.fixture
def mock_event():
    """Create a mock event for testing."""
    return Mock()


@pytest.fixture
def test_time():
    """Create a test datetime."""
    return datetime(2024, 1, 1, 10, 0, 0)


# ========== Construction Tests ==========

class TestStrategyConstruction:
    """Test StrategyBase construction and initialization."""

    def test_strategy_init(self):
        """Test base strategy initialization."""
        strategy = BaseStrategy("test_strategy")
        assert strategy is not None
        assert strategy._name == "test_strategy"
        assert strategy._raw == {}
        assert strategy._data_feeder is None

    def test_name_property(self, base_strategy):
        """Test name property."""
        assert base_strategy.name == "test_strategy"

    def test_inheritance_from_backtest_base(self, base_strategy):
        """Test inheritance from BacktestBase."""
        from ginkgo.trading.core.backtest_base import BacktestBase

        assert isinstance(base_strategy, BacktestBase)

        # Verify inherited attributes and methods
        assert hasattr(base_strategy, "on_time_goes_by")
        assert hasattr(base_strategy, "now")
        assert hasattr(base_strategy, "_name")


# ========== Data Feeder Binding Tests ==========

class TestDataFeederBinding:
    """Test data feeder binding functionality."""

    def test_bind_data_feeder(self, base_strategy):
        """Test binding data feeder."""
        mock_feeder = Mock()
        base_strategy.bind_data_feeder(mock_feeder)

        # Verify data feeder bound
        assert base_strategy._data_feeder == mock_feeder
        assert base_strategy.data_feeder == mock_feeder

    def test_data_feeder_property(self, base_strategy):
        """Test data_feeder property."""
        # Initial state should be None
        assert base_strategy.data_feeder is None

        # After binding, should return bound data feeder
        mock_feeder = Mock()
        base_strategy.bind_data_feeder(mock_feeder)
        assert base_strategy.data_feeder == mock_feeder


# ========== Cal Method Tests ==========

class TestCalMethod:
    """Test cal method functionality."""

    def test_cal_method_interface(self, base_strategy, portfolio_info, mock_event):
        """Test cal method interface."""
        # cal method should exist
        assert hasattr(base_strategy, "cal")
        assert callable(base_strategy.cal)

        # Calling cal method should return signal list
        result = base_strategy.cal(portfolio_info, mock_event)
        assert isinstance(result, list)
        # For base strategy, should return empty list
        assert result == []

    def test_cal_method_with_different_inputs(self, base_strategy, mock_event):
        """Test cal method with different inputs."""
        # Test normal input
        portfolio_info = {"cash": 100000, "positions": {}, "net_value": 100000}
        result = base_strategy.cal(portfolio_info, mock_event)
        assert isinstance(result, list)

        # Test empty portfolio_info
        result = base_strategy.cal({}, mock_event)
        assert isinstance(result, list)

        # Test None input
        result = base_strategy.cal(None, mock_event)
        assert isinstance(result, list)

        result = base_strategy.cal(portfolio_info, None)
        assert isinstance(result, list)


# ========== Raw Data Tests ==========

class TestRawData:
    """Test _raw data attribute."""

    def test_raw_data_attribute(self, base_strategy):
        """Test _raw attribute."""
        # Initial state should be empty dict
        assert base_strategy._raw == {}
        assert isinstance(base_strategy._raw, dict)

        # Can modify _raw attribute
        base_strategy._raw["test_key"] = "test_value"
        assert base_strategy._raw["test_key"] == "test_value"


# ========== Time Management Tests ==========

class TestTimeManagement:
    """Test time management functionality."""

    def test_time_management(self, base_strategy):
        """Test time management (inherited from BacktestBase)."""
        test_time = datetime(2024, 2, 1, 15, 30, 0)
        base_strategy.on_time_goes_by(test_time)
        assert base_strategy.now == test_time


# ========== Polymorphism Tests ==========

class TestStrategyPolymorphism:
    """Test strategy polymorphism."""

    def test_strategy_polymorphism(self, portfolio_info, mock_event):
        """Test strategy polymorphism."""
        # Create custom strategy class
        class CustomStrategy(BaseStrategy):
            def cal(self, portfolio_info, event, *args, **kwargs):
                return [Signal(
                    portfolio_id="test_portfolio",
                    engine_id="test_engine",
                    timestamp=datetime(2024, 1, 1),
                    code="TEST001",
                    direction=DIRECTION_TYPES.LONG,
                    reason="test_signal",
                    source=SOURCE_TYPES.OTHER
                )]

        custom_strategy = CustomStrategy("custom_test")
        result = custom_strategy.cal(portfolio_info, mock_event)

        # Verify custom strategy cal method called correctly
        assert isinstance(result, list)
        assert len(result) == 1
        assert isinstance(result[0], Signal)
        assert result[0].code == "TEST001"
        assert result[0].direction == DIRECTION_TYPES.LONG

    @pytest.mark.parametrize("direction,reason", [
        (DIRECTION_TYPES.LONG, "Buy signal"),
        (DIRECTION_TYPES.SHORT, "Sell signal"),
        (DIRECTION_TYPES.OTHER, "Close signal"),
    ])
    def test_strategy_with_different_directions(self, direction, reason):
        """Test strategy generating different signal directions."""
        class DirectionStrategy(BaseStrategy):
            def cal(self, portfolio_info, event, *args, **kwargs):
                return [Signal(
                    portfolio_id="test_portfolio",
                    engine_id="test_engine",
                    timestamp=datetime(2024, 1, 1),
                    code="TEST001",
                    direction=direction,
                    reason=reason,
                    source=SOURCE_TYPES.STRATEGY
                )]

        strategy = DirectionStrategy("direction_test")
        result = strategy.cal({}, Mock())

        assert len(result) == 1
        assert result[0].direction == direction
        assert result[0].reason == reason


# ========== Engine ID Tests ==========

class TestEngineIdAccess:
    """Test engine_id access."""

    def test_engine_id_access(self, base_strategy):
        """Test engine_id access (inherited from BacktestBase)."""
        # engine_id should be accessible and settable
        assert hasattr(base_strategy, "engine_id")

        test_id = "test_engine_123"
        base_strategy.engine_id = test_id
        assert base_strategy.engine_id == test_id


# ========== Representation Tests ==========

class TestRepresentation:
    """Test string representation."""

    def test_strategy_repr_method(self, base_strategy):
        """Test strategy string representation."""
        repr_str = repr(base_strategy)
        assert isinstance(repr_str, str)
        assert "test_strategy" in repr_str


# ========== Multiple Signals Tests ==========

class TestMultipleSignals:
    """Test strategy generating multiple signals."""

    def test_multiple_signals_generation(self, portfolio_info, mock_event):
        """Test strategy can generate multiple signals."""
        class MultiSignalStrategy(BaseStrategy):
            def cal(self, portfolio_info, event, *args, **kwargs):
                return [
                    Signal(
                        portfolio_id="test_portfolio",
                        engine_id="test_engine",
                        timestamp=datetime(2024, 1, 1),
                        code="TEST001",
                        direction=DIRECTION_TYPES.LONG,
                        reason="Buy signal",
                        source=SOURCE_TYPES.STRATEGY
                    ),
                    Signal(
                        portfolio_id="test_portfolio",
                        engine_id="test_engine",
                        timestamp=datetime(2024, 1, 1),
                        code="TEST002",
                        direction=DIRECTION_TYPES.SHORT,
                        reason="Sell signal",
                        source=SOURCE_TYPES.STRATEGY
                    ),
                ]

        strategy = MultiSignalStrategy("multi_test")
        result = strategy.cal(portfolio_info, mock_event)

        assert len(result) == 2
        assert result[0].code == "TEST001"
        assert result[1].code == "TEST002"
