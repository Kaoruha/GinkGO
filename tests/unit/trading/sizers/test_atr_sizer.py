"""
Unit tests for ATRSizer.

Covers:
- #4706: LONG 取数走注入的 _data_feeder.get_historical_data()（对齐
  FixedSizer/RatioSizer），缺数据时 WARN + return None 恢复可诊断性。
- #5490: 近零 ATR 保护（floor）。
- #6019: 不得以 INFO 输出完整 DataFrame。
- #4708: self.now 误用（应 get_time_provider()）+ Decimal 列/cash 算术 TypeError。

注：ATRSizer 经 portfolio_base.bind_data_feeder 注入 feeder（见 sizer_base），
单测通过直接设置 sizer._data_feeder 模拟注入，走公共 cal() 接口验证行为。
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
    # #4708: 对齐 RatioSizer/FixedSizer 范式，sizer 经 get_time_provider() 取当前时间。
    # 旧 fixture 直接 `s.now = ...` 掩盖了 ATRSizer 误用 self.now（#4706 引入、不存在）
    # 的 AttributeError —— 真实 engine 从不设置 sizer.now。
    tp = MagicMock()
    tp.now.return_value = datetime.datetime(2026, 1, 15, 10, 0, 0)
    s._time_provider = tp
    return s


def _make_signal(code="000001.SZ", direction=DIRECTION_TYPES.LONG):
    s = Signal(code=code, direction=direction)
    return s


def _make_portfolio_info(cash=500000.0, positions=None):
    # NOTE: cash as float — atr_sizer.py does `cash * self.risk` with no
    # Decimal coercion, so Decimal cash raises TypeError. That is a separate
    # pre-existing issue, out of scope here.
    return {"cash": cash, "positions": positions or {}}


def _bar_df(n, high, low, close):
    """Build a flat-price bar DataFrame (n rows) producing a known ATR."""
    return pd.DataFrame({
        "high": [high] * n,
        "low": [low] * n,
        "close": [close] * n,
    })


def _bind_feeder(sizer, df):
    """注入模拟 _data_feeder：get_historical_data 返回给定 DataFrame。

    对齐 BacktestFeeder.get_historical_data 契约（返回 DataFrame，空数据返
    空 DataFrame）。模拟 portfolio_base 在装配时调 bind_data_feeder 的结果。
    """
    feeder = MagicMock()
    feeder.get_historical_data.return_value = df
    sizer._data_feeder = feeder
    return feeder


class TestATRSizerDataFeederPath:
    """#4706: LONG 取数走 _data_feeder.get_historical_data()，缺数据 WARN。"""

    def test_normal_bars_via_feeder_returns_expected_volume(self, sizer):
        """Tracer: 经 _data_feeder 注入正常 bar，产出预期 volume（与历史 mock 路径一致）。

        TR=1 → ATR=1 → atr=2；max_money=5000，max_shares=int(5000/2/100)*100=2500。
        验证迁移到 feeder 契约后 sizing 行为不变。
        """
        df = _bar_df(15, high=11.0, low=10.0, close=10.0)
        _bind_feeder(sizer, df)
        signal = _make_signal("000001.SZ", DIRECTION_TYPES.LONG)
        info = _make_portfolio_info(cash=500000.0)

        order = sizer.cal(info, signal)

        assert order is not None
        assert order.volume == 2500
        # 契约：经 _data_feeder.get_historical_data 取数（symbols/start_time/end_time）
        assert sizer._data_feeder.get_historical_data.called

    def test_feeder_unbound_logs_error_and_returns_none(self, sizer):
        """#4706: _data_feeder 未注入（None）时 ERROR + return None（对齐 FixedSizer）。"""
        assert sizer._data_feeder is None  # 默认未绑定
        signal = _make_signal("000001.SZ", DIRECTION_TYPES.LONG)
        info = _make_portfolio_info(cash=500000.0)

        with patch("ginkgo.trading.sizers.atr_sizer.GLOG") as mock_glog:
            order = sizer.cal(info, signal)

        assert order is None
        mock_glog.ERROR.assert_called()

    def test_no_bars_warns_and_returns_none(self, sizer):
        """#4706 验收#1/#3: feeder 返回空 DataFrame → WARN 'no bars for {code}, signal dropped' + None。"""
        _bind_feeder(sizer, pd.DataFrame())  # 空 DF
        signal = _make_signal("000001.SZ", DIRECTION_TYPES.LONG)
        info = _make_portfolio_info(cash=500000.0)

        with patch("ginkgo.trading.sizers.atr_sizer.GLOG") as mock_glog:
            order = sizer.cal(info, signal)

        assert order is None
        # WARN 被调用，且消息含 code 与 "signal dropped"
        warn_calls = [c.args[0] for c in mock_glog.WARN.call_args_list if c.args]
        assert any("000001.SZ" in m and "signal dropped" in m for m in warn_calls), (
            f"缺 bar 应 WARN 'no bars ... signal dropped'，实际 WARN: {warn_calls}"
        )

    def test_feeder_returns_none_warns_and_returns_none(self, sizer):
        """#4706: feeder 返回 None（时间校验失败/未来数据泄露拦截）→ WARN + None。"""
        _bind_feeder(sizer, None)
        signal = _make_signal("000001.SZ", DIRECTION_TYPES.LONG)
        info = _make_portfolio_info(cash=500000.0)

        with patch("ginkgo.trading.sizers.atr_sizer.GLOG") as mock_glog:
            order = sizer.cal(info, signal)

        assert order is None
        mock_glog.WARN.assert_called()

    def test_zero_atr_warns_and_returns_none(self, sizer):
        """#4706: 平盘 bar（TR=0 → ATR=0）→ WARN 'ATR is ...' + None（原静默分支恢复可诊断）。"""
        df = _bar_df(15, high=10.0, low=10.0, close=10.0)  # 全平 → ATR=0
        _bind_feeder(sizer, df)
        signal = _make_signal("000001.SZ", DIRECTION_TYPES.LONG)
        info = _make_portfolio_info(cash=500000.0)

        with patch("ginkgo.trading.sizers.atr_sizer.GLOG") as mock_glog:
            order = sizer.cal(info, signal)

        assert order is None
        warn_calls = [c.args[0] for c in mock_glog.WARN.call_args_list if c.args]
        assert any("ATR is" in m and "000001.SZ" in m for m in warn_calls), (
            f"ATR=0 应 WARN，实际: {warn_calls}"
        )


class TestATRSizerNearZeroFloor:
    """#5490: ATR approaching zero must not produce oversized positions."""

    def test_normal_atr_returns_expected_volume(self, sizer):
        """Tracer: normal ATR (TR=1 → ATR=1 → atr=2) yields bounded volume.

        max_money=5000, atr=2 → max_shares=int(5000/2/100)*100=2500.
        """
        df = _bar_df(15, high=11.0, low=10.0, close=10.0)
        _bind_feeder(sizer, df)
        signal = _make_signal("000001.SZ", DIRECTION_TYPES.LONG)
        info = _make_portfolio_info(cash=500000.0)

        order = sizer.cal(info, signal)

        assert order is not None
        assert order.volume == 2500

    def test_near_zero_atr_floored_to_prevent_oversized_position(self, sizer):
        """#5490: tiny non-zero ATR (near-stagnant bar) must not explode volume.

        high=10.001/low=10.0/close=10.0 → TR=0.001 → ATR=0.001 → atr=0.002.
        Floor (close * min_atr_percent=0.005 → 0.05, since 0.002<0.05):
        int(5000/0.05/100)*100 = 100,000 shares (vs 2,500,000 unfloored).
        """
        df = _bar_df(15, high=10.001, low=10.0, close=10.0)
        _bind_feeder(sizer, df)
        signal = _make_signal("000001.SZ", DIRECTION_TYPES.LONG)
        info = _make_portfolio_info(cash=500000.0)

        order = sizer.cal(info, signal)

        assert order is not None
        assert order.volume == 100000

    def test_min_atr_percent_configurable(self):
        """min_atr_percent raises the floor → smaller max_shares on near-zero ATR.

        Same tiny-ATR bar, min_atr_percent=0.01 → min_atr=0.1 → int(5000/0.1/100)*100=50,000.
        """
        s = ATRSizer(name="T", period=14, risk=0.01, risk_ratio=2, min_atr_percent=0.01)
        tp = MagicMock()
        tp.now.return_value = datetime.datetime(2026, 1, 15, 10, 0, 0)
        s._time_provider = tp
        df = _bar_df(15, high=10.001, low=10.0, close=10.0)
        _bind_feeder(s, df)
        signal = _make_signal("000001.SZ", DIRECTION_TYPES.LONG)
        info = _make_portfolio_info(cash=500000.0)

        order = s.cal(info, signal)

        assert order is not None
        assert order.volume == 50000


class TestATRSizerDoesNotLogDataFrame:
    """#6019: ATRSizer 不得以 INFO 级别输出完整 DataFrame（遗留调试日志）。"""

    def test_cal_does_not_log_full_dataframe(self, sizer):
        df = _bar_df(15, high=11.0, low=10.0, close=10.0)
        _bind_feeder(sizer, df)
        signal = _make_signal("000001.SZ", DIRECTION_TYPES.LONG)
        info = _make_portfolio_info(cash=500000.0)

        with patch("ginkgo.trading.sizers.atr_sizer.GLOG") as mock_glog:
            sizer.cal(info, signal)

        info_args = [c.args[0] for c in mock_glog.INFO.call_args_list if c.args]
        dataframe_logged = any(isinstance(a, pd.DataFrame) for a in info_args)
        assert not dataframe_logged, (
            f"#6019: ATRSizer 仍以 INFO 输出完整 DataFrame: {info_args}"
        )


class TestATRSizerDecimalColumns:
    """#4708: 真实回测下 bar 列为 Decimal、cash 也常为 Decimal。

    #4706 引入的算术链 `ATR.cal()*risk_ratio` / `close*min_atr_percent` /
    `cash*risk` / `close*1.1` 在 Decimal 输入下全部 TypeError（原测试用 float
    bar + float cash 绕过）。本类补 Decimal 路径回归，与 DualThrust #4708 同源。
    """

    def test_decimal_bars_and_cash_no_typeerror(self):
        """Decimal high/low/close + Decimal cash → cal() 不抛 TypeError 且产出合理 volume。

        TR=1 → ATR=1 → atr=2；max_money=5000，max_shares=int(5000/2/100)*100=2500。
        与 float 路径期望一致（ Decimal 不改变 sizing 语义）。
        """
        from decimal import Decimal
        s = ATRSizer(name="T", period=14, risk=0.01, risk_ratio=2)
        tp = MagicMock()
        tp.now.return_value = datetime.datetime(2026, 1, 15, 10, 0, 0)
        s._time_provider = tp
        df = pd.DataFrame({
            "high": [Decimal("11")] * 15,
            "low": [Decimal("10")] * 15,
            "close": [Decimal("10")] * 15,
        })
        _bind_feeder(s, df)
        signal = _make_signal("000001.SZ", DIRECTION_TYPES.LONG)
        info = {"cash": Decimal("500000"), "positions": {}}

        order = s.cal(info, signal)

        assert order is not None
        assert order.volume == 2500

    def test_decimal_bars_near_zero_atr_floor(self):
        """Decimal 列 + 近零 ATR → floor 保护生效，不抛 TypeError。

        high=Decimal('10.001')/low=Decimal('10')/close=Decimal('10') → TR=0.001 →
        atr=0.002 < floor(0.05) → floor 生效 → int(5000/0.05/100)*100=100000。
        """
        from decimal import Decimal
        s = ATRSizer(name="T", period=14, risk=0.01, risk_ratio=2)
        tp = MagicMock()
        tp.now.return_value = datetime.datetime(2026, 1, 15, 10, 0, 0)
        s._time_provider = tp
        df = pd.DataFrame({
            "high": [Decimal("10.001")] * 15,
            "low": [Decimal("10")] * 15,
            "close": [Decimal("10")] * 15,
        })
        _bind_feeder(s, df)
        signal = _make_signal("000001.SZ", DIRECTION_TYPES.LONG)
        info = {"cash": Decimal("500000"), "positions": {}}

        order = s.cal(info, signal)

        assert order is not None
        assert order.volume == 100000
