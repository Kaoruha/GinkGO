"""
Momentum Strategy (动量因子策略) 单元测试

覆盖范围:
- TestMomentumConstruction: 默认参数、自定义参数、无效参数验证
- TestMomentumCal: 事件过滤、数据不足、动量信号生成
- TestResetState: 状态重置

Related: #3620
"""

import sys
_path = "/home/kaoru/Ginkgo/src"
if _path not in sys.path:
    sys.path.insert(0, _path)

import pytest
from datetime import datetime, timedelta
from unittest.mock import MagicMock, patch

from ginkgo.trading.strategies.momentum import Momentum
from ginkgo.trading.events.price_update import EventPriceUpdate
from ginkgo.enums import DIRECTION_TYPES
from ginkgo.entities import Bar


def _make_bar(close: float, code: str = "000001.SZ", timestamp: datetime = None):
    """创建一个模拟的 bar 对象"""
    if timestamp is None:
        timestamp = datetime(2024, 1, 15, 10, 0, 0)
    bar = MagicMock(spec=Bar)
    bar.close = close
    bar.code = code
    bar.timestamp = timestamp
    return bar


def _make_bars(closes: list, code: str = "000001.SZ", start: datetime = None):
    """创建一个 bar 列表，每条间隔一天"""
    if start is None:
        start = datetime(2024, 1, 1)
    bars = []
    for i, c in enumerate(closes):
        bars.append(_make_bar(c, code=code, timestamp=start + timedelta(days=i)))
    return bars


def _make_price_event(code: str = "000001.SZ"):
    """创建模拟的 EventPriceUpdate（绕过 Bar 构造复杂性）"""
    event = MagicMock(spec=EventPriceUpdate)
    event.code = code
    event.__class__ = EventPriceUpdate
    return event


def _make_portfolio_info(now: datetime = None, interested_codes=None):
    """创建模拟的 portfolio_info 字典"""
    if now is None:
        now = datetime(2024, 1, 20)
    if interested_codes is None:
        interested_codes = ["000001.SZ"]
    return {
        "uuid": "portfolio-001",
        "engine_id": "engine-001",
        "task_id": "run-001",
        "now": now,
        "interested_codes": interested_codes,
        "positions": {},
    }


@pytest.fixture
def bound_strategy():
    """创建并绑定上下文的 Momentum 策略实例"""
    s = Momentum(lookback_period=5, momentum_threshold=0.02)
    ctx = MagicMock()
    ctx.portfolio_id = "portfolio-001"
    ctx.engine_id = "engine-001"
    ctx.task_id = "run-001"
    s._context = ctx
    return s


# ──────────────────────────────────────────────
# TestMomentumConstruction
# ──────────────────────────────────────────────

class TestMomentumConstruction:
    """动量策略构造与参数验证测试"""

    def test_default_params(self):
        """默认参数初始化"""
        s = Momentum()
        assert s.lookback_period == 20
        assert s.momentum_threshold == 0.02
        assert s.frequency == "1d"

    def test_custom_params(self):
        """自定义参数初始化"""
        s = Momentum(
            name="MyMomentum",
            lookback_period=10,
            momentum_threshold=0.05,
            frequency="1h",
        )
        assert s.name == "MyMomentum"
        assert s.lookback_period == 10
        assert s.momentum_threshold == 0.05
        assert s.frequency == "1h"

    def test_invalid_lookback_period_raises(self):
        """lookback_period < 2 应该抛出 ValueError"""
        with pytest.raises(ValueError, match="lookback_period"):
            Momentum(lookback_period=1)


# ──────────────────────────────────────────────
# TestMomentumCal
# ──────────────────────────────────────────────

class TestMomentumCal:
    """动量策略 cal 方法核心逻辑测试"""

    def test_returns_empty_for_non_price_update_event(self):
        """非 EventPriceUpdate 事件应返回空列表"""
        s = Momentum()
        portfolio_info = _make_portfolio_info()
        event = MagicMock()  # 不是 EventPriceUpdate
        result = s.cal(portfolio_info, event)
        assert result == []

    def test_returns_empty_when_insufficient_data(self):
        """数据不足时返回空列表"""
        s = Momentum(lookback_period=20)
        portfolio_info = _make_portfolio_info()

        with patch.object(s, "get_bars_cached", return_value=[]):
            result = s.cal(portfolio_info, _make_price_event("000001.SZ"))
            assert result == []

    def test_returns_empty_when_exactly_lookback_period_bars(self, bound_strategy):
        """#5498: 恰好 lookback_period 条应判数据不足（请求 lookback_period+1）。

        off-by-one: 请求 N+1 但校验 >= N。恰好 5 条上升数据当前会产 LONG 信号
        （动量 0.1 > 阈值 0.02），但动量区间短缺一天（应跨 6 条 lookback）。
        修复后校验 >= N+1，恰好 5 条 return []。
        """
        s = bound_strategy  # lookback_period=5
        now = datetime(2024, 1, 20)
        portfolio_info = _make_portfolio_info(now=now)
        bars = _make_bars([100.0, 101.0, 103.0, 106.0, 110.0])  # 恰好 5 条，上升

        with patch.object(s, "get_bars_cached", return_value=bars):
            result = s.cal(portfolio_info, _make_price_event("000001.SZ"))
        assert result == [], "恰好 lookback_period 条应判数据不足 return []（请求 N+1）"

    def test_long_signal_when_momentum_exceeds_threshold(self, bound_strategy):
        """动量超过正阈值且无持仓 → LONG 信号"""
        s = bound_strategy
        now = datetime(2024, 1, 20)
        portfolio_info = _make_portfolio_info(now=now)
        bars = _make_bars([100.0, 101.0, 103.0, 106.0, 108.0, 110.0])

        with patch.object(s, "get_bars_cached", return_value=bars):
            result = s.cal(portfolio_info, _make_price_event("000001.SZ"))

        assert len(result) == 1
        assert result[0].direction == DIRECTION_TYPES.LONG
        assert result[0].code == "000001.SZ"

    def test_short_signal_when_negative_momentum_with_position(self, bound_strategy):
        """动量低于负阈值且有持仓 → SHORT 信号"""
        s = bound_strategy
        now = datetime(2024, 1, 20)
        portfolio_info = _make_portfolio_info(now=now)
        portfolio_info["positions"] = {"000001.SZ": {}}
        bars = _make_bars([100.0, 98.0, 96.0, 93.0, 91.0, 90.0])

        with patch.object(s, "get_bars_cached", return_value=bars):
            result = s.cal(portfolio_info, _make_price_event("000001.SZ"))

        assert len(result) == 1
        assert result[0].direction == DIRECTION_TYPES.SHORT

    def test_no_signal_within_threshold(self):
        """动量在阈值范围内 → 无信号"""
        s = Momentum(lookback_period=5, momentum_threshold=0.10)
        now = datetime(2024, 1, 20)
        portfolio_info = _make_portfolio_info(now=now)
        bars = _make_bars([100.0, 101.0, 101.5, 102.0, 102.5, 103.0])

        with patch.object(s, "get_bars_cached", return_value=bars):
            result = s.cal(portfolio_info, _make_price_event("000001.SZ"))

        assert result == []

    def test_no_duplicate_buy_with_position(self):
        """有持仓且动量超阈值 → 不重复买入"""
        s = Momentum(lookback_period=5, momentum_threshold=0.02)
        now = datetime(2024, 1, 20)
        portfolio_info = _make_portfolio_info(now=now)
        portfolio_info["positions"] = {"000001.SZ": {}}
        bars = _make_bars([100.0, 101.0, 103.0, 106.0, 108.0, 110.0])

        with patch.object(s, "get_bars_cached", return_value=bars):
            result = s.cal(portfolio_info, _make_price_event("000001.SZ"))

        assert result == []

    def test_returns_empty_when_current_time_not_datetime(self):
        """Related: #3820 — current_time 非 datetime 应返回空"""
        s = Momentum()
        portfolio_info = _make_portfolio_info()
        portfolio_info["now"] = "not-a-datetime"
        result = s.cal(portfolio_info, _make_price_event("000001.SZ"))
        assert result == []

    def test_returns_empty_when_closes_less_than_two(self):
        """Related: #3820 — closes 列表不足 2 个数据点应返回空"""
        s = Momentum(lookback_period=3)
        portfolio_info = _make_portfolio_info()
        bars = _make_bars([100.0])

        with patch.object(s, "get_bars_cached", return_value=bars):
            result = s.cal(portfolio_info, _make_price_event("000001.SZ"))
        assert result == []

    def test_returns_empty_when_first_close_zero_or_negative(self):
        """Related: #3820 — first_close <= 0 应返回空"""
        s = Momentum(lookback_period=3)
        portfolio_info = _make_portfolio_info()
        bars = _make_bars([0.0, 50.0, 60.0, 70.0])

        with patch.object(s, "get_bars_cached", return_value=bars):
            result = s.cal(portfolio_info, _make_price_event("000001.SZ"))
        assert result == []

    def test_returns_empty_on_get_bars_cached_exception(self):
        """Related: #3820 — get_bars_cached 抛异常应返回空"""
        s = Momentum()
        portfolio_info = _make_portfolio_info()

        with patch.object(s, "get_bars_cached", side_effect=RuntimeError("db error")):
            result = s.cal(portfolio_info, _make_price_event("000001.SZ"))
        assert result == []

    def test_signals_contain_correct_portfolio_context(self, bound_strategy):
        """信号应包含正确的 portfolio_id、engine_id、business_timestamp"""
        s = bound_strategy
        s._context.engine_id = "engine-xyz"
        s._context.task_id = "run-abc"
        now = datetime(2024, 3, 15, 14, 30, 0)
        portfolio_info = _make_portfolio_info(now=now, interested_codes=["000001.SZ"])
        bars = _make_bars([100.0, 101.0, 102.0, 103.0, 104.0, 110.0])

        with patch.object(s, "get_bars_cached", return_value=bars):
            result = s.cal(portfolio_info, _make_price_event("000001.SZ"))

        assert len(result) == 1
        sig = result[0]
        assert sig.portfolio_id == "portfolio-001"
        assert sig.engine_id == "engine-xyz"
        assert sig.task_id == "run-abc"
        assert sig.business_timestamp == now


# ──────────────────────────────────────────────
# TestResetState
# ──────────────────────────────────────────────

class TestResetState:
    """状态重置测试"""

    def test_reset_state(self):
        """重置后数据缓存应清空"""
        s = Momentum()
        # 填充缓存
        s._data_cache["000001.SZ"] = [MagicMock()]
        s._cache_timestamps["000001.SZ"] = datetime(2024, 1, 1)

        s.reset_state()

        assert len(s._data_cache) == 0
        assert len(s._cache_timestamps) == 0
