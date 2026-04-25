"""Tests for TrendFollow (trend_reverse.py) - trend following strategy based on triple MA alignment.

Test coverage:
- Construction: default params, custom params, invalid period order
- Cal: non-EventPriceUpdate, insufficient data, bullish alignment change, bearish alignment change, no change
- reset_state
"""

import sys
from unittest.mock import MagicMock, patch, PropertyMock

import pytest

_path = "/home/kaoru/Ginkgo/src"
if _path not in sys.path:
    sys.path.insert(0, _path)

from ginkgo.trading.strategies.trend_reverse import TrendFollow
from ginkgo.trading.events.price_update import EventPriceUpdate
from ginkgo.entities import Bar
from ginkgo.enums import DIRECTION_TYPES, FREQUENCY_TYPES


def _make_bar(close, high=None, low=None, code="000001.SZ"):
    """Helper: create a Bar entity with close/high/low prices."""
    return Bar(
        code=code,
        open=close,
        high=high if high is not None else close + 1,
        low=low if low is not None else close - 1,
        close=close,
        volume=1000,
        amount=close * 1000,
        frequency=FREQUENCY_TYPES.DAY,
        timestamp="2024-01-01",
    )


def _make_bars(prices, code="000001.SZ"):
    """Helper: create a list of bars from price list."""
    return [_make_bar(p, code=code) for p in prices]


def _make_event(code="000001.SZ"):
    """Helper: create an EventPriceUpdate with a Bar payload."""
    bar = _make_bar(100, code=code)
    event = EventPriceUpdate(payload=bar)
    return event


def _make_portfolio_info():
    """Helper: create a minimal portfolio_info dict."""
    return {"uuid": "portfolio-001", "now": "2024-01-01"}


class TestTrendFollowConstruction:
    """Construction and parameter validation tests."""

    def test_default_params(self):
        strategy = TrendFollow()
        assert strategy.short_period == 5
        assert strategy.medium_period == 20
        assert strategy.long_period == 60
        assert strategy.atr_period == 14
        assert strategy.atr_multiplier == 2.0
        assert strategy.frequency == "1d"

    def test_custom_params(self):
        strategy = TrendFollow(
            name="MyTrend",
            short_period=3,
            medium_period=10,
            long_period=30,
            atr_period=10,
            atr_multiplier=3.0,
            frequency="1h",
        )
        assert strategy.short_period == 3
        assert strategy.medium_period == 10
        assert strategy.long_period == 30
        assert strategy.atr_period == 10
        assert strategy.atr_multiplier == 3.0
        assert strategy.frequency == "1h"

    def test_short_ge_medium_raises(self):
        with pytest.raises(ValueError, match="short_period.*必须小于.*medium_period"):
            TrendFollow(short_period=20, medium_period=20)

    def test_medium_ge_long_raises(self):
        with pytest.raises(ValueError, match="medium_period.*必须小于.*long_period"):
            TrendFollow(medium_period=60, long_period=60)

    def test_period_too_small(self):
        with pytest.raises(ValueError, match="均线周期必须 >= 2"):
            TrendFollow(short_period=1)

    def test_invalid_frequency_type(self):
        # frequency is just stored as string; type validation is not strict
        strategy = TrendFollow(frequency="invalid_freq")
        assert strategy.frequency == "invalid_freq"


class TestTrendFollowCal:
    """Core cal() method logic tests."""

    def test_returns_empty_for_non_price_update_event(self):
        strategy = TrendFollow()
        portfolio_info = _make_portfolio_info()
        event = MagicMock()  # not an EventPriceUpdate
        result = strategy.cal(portfolio_info, event)
        assert result == []

    def test_returns_empty_when_insufficient_data(self):
        strategy = TrendFollow()
        portfolio_info = _make_portfolio_info()
        event = _make_event("000001.SZ")

        with patch.object(strategy, "get_bars_cached", return_value=[]):
            result = strategy.cal(portfolio_info, event)
        assert result == []

    @patch.object(TrendFollow, "get_bars_cached")
    def test_buy_on_bullish_alignment_change(self, mock_get_bars):
        """When alignment changes from not-bullish to bullish, generate LONG signal."""
        strategy = TrendFollow(
            short_period=3, medium_period=5, long_period=7, atr_period=3
        )
        portfolio_info = _make_portfolio_info()
        event = _make_event("000001.SZ")

        # Mock engine_id and task_id as they are read-only properties from context
        type(strategy).engine_id = PropertyMock(return_value="engine-001")
        type(strategy).task_id = PropertyMock(return_value="run-001")
        event = _make_event("000001.SZ")

        # Create bars where:
        # - First call: NOT bullish alignment (bearish or mixed)
        # - Second call: bullish alignment (short > medium > long)
        #
        # Bearish: prices declining, so short_ma < medium_ma < long_ma
        bearish_prices = [100, 99, 98, 97, 96, 95, 94, 93, 92, 91]
        # Bullish: prices rising strongly, so short_ma > medium_ma > long_ma
        bullish_prices = [10, 20, 30, 40, 50, 60, 70, 80, 90, 100]

        bearish_bars = _make_bars(bearish_prices)
        bullish_bars = _make_bars(bullish_prices)

        mock_get_bars.return_value = bearish_bars
        # First call: establishes state (no prior state, so no signal)
        result1 = strategy.cal(portfolio_info, event)
        assert result1 == []

        mock_get_bars.return_value = bullish_bars
        # Second call: alignment changed to bullish -> LONG signal
        result2 = strategy.cal(portfolio_info, event)
        assert len(result2) == 1
        assert result2[0].direction == DIRECTION_TYPES.LONG
        assert "000001.SZ" in result2[0].code

    @patch.object(TrendFollow, "get_bars_cached")
    def test_sell_on_bearish_alignment_change(self, mock_get_bars):
        """When alignment changes from bullish to bearish, generate SHORT signal."""
        strategy = TrendFollow(
            short_period=3, medium_period=5, long_period=7, atr_period=3
        )
        portfolio_info = _make_portfolio_info()
        event = _make_event("000001.SZ")

        type(strategy).engine_id = PropertyMock(return_value="engine-001")
        type(strategy).task_id = PropertyMock(return_value="run-001")
        event = _make_event("000001.SZ")

        # Bullish first
        bullish_prices = [10, 20, 30, 40, 50, 60, 70, 80, 90, 100]
        # Then bearish
        bearish_prices = [100, 99, 98, 97, 96, 95, 94, 93, 92, 91]

        mock_get_bars.return_value = _make_bars(bullish_prices)
        result1 = strategy.cal(portfolio_info, event)
        assert result1 == []  # first call, no prior state

        mock_get_bars.return_value = _make_bars(bearish_prices)
        result2 = strategy.cal(portfolio_info, event)
        assert len(result2) == 1
        assert result2[0].direction == DIRECTION_TYPES.SHORT

    @patch.object(TrendFollow, "get_bars_cached")
    def test_no_signal_when_alignment_unchanged(self, mock_get_bars):
        """When alignment stays bullish, no signal is generated."""
        strategy = TrendFollow(
            short_period=3, medium_period=5, long_period=7, atr_period=3
        )
        portfolio_info = _make_portfolio_info()
        event = _make_event("000001.SZ")

        bullish_prices = [10, 20, 30, 40, 50, 60, 70, 80, 90, 100]
        mock_get_bars.return_value = _make_bars(bullish_prices)

        result1 = strategy.cal(portfolio_info, event)
        assert result1 == []  # first call, no prior state

        result2 = strategy.cal(portfolio_info, event)
        assert result2 == []  # still bullish, no change

    @patch.object(TrendFollow, "get_bars_cached")
    def test_first_call_no_signal(self, mock_get_bars):
        """First call with bullish data should not generate a signal (no prior state)."""
        strategy = TrendFollow(
            short_period=3, medium_period=5, long_period=7, atr_period=3
        )
        portfolio_info = _make_portfolio_info()
        event = _make_event("000001.SZ")

        bullish_prices = [10, 20, 30, 40, 50, 60, 70, 80, 90, 100]
        mock_get_bars.return_value = _make_bars(bullish_prices)

        result = strategy.cal(portfolio_info, event)
        assert result == []

    @patch.object(TrendFollow, "get_bars_cached")
    def test_neutral_to_bearish_no_signal(self, mock_get_bars):
        """Going from neutral (first call) to bearish should not generate signal.
        The first call establishes state; second call only fires on CHANGE."""
        strategy = TrendFollow(
            short_period=3, medium_period=5, long_period=7, atr_period=3
        )
        portfolio_info = _make_portfolio_info()
        event = _make_event("000001.SZ")

        # First: neutral (mixed, not clearly bullish or bearish)
        mixed_prices = [100, 95, 100, 95, 100, 95, 100, 95, 100, 95]
        mock_get_bars.return_value = _make_bars(mixed_prices)
        result1 = strategy.cal(portfolio_info, event)
        assert result1 == []

        # Second: bearish
        bearish_prices = [100, 99, 98, 97, 96, 95, 94, 93, 92, 91]
        mock_get_bars.return_value = _make_bars(bearish_prices)
        result2 = strategy.cal(portfolio_info, event)
        assert result2 == []


class TestTrendFollowResetState:
    """reset_state tests."""

    def test_reset_state_clears_alignment_history(self):
        strategy = TrendFollow(
            short_period=3, medium_period=5, long_period=7, atr_period=3
        )
        # Manually set some state
        strategy._prev_alignment["000001.SZ"] = True
        strategy._prev_alignment["000002.SZ"] = False

        strategy.reset_state()

        assert strategy._prev_alignment == {}
