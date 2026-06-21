"""
Unit tests for ATRSizer near-zero ATR protection (#5490).

ATRSizer still uses container.bar_service() (not yet migrated to _data_feeder),
so tests patch ginkgo.trading.sizers.atr_sizer.container.
"""
import datetime
from unittest.mock import MagicMock, patch

import pandas as pd
import pytest

from ginkgo.enums import DIRECTION_TYPES
from ginkgo.entities import Signal
from ginkgo.trading.sizers.atr_sizer import ATRSizer


@pytest.fixture
def sizer():
    s = ATRSizer(name="TestATRSizer", period=14, risk=0.01, risk_ratio=2)
    s.now = datetime.datetime(2026, 1, 15, 10, 0, 0)
    return s


def _make_signal(code="000001.SZ", direction=DIRECTION_TYPES.LONG):
    s = Signal(code=code, direction=direction)
    return s


def _make_portfolio_info(cash=500000.0, positions=None):
    # NOTE: cash as float — atr_sizer.py:88 does `cash * self.risk` with no
    # Decimal coercion, so Decimal cash raises TypeError. That is a separate
    # pre-existing issue, out of scope for #5490 (near-zero ATR floor).
    return {"cash": cash, "positions": positions or {}}


def _bar_df(n, high, low, close):
    """Build a flat-price bar DataFrame (n rows) producing a known ATR."""
    return pd.DataFrame({
        "high": [high] * n,
        "low": [low] * n,
        "close": [close] * n,
    })


class TestATRSizerNearZeroFloor:
    """#5490: ATR approaching zero must not produce oversized positions."""

    def test_normal_atr_returns_expected_volume(self, sizer):
        """Tracer: normal ATR (TR=1 → ATR=1 → atr=2) yields bounded volume.

        max_money=5000, atr=2 → max_shares=int(5000/2/100)*100=2500.
        Establishes mock path + baseline before adding floor logic.
        """
        df = _bar_df(15, high=11.0, low=10.0, close=10.0)
        signal = _make_signal("000001.SZ", DIRECTION_TYPES.LONG)
        info = _make_portfolio_info(cash=500000.0)

        with patch("ginkgo.trading.sizers.atr_sizer.container") as cm:
            service = MagicMock()
            result = MagicMock()
            result.success = True
            result.data.to_dataframe.return_value = df
            service.get.return_value = result
            cm.bar_service.return_value = service

            order = sizer.cal(info, signal)

        assert order is not None
        assert order.volume == 2500

    def test_near_zero_atr_floored_to_prevent_oversized_position(self, sizer):
        """#5490: tiny non-zero ATR (near-stagnant bar) must not explode volume.

        high=10.001/low=10.0/close=10.0 → TR=0.001 → ATR=0.001 → atr=0.002.
        Without a floor: int(5000/0.002/100)*100 = 2,500,000 shares (oversized).
        Floor (close * min_atr_percent=0.005 → 0.05, since 0.002<0.05):
        int(5000/0.05/100)*100 = 100,000 shares (bounded, 25x smaller).
        """
        df = _bar_df(15, high=10.001, low=10.0, close=10.0)
        signal = _make_signal("000001.SZ", DIRECTION_TYPES.LONG)
        info = _make_portfolio_info(cash=500000.0)

        with patch("ginkgo.trading.sizers.atr_sizer.container") as cm:
            service = MagicMock()
            result = MagicMock()
            result.success = True
            result.data.to_dataframe.return_value = df
            service.get.return_value = result
            cm.bar_service.return_value = service

            order = sizer.cal(info, signal)

        assert order is not None
        # 2,500,000 (unfloored) would mean ~25M CNY position on 500k cash.
        assert order.volume == 100000

    def test_zero_atr_returns_none_not_floored(self, sizer):
        """Regression: flat bar (TR=0 → ATR=0) must return None, not floor up.

        The floor sits AFTER the atr==0 guard, so a true zero still declines
        the signal. Without this ordering, floor would turn a dead market into
        a max-size order.
        """
        df = _bar_df(15, high=10.0, low=10.0, close=10.0)
        signal = _make_signal("000001.SZ", DIRECTION_TYPES.LONG)
        info = _make_portfolio_info(cash=500000.0)

        with patch("ginkgo.trading.sizers.atr_sizer.container") as cm:
            service = MagicMock()
            result = MagicMock()
            result.success = True
            result.data.to_dataframe.return_value = df
            service.get.return_value = result
            cm.bar_service.return_value = service

            order = sizer.cal(info, signal)

        assert order is None

    def test_min_atr_percent_configurable(self):
        """min_atr_percent raises the floor → smaller max_shares on near-zero ATR.

        Same tiny-ATR bar as the floor test, but min_atr_percent=0.01 →
        min_atr=0.1 (vs 0.05 default) → int(5000/0.1/100)*100 = 50,000.
        """
        s = ATRSizer(name="T", period=14, risk=0.01, risk_ratio=2, min_atr_percent=0.01)
        s.now = datetime.datetime(2026, 1, 15, 10, 0, 0)
        df = _bar_df(15, high=10.001, low=10.0, close=10.0)
        signal = _make_signal("000001.SZ", DIRECTION_TYPES.LONG)
        info = _make_portfolio_info(cash=500000.0)

        with patch("ginkgo.trading.sizers.atr_sizer.container") as cm:
            service = MagicMock()
            result = MagicMock()
            result.success = True
            result.data.to_dataframe.return_value = df
            service.get.return_value = result
            cm.bar_service.return_value = service

            order = s.cal(info, signal)

        assert order is not None
        assert order.volume == 50000


class TestATRSizerDoesNotLogDataFrame:
    """#6019: ATRSizer 不得以 INFO 级别输出完整 DataFrame（遗留调试日志）。

    历史：原始 `print(df)` 调试代码被机械地替换为 `GLOG.INFO(df)`，
    导致每次 cal() 都把完整行情 DataFrame（高/低/收 多行）写日志。
    验收：cal() 执行后，GLOG.INFO 的所有调用参数中不得出现
    pandas.DataFrame 实例（"Order Generated." 字符串、Order 对象等
    正常业务日志不受影响）。
    """

    def test_cal_does_not_log_full_dataframe(self, sizer):
        df = _bar_df(15, high=11.0, low=10.0, close=10.0)
        signal = _make_signal("000001.SZ", DIRECTION_TYPES.LONG)
        info = _make_portfolio_info(cash=500000.0)

        with patch("ginkgo.trading.sizers.atr_sizer.GLOG") as mock_glog, \
             patch("ginkgo.trading.sizers.atr_sizer.container") as cm:
            service = MagicMock()
            result = MagicMock()
            result.success = True
            result.data.to_dataframe.return_value = df
            service.get.return_value = result
            cm.bar_service.return_value = service

            sizer.cal(info, signal)

        info_args = [c.args[0] for c in mock_glog.INFO.call_args_list if c.args]
        dataframe_logged = any(isinstance(a, pd.DataFrame) for a in info_args)
        assert not dataframe_logged, (
            f"#6019: ATRSizer 仍以 INFO 输出完整 DataFrame: {info_args}"
        )
