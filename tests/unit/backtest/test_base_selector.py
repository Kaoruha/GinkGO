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
    # Use a mutable mock that tracks time changes
    current = [test_time]
    mock_tp = Mock()
    mock_tp.now = Mock(side_effect=lambda: current[0])
    mock_tp.set_current_time = Mock(side_effect=lambda t: current.__setitem__(0, t) or True)
    selector.set_time_provider(mock_tp)
    selector.advance_time(test_time)
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
        assert selector.name == "selector"
        assert selector._data_feeder is None

    def test_name_property(self, base_selector):
        """Test name property."""
        assert base_selector.name == "test_selector"

    def test_inheritance_from_base(self, base_selector):
        """Test inheritance from Base."""
        from ginkgo.entities.base import Base

        assert isinstance(base_selector, Base)

        # Verify inherited attributes and methods
        assert hasattr(base_selector, "advance_time")
        assert hasattr(base_selector, "get_current_time")
        assert hasattr(base_selector, "_name")
        assert hasattr(base_selector, "uuid")


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

        # Non-JSON string is treated as comma-separated; single token becomes one code
        result = selector.pick()
        assert result == ["invalid json string"]

    def test_fixed_selector_with_logging(self):
        """Test FixedSelector logging."""
        codes = '["TEST001", "TEST002"]'
        selector = FixedSelector("logging_test", codes)

        with patch('ginkgo.libs.GLOG.DEBUG') as mock_debug:
            result = selector.pick()

            # Verify log was called
            mock_debug.assert_called_once()
            call_arg = mock_debug.call_args[0][0]
            assert "pick" in call_arg


# ========== Time Management Tests ==========

class TestTimeManagement:
    """Test time management functionality."""

    def test_time_management(self, base_selector):
        """Test time management (inherited from TimeMixin)."""
        test_time = datetime(2024, 2, 1, 15, 30, 0)
        base_selector.advance_time(test_time)
        assert base_selector.current_timestamp == test_time

    @pytest.mark.parametrize("days_offset", [0, 1, 7, 30, 365])
    def test_time_independence(self, base_selector, days_offset):
        """Test time setting with different offsets."""
        base_time = datetime(2024, 1, 1)
        test_time = base_time + timedelta(days=days_offset)

        base_selector.advance_time(test_time)
        assert base_selector.current_timestamp == test_time


# ========== Logging Tests ==========

class TestLogging:
    """Test logging functionality."""

    def test_logging_functionality(self, base_selector):
        """Test GLOG is available for logging."""
        from ginkgo.libs import GLOG
        # GLOG module is available for use by components
        assert hasattr(GLOG, 'INFO')
        assert callable(GLOG.INFO)


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
        time1 = datetime(2024, 1, 1, 10, 0, 0)
        time2 = datetime(2024, 1, 2, 15, 30, 0)

        selector1 = BaseSelector("selector1")
        cur1 = [time1]
        mock_tp1 = Mock()
        mock_tp1.now = Mock(side_effect=lambda: cur1[0])
        mock_tp1.set_current_time = Mock(side_effect=lambda t: cur1.__setitem__(0, t) or True)
        selector1.set_time_provider(mock_tp1)
        selector1.advance_time(time1)

        selector2 = BaseSelector("selector2")
        cur2 = [time2]
        mock_tp2 = Mock()
        mock_tp2.now = Mock(side_effect=lambda: cur2[0])
        mock_tp2.set_current_time = Mock(side_effect=lambda t: cur2.__setitem__(0, t) or True)
        selector2.set_time_provider(mock_tp2)
        selector2.advance_time(time2)

        # Verify time independence
        assert selector1.current_timestamp == time1
        assert selector2.current_timestamp == time2


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
        current = [start_time]
        mock_tp = Mock()
        mock_tp.now = Mock(side_effect=lambda: current[0])
        mock_tp.set_current_time = Mock(side_effect=lambda t: current.__setitem__(0, t) or True)
        selector.set_time_provider(mock_tp)

        # Test large time span
        for i in range(1000):
            test_time = start_time + timedelta(days=i)
            selector.advance_time(test_time)
            result = selector.pick(time=test_time)

            # Each call should return empty list
            assert isinstance(result, list)
            assert len(result) == 0

        # Verify final time set correctly
        expected_final_time = start_time + timedelta(days=999)
        assert selector.current_timestamp == expected_final_time


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


# ========== Engine ID Tests ==========

class TestEngineIdAccess:
    """Test engine_id access."""

    def test_engine_id_access(self, base_selector):
        """Test engine_id access (inherited from ContextMixin)."""
        # engine_id should be accessible as a property
        assert hasattr(base_selector, "engine_id")
        # Without a bound engine, engine_id is None
        assert base_selector.engine_id is None
