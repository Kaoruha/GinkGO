"""
Dual Thrust 策略单元测试

覆盖范围:
- TestDualThrustCal: 突破信号生成（LONG/SHORT/无信号）
- #5496: Decimal * numpy.float64 类型混用导致 cal() 抛 TypeError 的回归防护

Related: #5496
"""

import sys
_path = "/home/kaoru/Ginkgo/src"
if _path not in sys.path:
    sys.path.insert(0, _path)

import pandas as pd
from datetime import datetime
from unittest.mock import MagicMock

from ginkgo.trading.strategies.dual_thrust import StrategyDualThrust
from ginkgo.enums import DIRECTION_TYPES


def _make_price_event(code="000001.SZ"):
    ev = MagicMock()
    ev.code = code
    return ev


def _make_portfolio_info(now=None, interested_codes=None, positions=None):
    if now is None:
        now = datetime(2024, 1, 20)
    if positions is None:
        positions = {}
    return {
        "uuid": "portfolio-001",
        "engine_id": "engine-001",
        "task_id": "run-001",
        "now": now,
        "interested_codes": interested_codes or ["000001.SZ"],
        "positions": positions,
    }


# 多头突破：历史窗口 range 小，昨日收低于开，今日大涨收（突破买入线）
LONG_BREAKOUT_DF = pd.DataFrame({
    "open":  [100.0, 100.0, 100.0, 100.0, 100.0],
    "high":  [100.1, 100.1, 100.1, 100.1, 101.0],
    "low":   [ 99.9,  99.9,  99.9,  99.9,  99.0],
    "close": [ 99.5,  99.5,  99.5,  99.5, 105.0],
})

# 空头跌破：历史窗口 range 小，昨日收高于开，今日大跌收（跌破卖出线）
SHORT_BREAKDOWN_DF = pd.DataFrame({
    "open":  [100.0, 100.0, 100.0, 100.0, 100.0],
    "high":  [100.1, 100.1, 100.1, 100.1, 101.0],
    "low":   [ 99.9,  99.9,  99.9,  99.9,  99.0],
    "close": [100.5, 100.5, 100.5, 100.5,  95.0],
})

# 横盘：无明显突破
FLAT_DF = pd.DataFrame({
    "open":  [100.0, 100.0, 100.0, 100.0, 100.0],
    "high":  [100.1, 100.1, 100.1, 100.1, 100.1],
    "low":   [ 99.9,  99.9,  99.9,  99.9,  99.9],
    "close": [100.0, 100.0, 100.0, 100.0, 100.0],
})


def _make_strategy(df, spans=3, k_buy=0.5, k_sell=0.5):
    s = StrategyDualThrust(spans=spans, k_buy=k_buy, k_sell=k_sell)
    feeder = MagicMock()
    feeder.get_historical_data.return_value = df
    s.bind_data_feeder(feeder)
    ctx = MagicMock()
    ctx.portfolio_id = "portfolio-001"
    ctx.engine_id = "engine-001"
    ctx.task_id = "run-001"
    s._context = ctx
    return s


class TestDualThrustCal:
    """DualThrust cal 方法信号生成测试 (#5496)"""

    def test_generates_long_on_breakout(self):
        """#5496: 价格突破买入线 → LONG 信号，且 cal() 不抛 TypeError"""
        s = _make_strategy(LONG_BREAKOUT_DF)
        info = _make_portfolio_info(positions={})
        result = s.cal(info, _make_price_event("000001.SZ"))
        assert len(result) == 1
        assert result[0].direction == DIRECTION_TYPES.LONG
        assert result[0].code == "000001.SZ"

    def test_generates_short_on_breakdown_with_position(self):
        """#5496: 持仓且价格跌破卖出线 → SHORT 信号"""
        s = _make_strategy(SHORT_BREAKDOWN_DF)
        info = _make_portfolio_info(positions={"000001.SZ": {}})
        result = s.cal(info, _make_price_event("000001.SZ"))
        assert len(result) == 1
        assert result[0].direction == DIRECTION_TYPES.SHORT

    def test_no_signal_in_flat_market(self):
        """#5496: 横盘无突破 → 无信号"""
        s = _make_strategy(FLAT_DF)
        info = _make_portfolio_info(positions={})
        result = s.cal(info, _make_price_event("000001.SZ"))
        assert result == []


class TestDualThrustTypeConsistency:
    """#5496: 数值类型一致性回归防护（防止重新引入 Decimal/numpy 混用）"""

    def test_k_buy_k_sell_stored_as_float(self):
        """k_buy/k_sell 必须存为 float，不得包 Decimal（与 numpy/pandas 算术兼容）"""
        from decimal import Decimal
        s = StrategyDualThrust(spans=3, k_buy=0.5, k_sell=0.7)
        assert isinstance(s._k_buy, float)
        assert isinstance(s._k_sell, float)
        assert not isinstance(s._k_buy, Decimal)

    def test_calculate_range_returns_float(self):
        """_calculate_range 返回值须为 float（与 _k_buy 算术兼容）"""
        s = _make_strategy(LONG_BREAKOUT_DF)
        r = s._calculate_range(LONG_BREAKOUT_DF)
        assert isinstance(r, (float, int)), f"期望 float，实际 {type(r)}"

    def test_arithmetic_chain_no_typeerror_with_fractional_k(self):
        """分数 k 值（如 0.3）下整条算术链不得抛 TypeError"""
        s = _make_strategy(LONG_BREAKOUT_DF, k_buy=0.3, k_sell=0.3)
        info = _make_portfolio_info(positions={})
        # 不抛 TypeError 即通过
        s.cal(info, _make_price_event("000001.SZ"))


class TestDualThrustHistoryWindow:
    """#4658: 历史数据窗口须按交易日倍数预留，避免日历日不足致恒零信号"""

    def test_history_window_covers_trading_days(self):
        """#4658: spans=7 时窗口不可仅 spans+1=8 日历日

        A 股 8 日历日 ≈ 5-6 交易日 < spans+1=8，触发
        `df.shape[0] < spans+1` 守卫恒真 → 策略 100% 零信号。
        修复后窗口日历日数须达 spans*2 级别，覆盖周末（每周 2/7 非交易日）
        与法定节假日 buffer。此断言锁定“按交易日倍数预留”的语义，
        不耦合具体公式（spans*2+5 / BDay 等任何 >= spans*2 的修复均通过）。
        """
        spans = 7
        s = _make_strategy(LONG_BREAKOUT_DF, spans=spans)
        info = _make_portfolio_info(now=datetime(2024, 1, 22))  # 周一
        s.cal(info, _make_price_event("000001.SZ"))

        call = s.data_feeder.get_historical_data.call_args
        date_start = call.kwargs["start_time"]
        calendar_days = (info["now"] - date_start).days

        min_required = spans * 2
        assert calendar_days >= min_required, (
            f"历史窗口仅 {calendar_days} 日历日 < {min_required}，"
            f"A 股下交易日数将不足 {spans + 1}，"
            f"触发 df.shape[0] < spans+1 守卫恒零信号 (#4658)"
        )
