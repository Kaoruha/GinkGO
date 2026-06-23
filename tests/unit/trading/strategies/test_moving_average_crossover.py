"""
Moving Average Crossover Strategy (金叉死叉策略) 单元测试

覆盖范围:
- TestConstruction: 默认参数、自定义参数、无效参数验证
- TestCal: 事件过滤、数据不足、金叉死叉信号生成

Related: #5498
"""

import sys
_path = "/home/kaoru/Ginkgo/src"
if _path not in sys.path:
    sys.path.insert(0, _path)

import pytest
from datetime import datetime, timedelta
from unittest.mock import MagicMock, patch

from ginkgo.trading.strategies.moving_average_crossover import MovingAverageCrossover
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


def _bind_context(strategy):
    """绑定 portfolio/engine/task 上下文（create_signal 所需）"""
    ctx = MagicMock()
    ctx.portfolio_id = "portfolio-001"
    ctx.engine_id = "engine-001"
    ctx.task_id = "run-001"
    strategy._context = ctx
    return strategy


# ──────────────────────────────────────────────
# TestConstruction
# ──────────────────────────────────────────────

class TestConstruction:
    """金叉死叉策略构造与参数验证测试"""

    def test_default_params(self):
        """默认参数初始化"""
        s = MovingAverageCrossover()
        assert s.short_period == 20
        assert s.long_period == 60
        assert s.frequency == "1d"

    def test_custom_params(self):
        """自定义参数初始化"""
        s = MovingAverageCrossover(short_period=5, long_period=20)
        assert s.short_period == 5
        assert s.long_period == 20

    def test_invalid_short_ge_long_raises(self):
        """short_period >= long_period 应抛 ValueError"""
        with pytest.raises(ValueError, match="short_period"):
            MovingAverageCrossover(short_period=20, long_period=20)

    def test_invalid_period_below_two_raises(self):
        """周期 < 2 应抛 ValueError"""
        with pytest.raises(ValueError, match="均线周期"):
            MovingAverageCrossover(short_period=1, long_period=5)


# ──────────────────────────────────────────────
# TestCal
# ──────────────────────────────────────────────

class TestCal:
    """金叉死叉策略 cal 方法核心逻辑测试"""

    def test_returns_empty_for_non_price_update_event(self):
        """非 EventPriceUpdate 事件应返回空列表"""
        s = MovingAverageCrossover(short_period=2, long_period=5)
        portfolio_info = _make_portfolio_info()
        event = MagicMock()  # 不是 EventPriceUpdate
        assert s.cal(portfolio_info, event) == []

    def test_returns_empty_when_exactly_long_period_bars(self):
        """#5498: 恰好 long_period 条应判数据不足（请求 long_period+1）。

        off-by-one: 请求 N+1 但校验 >= N。恰好 5 条经两次 cal 当前会触发金叉信号
        （基于少一天的 MA 窗口），但该窗口不可靠。修复后校验 >= N+1，
        两次都 return []（数据不足）。
        """
        s = _bind_context(MovingAverageCrossover(short_period=2, long_period=5))
        portfolio_info = _make_portfolio_info()

        bars_prev = _make_bars([10.0] * 5)  # 恰好 5 条，平盘 prev short=long
        bars_cross = _make_bars([10.0, 10.0, 10.0, 10.0, 100.0])  # 5 条，short=55 > long=28

        with patch.object(s, "get_bars_cached", side_effect=[bars_prev, bars_cross]):
            s.cal(portfolio_info, _make_price_event("000001.SZ"))  # 第1次设 prev_state
            result = s.cal(portfolio_info, _make_price_event("000001.SZ"))  # 第2次金叉

        assert result == [], "恰好 long_period 条应判数据不足 return []（请求 N+1）"

    def test_golden_cross_signal_when_sufficient_data(self):
        """充足数据（long_period+1 条）两次 cal 触发金叉 → LONG 信号。

        回归保护：修复后 6 条（>= N+1=6）应正常放行产信号。
        """
        s = _bind_context(MovingAverageCrossover(short_period=2, long_period=5))
        portfolio_info = _make_portfolio_info()

        bars_prev = _make_bars([10.0] * 6)  # 6 条 = N+1，平盘
        bars_cross = _make_bars([10.0, 10.0, 10.0, 10.0, 10.0, 100.0])  # 6 条金叉

        with patch.object(s, "get_bars_cached", side_effect=[bars_prev, bars_cross]):
            s.cal(portfolio_info, _make_price_event("000001.SZ"))
            result = s.cal(portfolio_info, _make_price_event("000001.SZ"))

        assert len(result) == 1
        assert result[0].direction == DIRECTION_TYPES.LONG
