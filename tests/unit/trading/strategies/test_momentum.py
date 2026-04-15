"""
Momentum Strategy (动量因子策略) 单元测试

覆盖范围:
- TestMomentumConstruction: 默认参数、自定义参数、无效参数验证
- TestMomentumCal: 事件过滤、数据不足、动量排名、再平衡逻辑
- test_reset_state: 状态重置
"""

import sys
sys.path.insert(0, "/home/kaoru/Ginkgo/src")

import pytest
from datetime import datetime, timedelta
from unittest.mock import MagicMock, patch

from ginkgo.trading.strategies.momentum import Momentum
from ginkgo.trading.events.price_update import EventPriceUpdate
from ginkgo.enums import DIRECTION_TYPES


def _make_bar(close: float, timestamp: datetime = None):
    """创建一个模拟的 bar 对象"""
    if timestamp is None:
        timestamp = datetime(2024, 1, 15, 10, 0, 0)
    bar = MagicMock()
    bar.close = close
    bar.timestamp = timestamp
    return bar


def _make_bars(closes: list, start: datetime = None):
    """创建一个 bar 列表，每条间隔一天"""
    if start is None:
        start = datetime(2024, 1, 1)
    bars = []
    for i, c in enumerate(closes):
        bars.append(_make_bar(c, timestamp=start + timedelta(days=i)))
    return bars


def _make_portfolio_info(now: datetime = None, interested_codes=None):
    """创建模拟的 portfolio_info 字典"""
    if now is None:
        now = datetime(2024, 1, 20)
    if interested_codes is None:
        interested_codes = ["000001.SZ", "000002.SZ", "000003.SZ"]
    return {
        "uuid": "portfolio-001",
        "engine_id": "engine-001",
        "run_id": "run-001",
        "now": now,
        "interested_codes": interested_codes,
        "positions": {},
    }


# ──────────────────────────────────────────────
# TestMomentumConstruction
# ──────────────────────────────────────────────

class TestMomentumConstruction:
    """动量策略构造与参数验证测试"""

    def test_default_params(self):
        """默认参数初始化"""
        s = Momentum()
        assert s.lookback_period == 20
        assert s.top_n == 5
        assert s.rebalance_days == 5
        assert s.frequency == "1d"
        assert s._last_rebalance is None
        assert s._current_holdings == set()

    def test_custom_params(self):
        """自定义参数初始化"""
        s = Momentum(
            name="MyMomentum",
            lookback_period=10,
            top_n=3,
            rebalance_days=3,
            frequency="1h",
        )
        assert s.name == "MyMomentum"
        assert s.lookback_period == 10
        assert s.top_n == 3
        assert s.rebalance_days == 3
        assert s.frequency == "1h"

    def test_invalid_top_n_zero_raises(self):
        """top_n=0 应该抛出 ValueError"""
        with pytest.raises(ValueError, match="top_n"):
            Momentum(top_n=0)

    def test_invalid_top_n_negative_raises(self):
        """top_n 为负数应该抛出 ValueError"""
        with pytest.raises(ValueError, match="top_n"):
            Momentum(top_n=-1)

    def test_invalid_lookback_period_raises(self):
        """lookback_period < 2 应该抛出 ValueError"""
        with pytest.raises(ValueError, match="lookback_period"):
            Momentum(lookback_period=1)

    def test_invalid_rebalance_days_raises(self):
        """rebalance_days < 1 应该抛出 ValueError"""
        with pytest.raises(ValueError, match="rebalance_days"):
            Momentum(rebalance_days=0)


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
        """数据不足时返回空列表（首次再平衡应该尝试，但 get_bars_cached 返回空）"""
        s = Momentum(lookback_period=20, top_n=2)
        portfolio_info = _make_portfolio_info(
            interested_codes=["000001.SZ", "000002.SZ"]
        )

        with patch.object(s, "get_bars_cached", return_value=[]):
            result = s.cal(portfolio_info, EventPriceUpdate())
            assert result == []

    def test_ranks_and_picks_top_momentum_stocks(self):
        """动量排名测试：3只股票取top 2，验证选中的是动量最高的"""
        s = Momentum(lookback_period=5, top_n=2, rebalance_days=1)
        now = datetime(2024, 1, 20)
        portfolio_info = _make_portfolio_info(
            now=now,
            interested_codes=["000001.SZ", "000002.SZ", "000003.SZ"],
        )

        # 000001.SZ: close 从 100 涨到 110 -> +10%
        # 000002.SZ: close 从 100 涨到 115 -> +15%  (最高)
        # 000003.SZ: close 从 100 涨到 95  -> -5%
        start = datetime(2024, 1, 1)

        def mock_get_bars(symbol, count, frequency, use_cache=True):
            if symbol == "000001.SZ":
                closes = [100.0, 102.0, 103.0, 107.0, 108.0, 110.0]
            elif symbol == "000002.SZ":
                closes = [100.0, 103.0, 106.0, 110.0, 112.0, 115.0]
            else:  # 000003.SZ
                closes = [100.0, 99.0, 98.0, 97.0, 96.0, 95.0]
            return _make_bars(closes, start)

        with patch.object(s, "get_bars_cached", side_effect=mock_get_bars):
            result = s.cal(portfolio_info, EventPriceUpdate())

        # 应该产生 2 个 LONG 信号（top 2 动量最高的股票）
        long_codes = {sig.code for sig in result if sig.direction == DIRECTION_TYPES.LONG}
        assert len(long_codes) == 2
        assert "000002.SZ" in long_codes  # +15% 最高动量
        assert "000001.SZ" in long_codes  # +10% 第二高
        assert "000003.SZ" not in long_codes  # -5% 不应该入选

    def test_skips_rebalance_if_not_enough_days_passed(self):
        """再平衡间隔未到时应返回空列表"""
        s = Momentum(lookback_period=5, top_n=2, rebalance_days=5)
        now = datetime(2024, 1, 20)
        portfolio_info = _make_portfolio_info(
            now=now,
            interested_codes=["000001.SZ", "000002.SZ"],
        )

        start = datetime(2024, 1, 1)

        def mock_get_bars(symbol, count, frequency, use_cache=True):
            closes = [100.0, 101.0, 102.0, 103.0, 104.0, 105.0]
            return _make_bars(closes, start)

        with patch.object(s, "get_bars_cached", side_effect=mock_get_bars):
            # 第一次调用 - 应该再平衡
            result1 = s.cal(portfolio_info, EventPriceUpdate())
            assert len(result1) > 0

            # 紧接着再调用（同一天）- 应该跳过
            result2 = s.cal(portfolio_info, EventPriceUpdate())
            assert result2 == []

    def test_generates_short_signals_for_exits(self):
        """持有股票跌出 top_n 时应生成 SHORT 信号"""
        s = Momentum(lookback_period=5, top_n=2, rebalance_days=1)
        now = datetime(2024, 1, 20)
        portfolio_info = _make_portfolio_info(
            now=now,
            interested_codes=["000001.SZ", "000002.SZ", "000003.SZ"],
        )

        start = datetime(2024, 1, 1)

        def mock_get_bars_phase1(symbol, count, frequency, use_cache=True):
            """第一阶段：000003.SZ 动量最高"""
            if symbol == "000001.SZ":
                closes = [100.0, 102.0, 103.0, 107.0, 108.0, 110.0]
            elif symbol == "000002.SZ":
                closes = [100.0, 103.0, 106.0, 110.0, 112.0, 115.0]
            else:
                closes = [100.0, 108.0, 112.0, 118.0, 122.0, 130.0]  # +30%
            return _make_bars(closes, start)

        # 第一次再平衡：选中 000003.SZ (+30%) 和 000002.SZ (+15%)
        with patch.object(s, "get_bars_cached", side_effect=mock_get_bars_phase1):
            result1 = s.cal(portfolio_info, EventPriceUpdate())
            assert len(result1) == 2
            long_codes_1 = {sig.code for sig in result1 if sig.direction == DIRECTION_TYPES.LONG}
            assert "000003.SZ" in long_codes_1

        # 模拟时间推进，超过再平衡间隔
        later_now = now + timedelta(days=s.rebalance_days + 1)
        portfolio_info["now"] = later_now

        def mock_get_bars_phase2(symbol, count, frequency, use_cache=True):
            """第二阶段：000003.SZ 动量暴跌"""
            if symbol == "000001.SZ":
                closes = [100.0, 102.0, 103.0, 107.0, 108.0, 120.0]  # +20%
            elif symbol == "000002.SZ":
                closes = [100.0, 103.0, 106.0, 110.0, 112.0, 125.0]  # +25%
            else:
                closes = [100.0, 98.0, 95.0, 92.0, 88.0, 85.0]  # -15%
            return _make_bars(closes, start)

        # 第二次再平衡：000003.SZ 跌出 top 2
        with patch.object(s, "get_bars_cached", side_effect=mock_get_bars_phase2):
            result2 = s.cal(portfolio_info, EventPriceUpdate())

        # 应该有 SHORT 信号卖出 000003.SZ
        short_codes = {sig.code for sig in result2 if sig.direction == DIRECTION_TYPES.SHORT}
        assert "000003.SZ" in short_codes

    def test_signals_contain_correct_portfolio_context(self):
        """信号应包含正确的 portfolio_id、engine_id、business_timestamp"""
        s = Momentum(lookback_period=5, top_n=1, rebalance_days=1)
        now = datetime(2024, 3, 15, 14, 30, 0)
        portfolio_info = _make_portfolio_info(
            now=now,
            interested_codes=["000001.SZ"],
        )
        portfolio_info["engine_id"] = "engine-xyz"
        portfolio_info["run_id"] = "run-abc"

        start = datetime(2024, 3, 1)

        def mock_get_bars(symbol, count, frequency, use_cache=True):
            closes = [100.0, 101.0, 102.0, 103.0, 104.0, 110.0]
            return _make_bars(closes, start)

        with patch.object(s, "get_bars_cached", side_effect=mock_get_bars):
            result = s.cal(portfolio_info, EventPriceUpdate())

        assert len(result) == 1
        sig = result[0]
        assert sig.portfolio_id == "portfolio-001"
        assert sig.engine_id == "engine-xyz"
        assert sig.run_id == "run-abc"
        assert sig.business_timestamp == now


# ──────────────────────────────────────────────
# test_reset_state
# ──────────────────────────────────────────────

class TestResetState:
    """状态重置测试"""

    def test_reset_state(self):
        """重置后 _last_rebalance 和 _current_holdings 应清空"""
        s = Momentum()
        s._last_rebalance = datetime(2024, 1, 1)
        s._current_holdings = {"000001.SZ", "000002.SZ"}

        s.reset_state()

        assert s._last_rebalance is None
        assert s._current_holdings == set()
