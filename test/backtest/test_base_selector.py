"""
BaseSelector tests using pytest framework.
Tests cover selector initialization, data feeder binding, pick functionality,
and concrete implementations like FixedSelector.
"""

import pytest
from datetime import datetime, timedelta
from unittest.mock import Mock, patch

from ginkgo.trading.selectors import BaseSelector
from ginkgo.trading.selectors import FixedSelector
from ginkgo.trading.feeders.base_feeder import BaseFeeder


# ========== Fixtures ==========

@pytest.fixture
def base_selector():
    """Create a BaseSelector instance for testing."""
    selector = BaseSelector("test_selector")
    test_time = datetime(2024, 1, 1, 10, 0, 0)
    selector.on_time_goes_by(test_time)
    return selector


@pytest.fixture
def test_time():
    """Create a test datetime."""
    return datetime(2024, 1, 1, 10, 0, 0)


@pytest.fixture
def fixed_selector():
    """Create a FixedSelector with valid codes."""
    codes = '["000001.SZ", "000002.SZ", "600000.SH"]'
    return FixedSelector("fixed_test", codes)


# ========== Construction Tests ==========

class TestBaseSelectorConstruction:
    """Test BaseSelector construction and initialization."""

    def test_base_selector_init(self):
        """Test base selector initialization."""
        selector = BaseSelector("test_selector")
        assert selector is not None

    def test_default_initialization(self):
        """Test default initialization."""
        selector = BaseSelector()
        assert selector._name == "BaseSelector"
        assert selector._data_feeder is None

    def test_name_property(self, base_selector):
        """Test name property."""
        assert base_selector.name == "test_selector"

    def test_inheritance_from_backtest_base(self, base_selector):
        """Test inheritance from BacktestBase."""
        from ginkgo.trading.core.backtest_base import BacktestBase

        assert isinstance(base_selector, BacktestBase)

        # Verify inherited attributes and methods
        assert hasattr(base_selector, "on_time_goes_by")
        assert hasattr(base_selector, "now")
        assert hasattr(base_selector, "_name")
        assert hasattr(base_selector, "log")


# ========== Data Feeder Binding Tests ==========

class TestDataFeederBinding:
    """Test data feeder binding functionality."""

    def test_bind_data_feeder(self, base_selector):
        """Test data feeder binding."""
        mock_feeder = Mock(spec=BaseFeeder)

        # Initial state should have no data feeder
        assert base_selector._data_feeder is None

        # Bind data feeder
        base_selector.bind_data_feeder(mock_feeder)

        # Verify binding successful
        assert base_selector._data_feeder == mock_feeder

    def test_bind_data_feeder_with_args_kwargs(self, base_selector):
        """Test data feeder binding with args and kwargs."""
        mock_feeder = Mock()
        test_args = ("arg1", "arg2")
        test_kwargs = {"param1": "value1", "param2": "value2"}

        base_selector.bind_data_feeder(mock_feeder, *test_args, **test_kwargs)

        # Verify binding successful
        assert base_selector._data_feeder == mock_feeder

    def test_data_feeder_rebinding(self, base_selector):
        """Test data feeder rebinding."""
        mock_feeder1 = Mock()
        mock_feeder2 = Mock()

        # Bind first data feeder
        base_selector.bind_data_feeder(mock_feeder1)
        assert base_selector._data_feeder == mock_feeder1

        # Rebind with second data feeder
        base_selector.bind_data_feeder(mock_feeder2)
        assert base_selector._data_feeder == mock_feeder2

    def test_data_feeder_none_binding(self, base_selector):
        """Test binding None data feeder."""
        # First bind a normal data feeder
        mock_feeder = Mock()
        base_selector.bind_data_feeder(mock_feeder)
        assert base_selector._data_feeder == mock_feeder

        # Bind None should override previous binding
        base_selector.bind_data_feeder(None)
        assert base_selector._data_feeder is None


# ========== Pick Functionality Tests ==========

class TestPickFunctionality:
    """Test pick method functionality."""

    def test_default_pick_method(self, base_selector):
        """Test default pick method."""
        # Default pick method should return empty list
        result = base_selector.pick()
        assert isinstance(result, list)
        assert len(result) == 0

    def test_pick_method_with_time_parameter(self, base_selector):
        """Test pick method with time parameter."""
        test_time = datetime(2024, 1, 1, 15, 30, 0)

        result = base_selector.pick(time=test_time)
        assert isinstance(result, list)
        assert len(result) == 0

    def test_pick_method_with_args_kwargs(self, base_selector):
        """Test pick method with args and kwargs."""
        test_args = ("arg1", "arg2")
        test_kwargs = {"param1": "value1", "param2": "value2"}

        result = base_selector.pick("time", *test_args, **test_kwargs)
        assert isinstance(result, list)
        assert len(result) == 0

    def test_pick_with_none_time(self, base_selector):
        """Test pick with None time."""
        result = base_selector.pick(time=None)
        assert isinstance(result, list)
        assert len(result) == 0


# ========== FixedSelector Tests ==========

class TestFixedSelector:
    """Test FixedSelector concrete implementation."""

    def test_concrete_selector_implementation(self):
        """Test concrete selector implementation."""
        valid_codes = '["000001.SZ", "000002.SZ", "600000.SH"]'
        selector = FixedSelector("fixed_test", valid_codes)

        assert selector is not None
        assert selector.name == "fixed_test"
        assert isinstance(selector, BaseSelector)

    def test_fixed_selector_pick_functionality(self):
        """Test FixedSelector pick functionality."""
        codes = '["000001.SZ", "000002.SZ", "600000.SH"]'
        selector = FixedSelector("fixed_test", codes)

        result = selector.pick()
        expected = ["000001.SZ", "000002.SZ", "600000.SH"]

        assert result == expected
        assert isinstance(result, list)
        assert len(result) == 3

    @pytest.mark.parametrize("codes,expected", [
        ('["000001.SZ"]', ["000001.SZ"]),
        ('["000001.SZ", "000002.SZ"]', ["000001.SZ", "000002.SZ"]),
        ('[]', []),
    ])
    def test_fixed_selector_with_different_codes(self, codes, expected):
        """Test FixedSelector with different code lists."""
        selector = FixedSelector("test", codes)
        assert selector.pick() == expected

    def test_fixed_selector_invalid_json(self):
        """Test FixedSelector with invalid JSON."""
        invalid_codes = "invalid json string"

        selector = FixedSelector("invalid_json_test", invalid_codes)

        # pick should return empty list
        result = selector.pick()
        assert result == []

    def test_fixed_selector_with_logging(self):
        """Test FixedSelector logging."""
        codes = '["TEST001", "TEST002"]'
        selector = FixedSelector("logging_test", codes)

        with patch.object(selector, 'log') as mock_log:
            result = selector.pick()

            # Verify log was called
            mock_log.assert_called_once()
            call_args = mock_log.call_args[0]
            assert call_args[0] == "DEBUG"
            assert "pick" in call_args[1]


# ========== Time Management Tests ==========

class TestTimeManagement:
    """Test time management functionality."""

    def test_time_management(self, base_selector):
        """Test time management (inherited from BacktestBase)."""
        test_time = datetime(2024, 2, 1, 15, 30, 0)
        base_selector.on_time_goes_by(test_time)
        assert base_selector.now == test_time

    @pytest.mark.parametrize("days_offset", [0, 1, 7, 30, 365])
    def test_time_independence(self, base_selector, days_offset):
        """Test time setting with different offsets."""
        base_time = datetime(2024, 1, 1)
        test_time = base_time + timedelta(days=days_offset)

        base_selector.on_time_goes_by(test_time)
        assert base_selector.now == test_time


# ========== Logging Tests ==========

class TestLogging:
    """Test logging functionality."""

    def test_logging_functionality(self, base_selector):
        """Test logging functionality (inherited from BacktestBase)."""
        with patch.object(base_selector, 'log') as mock_log:
            base_selector.log("INFO", "Test message")

            # Verify log method was called
            mock_log.assert_called_once_with("INFO", "Test message")


# ========== Independence Tests ==========

class TestIndependence:
    """Test independence of multiple selector instances."""

    def test_multiple_selectors_independence(self):
        """Test multiple selector instances independence."""
        selector1 = BaseSelector("selector1")
        selector2 = BaseSelector("selector2")

        mock_feeder1 = Mock()
        mock_feeder2 = Mock()

        # Bind different data feeders
        selector1.bind_data_feeder(mock_feeder1)
        selector2.bind_data_feeder(mock_feeder2)

        # Verify independence
        assert selector1._data_feeder == mock_feeder1
        assert selector2._data_feeder == mock_feeder2
        assert selector1._data_feeder != selector2._data_feeder

    def test_selector_time_independence(self):
        """Test selector time setting independence."""
        selector1 = BaseSelector("selector1")
        selector2 = BaseSelector("selector2")

        time1 = datetime(2024, 1, 1, 10, 0, 0)
        time2 = datetime(2024, 1, 2, 15, 30, 0)

        # Set different times
        selector1.on_time_goes_by(time1)
        selector2.on_time_goes_by(time2)

        # Verify time independence
        assert selector1.now == time1
        assert selector2.now == time2


# ========== Performance Tests ==========

class TestPerformance:
    """Test performance with large datasets."""

    def test_selector_resource_cleanup(self):
        """Test selector resource cleanup."""
        selectors = []

        # Create multiple selector instances
        for i in range(10):
            selector = BaseSelector(f"selector_{i}")
            selector.bind_data_feeder(Mock())
            selectors.append(selector)

        # Verify all selectors work
        for selector in selectors:
            assert selector._data_feeder is not None
            result = selector.pick()
            assert isinstance(result, list)

        # Clear references
        selectors.clear()

        # Original selector should still work
        base_selector = BaseSelector("original")
        assert base_selector._data_feeder is None
        result = base_selector.pick()
        assert isinstance(result, list)

    def test_selector_with_large_time_range(self):
        """Test selector stability over large time range."""
        selector = BaseSelector("range_test")
        start_time = datetime(2020, 1, 1)

        # Test large time span
        for i in range(1000):
            test_time = start_time + timedelta(days=i)
            selector.on_time_goes_by(test_time)
            result = selector.pick(time=test_time)

            # Each call should return empty list
            assert isinstance(result, list)
            assert len(result) == 0

        # Verify final time set correctly
        expected_final_time = start_time + timedelta(days=999)
        assert selector.now == expected_final_time


# ========== Abstract Behavior Tests ==========

class TestAbstractBehavior:
    """Test abstract behavior enforcement."""

    def test_abstract_behavior_enforcement(self):
        """Test abstract behavior enforcement."""
        selector = BaseSelector("abstract_test")

        # Default pick method should return empty list
        result = selector.pick()
        assert result == []

        # Subclass should override this method
        class ConcreteSelector(BaseSelector):
            def pick(self, time=None, *args, **kwargs):
                return ["OVERRIDDEN"]

        concrete = ConcreteSelector("concrete")
        result = concrete.pick()
        assert result == ["OVERRIDDEN"]


# ========== Representation Tests ==========

class TestRepresentation:
    """Test string representation."""

    def test_selector_repr_method(self, base_selector):
        """Test selector string representation."""
        repr_str = repr(base_selector)
        assert isinstance(repr_str, str)
        assert "test_selector" in repr_str


# ========== Engine ID Tests ==========

class TestEngineIdAccess:
    """Test engine_id access."""

    def test_engine_id_access(self, base_selector):
        """Test engine_id access (inherited from BacktestBase)."""
        # engine_id should be accessible and settable
        assert hasattr(base_selector, "engine_id")

        test_id = "test_engine_123"
        base_selector.engine_id = test_id
        assert base_selector.engine_id == test_id
