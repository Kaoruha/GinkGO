"""
性能: 219MB RSS, 1.93s, 21 tests [PASS]
BaseSizer tests using pytest framework.
Tests cover base sizer initialization, data feeder binding, and position sizing.
"""

import pytest
from datetime import datetime, timedelta
from unittest.mock import Mock, patch, MagicMock
from decimal import Decimal

from ginkgo.trading.sizers import BaseSizer
from ginkgo.trading.sizers import FixedSizer
from ginkgo.entities import Signal
from ginkgo.entities import Order
from ginkgo.trading.feeders.base_feeder import BaseFeeder
from ginkgo.enums import DIRECTION_TYPES, ORDER_TYPES, ORDERSTATUS_TYPES


# ========== Fixtures ==========

@pytest.fixture
def base_sizer():
    """Create a BaseSizer instance for testing."""
    sizer = BaseSizer("test_sizer")
    test_time = datetime(2024, 1, 1, 10, 0, 0)
    # Use a mutable mock that tracks time changes
    current = [test_time]
    mock_tp = Mock()
    mock_tp.now = Mock(side_effect=lambda: current[0])
    mock_tp.set_current_time = Mock(side_effect=lambda t: current.__setitem__(0, t) or True)
    sizer.set_time_provider(mock_tp)
    sizer.advance_time(test_time)
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
        assert sizer.name == "test_sizer"
        assert sizer._data_feeder is None

    def test_default_initialization(self):
        """Test default initialization."""
        sizer = BaseSizer()
        assert sizer.name == "sizer"
        assert sizer._data_feeder is None

    def test_name_property(self, base_sizer):
        """Test name property."""
        assert base_sizer.name == "test_sizer"

    def test_inheritance_from_base(self, base_sizer):
        """Test inheritance from Base."""
        from ginkgo.entities.base import Base

        assert isinstance(base_sizer, Base)

        # Verify inherited attributes and methods
        assert hasattr(base_sizer, "advance_time")
        assert hasattr(base_sizer, "get_current_time")
        assert hasattr(base_sizer, "_name")
        assert hasattr(base_sizer, "uuid")


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

    def test_cal_method_returns_none(self, base_sizer):
        """Test base cal method returns None (not implemented)."""
        mock_portfolio_info = {"cash": 10000, "positions": {}}
        mock_signal = Mock(spec=Signal)

        # BaseSizer.cal returns None
        result = base_sizer.cal(mock_portfolio_info, mock_signal)
        assert result is None


# ========== Time Management Tests ==========

class TestTimeManagement:
    """Test time management functionality."""

    def test_time_management(self, base_sizer):
        """Test time management (inherited from TimeMixin)."""
        test_time = datetime(2024, 2, 1, 15, 30, 0)
        base_sizer.advance_time(test_time)
        assert base_sizer.current_timestamp == test_time

    @pytest.mark.parametrize("days_offset", [0, 1, 7, 30, 365])
    def test_time_with_different_offsets(self, base_sizer, days_offset):
        """Test time setting with different offsets."""
        base_time = datetime(2024, 1, 1)
        test_time = base_time + timedelta(days=days_offset)

        base_sizer.advance_time(test_time)
        assert base_sizer.current_timestamp == test_time


# ========== Logging Tests ==========

class TestLogging:
    """Test logging functionality."""

    def test_logging_functionality(self, base_sizer):
        """Test GLOG is available for logging."""
        from ginkgo.libs import GLOG
        # GLOG module is available for use by components
        assert hasattr(GLOG, 'INFO')
        assert callable(GLOG.INFO)


# ========== FixedSizer Tests ==========

class TestFixedSizer:
    """Test FixedSizer concrete implementation."""

    def test_fixed_sizer_init(self):
        """Test FixedSizer initialization."""
        sizer = FixedSizer()
        assert sizer is not None
        assert isinstance(sizer, BaseSizer)

    def test_fixed_sizer_volume_property(self):
        """Test FixedSizer volume property."""
        sizer = FixedSizer(volume="500")
        assert sizer.volume == 500

        sizer2 = FixedSizer(volume=1000)
        assert sizer2.volume == 1000

    def test_fixed_sizer_cal_returns_none_for_invalid_signal(self):
        """Test FixedSizer cal returns None for invalid signal."""
        sizer = FixedSizer(volume="100")

        mock_portfolio_info = {"cash": 10000, "positions": {}}
        mock_signal = Mock(spec=Signal)
        mock_signal.is_valid.return_value = False

        result = sizer.cal(mock_portfolio_info, mock_signal)
        assert result is None

    def test_fixed_sizer_cal_returns_none_for_none_signal(self):
        """Test FixedSizer cal returns None for None signal."""
        sizer = FixedSizer(volume="100")

        mock_portfolio_info = {"cash": 10000, "positions": {}}

        result = sizer.cal(mock_portfolio_info, None)
        assert result is None


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

                code = signal.code if hasattr(signal, 'code') else "TEST001"
                order = Order(
                    portfolio_id="test_portfolio",
                    engine_id="test_engine",
                    run_id="test_run",
                    code=code,
                    direction=DIRECTION_TYPES.LONG,
                    order_type=ORDER_TYPES.MARKETORDER,
                    status=ORDERSTATUS_TYPES.NEW,
                    volume=target_volume,
                    limit_price=0,
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
        """Test engine_id access (inherited from ContextMixin)."""
        # engine_id should be accessible as a property
        assert hasattr(base_sizer, "engine_id")
        # Without a bound engine, engine_id is None
        assert base_sizer.engine_id is None


# ========== Representation Tests ==========

class TestRepresentation:
    """Test string representation."""

    def test_sizer_repr_method(self, base_sizer):
        """Test sizer string representation."""
        repr_str = repr(base_sizer)
        assert isinstance(repr_str, str)
