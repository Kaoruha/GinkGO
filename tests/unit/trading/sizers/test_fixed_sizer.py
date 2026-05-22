"""
Unit tests for FixedSizer using data_feeder instead of DI container.
"""
import datetime
from decimal import Decimal
from unittest.mock import MagicMock, patch

import pandas as pd
import pytest

from ginkgo.enums import DIRECTION_TYPES
from ginkgo.entities import Signal
from ginkgo.trading.sizers.fixed_sizer import FixedSizer


@pytest.fixture
def sizer():
    s = FixedSizer(name="TestSizer", volume="100")
    # mock time provider
    tp = MagicMock()
    tp.now.return_value = datetime.datetime(2026, 1, 15, 10, 0, 0)
    s._time_provider = tp
    return s


@pytest.fixture
def mock_feeder():
    feeder = MagicMock()
    return feeder


def _make_signal(code="000001.SZ", direction=DIRECTION_TYPES.LONG):
    s = Signal(code=code, direction=direction)
    s._portfolio_id = "test-portfolio"
    s._engine_id = "test-engine"
    return s


def _make_portfolio_info(cash=Decimal("500000"), positions=None):
    return {
        "cash": cash,
        "positions": positions or {},
    }


class TestFixedSizerUsesDataFeeder:
    """FixedSizer should get price data via _data_feeder, not container."""

    def test_long_uses_data_feeder(self, sizer, mock_feeder):
        """LONG order fetches price via data_feeder.get_historical_data."""
        df = pd.DataFrame({"close": [10.0, 10.5, 11.0]})
        mock_feeder.get_historical_data.return_value = df
        sizer._data_feeder = mock_feeder

        signal = _make_signal("000001.SZ", DIRECTION_TYPES.LONG)
        info = _make_portfolio_info(cash=Decimal("500000"))

        order = sizer.cal(info, signal)

        mock_feeder.get_historical_data.assert_called_once()
should NOT import container
        assert order is not None
        assert order.code == "000001.SZ"

    def test_no_data_feeder_returns_none(self, sizer):
        """Without data_feeder, LONG signal cannot get price → None."""
        sizer._data_feeder = None

        signal = _make_signal("000001.SZ", DIRECTION_TYPES.LONG)
        info = _make_portfolio_info()

        order = sizer.cal(info, signal)
        assert order is None

    def test_empty_dataframe_returns_none(self, sizer, mock_feeder):
        """data_feeder returns empty DataFrame → no order."""
        mock_feeder.get_historical_data.return_value = pd.DataFrame()
        sizer._data_feeder = mock_feeder

        signal = _make_signal("000001.SZ", DIRECTION_TYPES.LONG)
        info = _make_portfolio_info()

        order = sizer.cal(info, signal)
        assert order is None

    def test_short_does_not_call_data_feeder(self, sizer, mock_feeder):
        """SHORT order uses existing position, no price lookup needed."""
        sizer._data_feeder = mock_feeder

        pos = MagicMock()
        pos.volume = 200
        signal = _make_signal("000001.SZ", DIRECTION_TYPES.SHORT)
        info = _make_portfolio_info(positions={"000001.SZ": pos})

        order = sizer.cal(info, signal)

        mock_feeder.get_historical_data.assert_not_called()
        assert order is not None
        assert order.volume == 200

    def test_get_historical_data_args(self, sizer, mock_feeder):
        """Verify correct date range passed to get_historical_data."""
        df = pd.DataFrame({"close": [10.0, 11.0]})
        mock_feeder.get_historical_data.return_value = df
        sizer._data_feeder = mock_feeder

        signal = _make_signal("600000.SH", DIRECTION_TYPES.LONG)
        info = _make_portfolio_info()

        sizer.cal(info, signal)

        call_args = mock_feeder.get_historical_data.call_args
        assert call_args.kwargs["symbols"] == ["600000.SH"]
        assert call_args.kwargs["start_time"].date() == datetime.date(2025, 12, 16)
        assert call_args.kwargs["end_time"].date() == datetime.date(2026, 1, 14)

    def test_no_container_import(self):
        """FixedSizer module should not import container."""
        import importlib
        import ginkgo.trading.sizers.fixed_sizer as mod

        importlib.reload(mod)
        source = open(mod.__file__).read()
        assert "container" not in source
