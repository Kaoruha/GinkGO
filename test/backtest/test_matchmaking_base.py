"""
MatchMakingBase tests using pytest framework.
Tests cover matchmaking functionality, fee calculation, and order book management.
"""

import pytest
from decimal import Decimal
import pandas as pd

from ginkgo.trading.gateway.base_matchmaking import MatchMakingBase


# ========== Fixtures ==========

@pytest.fixture
def matchmaker():
    """Create a MatchMakingBase instance for testing."""
    return MatchMakingBase()


@pytest.fixture
def dummy_event():
    """Create a dummy event for testing."""
    class DummyEvent:
        def __init__(self, name="dummy"):
            self.name = name
    return DummyEvent


# ========== Construction Tests ==========

class TestMatchMakingConstruction:
    """Test MatchMakingBase construction and initialization."""

    def test_initial_state(self, matchmaker):
        """Test initial state properties."""
        assert matchmaker.name == "HaloMatchmaking"
        assert isinstance(matchmaker.price_cache, pd.DataFrame)
        assert matchmaker.order_book == {}
        assert matchmaker.commission_rate == Decimal("0.0003")
        assert matchmaker.commission_min == 5


# ========== Fee Calculation Tests ==========

class TestFeeCalculation:
    """Test fee calculation functionality."""

    def test_cal_fee_long(self, matchmaker):
        """Test fee calculation for long position."""
        fee = matchmaker.cal_fee(100000, is_long=True)
        # Manual calculation: transfer: 1, collection: 6.87, commission: 30 > 5 -> total = 37.87
        expected = Decimal("1") + Decimal("6.87") + Decimal("30")  # no stamp tax
        assert fee == round(expected, 2)

    def test_cal_fee_short(self, matchmaker):
        """Test fee calculation for short position."""
        fee = matchmaker.cal_fee(100000, is_long=False)
        # stamp: 100, transfer: 1, collection: 6.87, commission: 30 -> total = 137.87
        expected = Decimal("100") + Decimal("1") + Decimal("6.87") + Decimal("30")
        assert fee == round(expected, 2)

    def test_cal_fee_minimum_commission(self, matchmaker):
        """Test fee calculation with minimum commission."""
        # Transaction too small, commission < min
        fee = matchmaker.cal_fee(1000, is_long=True)
        # commission = 0.3 < 5 -> use 5
        # stamp: 0, transfer: 0.01, collection: 0.0687, commission: 5 -> 5.08
        expected = Decimal("0.01") + Decimal("0.0687") + Decimal("5")
        assert fee == round(expected, 2)

    def test_cal_fee_invalid(self, matchmaker):
        """Test fee calculation with invalid amount."""
        fee = matchmaker.cal_fee(-100, is_long=True)
        assert fee == 0

    @pytest.mark.parametrize("amount,is_long,expected_range", [
        (10000, True, (5, 10)),       # Small long position
        (100000, True, (35, 40)),      # Medium long position
        (1000000, True, (300, 400)),    # Large long position
        (10000, False, (5, 110)),      # Small short position (with stamp)
        (100000, False, (130, 145)),    # Medium short position
    ])
    def test_cal_fee_various_amounts(self, matchmaker, amount, is_long, expected_range):
        """Test fee calculation for various amounts."""
        fee = matchmaker.cal_fee(amount, is_long=is_long)
        assert expected_range[0] <= fee <= expected_range[1]


# ========== Event Handling Tests ==========

class TestEventHandling:
    """Test event handling functionality."""

    def test_put_event_without_engine(self, matchmaker, dummy_event):
        """Test putting event without bound engine."""
        mm = MatchMakingBase()
        mm._engine_put = None
        # Just make sure it doesn't crash
        mm.put(dummy_event())


# ========== Time Management Tests ==========

class TestTimeManagement:
    """Test time management functionality."""

    def test_on_time_goes_by(self, matchmaker):
        """Test on_time_goes_by clears caches."""
        matchmaker._price_cache = pd.DataFrame({"a": [1, 2, 3]})
        matchmaker._order_book = {"AAPL": ["order1", "order2"]}
        matchmaker.on_time_goes_by("2023-01-01")
        assert matchmaker.price_cache.empty
        assert matchmaker.order_book == {}


# ========== Order Book Tests ==========

class TestOrderBook:
    """Test order book management."""

    def test_order_book_initial_state(self, matchmaker):
        """Test order book initial state."""
        assert matchmaker.order_book == {}

    def test_order_book_after_time_update(self, matchmaker):
        """Test order book cleared after time update."""
        # Add some orders to order book
        matchmaker._order_book = {"TEST": ["order1"]}
        # Update time should clear
        matchmaker.on_time_goes_by("2023-01-01")
        assert matchmaker.order_book == {}


# ========== Price Cache Tests ==========

class TestPriceCache:
    """Test price cache management."""

    def test_price_cache_initial_state(self, matchmaker):
        """Test price cache initial state."""
        assert isinstance(matchmaker.price_cache, pd.DataFrame)
        assert matchmaker.price_cache.empty

    def test_price_cache_after_time_update(self, matchmaker):
        """Test price cache cleared after time update."""
        # Add some data to cache
        matchmaker._price_cache = pd.DataFrame({"price": [100, 101, 102]})
        # Update time should clear
        matchmaker.on_time_goes_by("2023-01-01")
        assert matchmaker.price_cache.empty


# ========== Commission Settings Tests ==========

class TestCommissionSettings:
    """Test commission rate and minimum settings."""

    def test_commission_rate_default(self, matchmaker):
        """Test default commission rate."""
        assert matchmaker.commission_rate == Decimal("0.0003")

    def test_commission_min_default(self, matchmaker):
        """Test default minimum commission."""
        assert matchmaker.commission_min == 5

    def test_commission_calculation_uses_minimum(self, matchmaker):
        """Test commission calculation uses minimum when needed."""
        # Small transaction where commission would be below minimum
        fee = matchmaker.cal_fee(1000, is_long=True)
        # Commission should be 5 (minimum), not 0.3 (0.3% of 1000)
        assert fee >= 5  # Should include minimum commission


# ========== Name Tests ==========

class TestName:
    """Test name property."""

    def test_matchmaker_name(self, matchmaker):
        """Test matchmaker name."""
        assert matchmaker.name == "HaloMatchmaking"
