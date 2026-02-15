"""
BaseSizer tests using pytest framework.
Tests cover base sizer initialization, data feeder binding, and position sizing.
"""

import pytest
from datetime import datetime, timedelta
from unittest.mock import Mock, patch, MagicMock
from decimal import Decimal

from ginkgo.trading.sizers import BaseSizer
from ginkgo.trading.sizers import FixedSizer
from ginkgo.trading.entities import Signal
from ginkgo.trading.entities import Order
from ginkgo.trading.feeders.base_feeder import BaseFeeder
from ginkgo.enums import DIRECTION_TYPES, ORDER_TYPES, ORDERSTATUS_TYPES


# ========== Fixtures ==========

@pytest.fixture
def base_sizer():
    """Create a BaseSizer instance for testing."""
    sizer = BaseSizer("test_sizer")
    test_time = datetime(2024, 1, 1, 10, 0, 0)
    sizer.on_time_goes_by(test_time)
    return sizer


@pytest.fixture
def fixed_sizer():
    """Create a FixedSizer instance for testing."""
    return FixedSizer()


@pytest.fixture
def test_time():
    """Create a test datetime."""
    return datetime(2024, 1, 1, 10, 0, 0)


# ========== Construction Tests ==========

class TestBaseSizerConstruction:
    """Test BaseSizer construction and initialization."""

    def test_base_sizer_init(self):
        """Test base sizer initialization."""
        sizer = BaseSizer("test_sizer")
        assert sizer is not None
        assert sizer._name == "test_sizer"
        assert sizer._data_feeder is None

    def test_default_initialization(self):
        """Test default initialization."""
        sizer = BaseSizer()
        assert sizer._name == "BaseSizer"
        assert sizer._data_feeder is None

    def test_name_property(self, base_sizer):
        """Test name property."""
        assert base_sizer.name == "test_sizer"

    def test_inheritance_from_backtest_base(self, base_sizer):
        """Test inheritance from BacktestBase."""
        from ginkgo.trading.core.backtest_base import BacktestBase

        assert isinstance(base_sizer, BacktestBase)

        # Verify inherited attributes and methods
        assert hasattr(base_sizer, "on_time_goes_by")
        assert hasattr(base_sizer, "now")
        assert hasattr(base_sizer, "_name")
        assert hasattr(base_sizer, "log")


# ========== Data Feeder Binding Tests ==========

class TestDataFeederBinding:
    """Test data feeder binding functionality."""

    def test_bind_data_feeder(self, base_sizer):
        """Test data feeder binding."""
        mock_feeder = Mock(spec=BaseFeeder)

        # Initial state should have no data feeder
        assert base_sizer._data_feeder is None

        # Bind data feeder
        base_sizer.bind_data_feeder(mock_feeder)

        # Verify binding successful
        assert base_sizer._data_feeder == mock_feeder

    def test_bind_data_feeder_with_args_kwargs(self, base_sizer):
        """Test data feeder binding with args and kwargs."""
        mock_feeder = Mock()
        test_args = ("arg1", "arg2")
        test_kwargs = {"param1": "value1", "param2": "value2"}

        base_sizer.bind_data_feeder(mock_feeder, *test_args, **test_kwargs)

        # Verify binding successful
        assert base_sizer._data_feeder == mock_feeder


# ========== Cal Method Tests ==========

class TestCalMethod:
    """Test cal method functionality."""

    def test_cal_method_not_implemented(self, base_sizer):
        """Test abstract cal method raises error."""
        mock_portfolio_info = {"cash": 10000, "positions": {}}
        mock_signal = Mock(spec=Signal)

        # BaseSizer.cal should raise exception
        with pytest.raises(Exception):
            base_sizer.cal(mock_portfolio_info, mock_signal)


# ========== Time Management Tests ==========

class TestTimeManagement:
    """Test time management functionality."""

    def test_time_management(self, base_sizer):
        """Test time management (inherited from BacktestBase)."""
        test_time = datetime(2024, 2, 1, 15, 30, 0)
        base_sizer.on_time_goes_by(test_time)
        assert base_sizer.now == test_time

    @pytest.mark.parametrize("days_offset", [0, 1, 7, 30, 365])
    def test_time_with_different_offsets(self, base_sizer, days_offset):
        """Test time setting with different offsets."""
        base_time = datetime(2024, 1, 1)
        test_time = base_time + timedelta(days=days_offset)

        base_sizer.on_time_goes_by(test_time)
        assert base_sizer.now == test_time


# ========== Logging Tests ==========

class TestLogging:
    """Test logging functionality."""

    def test_logging_functionality(self, base_sizer):
        """Test logging functionality (inherited from BacktestBase)."""
        with patch.object(base_sizer, 'log') as mock_log:
            base_sizer.log("INFO", "Test message")

            # Verify log method was called
            mock_log.assert_called_once_with("INFO", "Test message")


# ========== FixedSizer Tests ==========

class TestFixedSizer:
    """Test FixedSizer concrete implementation."""

    def test_fixed_sizer_init(self):
        """Test FixedSizer initialization."""
        sizer = FixedSizer()
        assert sizer is not None
        assert isinstance(sizer, BaseSizer)

    @pytest.mark.parametrize("cash,volume,expected_volume", [
        (10000, 100, 100),
        (50000, 500, 500),
        (100000, 1000, 1000),
    ])
    def test_fixed_sizer_cal(self, cash, volume, expected_volume):
        """Test FixedSizer cal method."""
        sizer = FixedSizer(volume=volume)

        mock_portfolio_info = {"cash": cash, "positions": {}}
        mock_signal = Mock(spec=Signal)

        result = sizer.cal(mock_portfolio_info, mock_signal)

        # FixedSizer should return an order with fixed volume
        assert result is not None
        assert result.volume == expected_volume


# ========== Polymorphism Tests ==========

class TestSizerPolymorphism:
    """Test sizer polymorphism."""

    def test_custom_sizer_implementation(self):
        """Test custom sizer implementation."""
        # Create custom sizer
        class CustomSizer(BaseSizer):
            def cal(self, portfolio_info, signal, *args, **kwargs):
                # Custom sizing logic
                cash = portfolio_info.get("cash", 0)
                target_volume = int(cash / 100)  # Use 1% of cash

                order = Order()
                order.set(
                    code=signal.code if hasattr(signal, 'code') else "TEST001",
                    direction=DIRECTION_TYPES.LONG,
                    volume=target_volume,
                )
                return order

        custom_sizer = CustomSizer("custom_test")

        mock_portfolio_info = {"cash": 50000, "positions": {}}
        mock_signal = Mock(spec=Signal)
        mock_signal.code = "TEST001"

        result = custom_sizer.cal(mock_portfolio_info, mock_signal)

        # Verify custom sizer logic
        assert result is not None
        assert result.volume == 500  # 50000 / 100


# ========== Engine ID Tests ==========

class TestEngineIdAccess:
    """Test engine_id access."""

    def test_engine_id_access(self, base_sizer):
        """Test engine_id access (inherited from BacktestBase)."""
        # engine_id should be accessible and settable
        assert hasattr(base_sizer, "engine_id")

        test_id = "test_engine_123"
        base_sizer.engine_id = test_id
        assert base_sizer.engine_id == test_id


# ========== Representation Tests ==========

class TestRepresentation:
    """Test string representation."""

    def test_sizer_repr_method(self, base_sizer):
        """Test sizer string representation."""
        repr_str = repr(base_sizer)
        assert isinstance(repr_str, str)
        assert "test_sizer" in repr_str
