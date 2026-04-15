"""
MeanReversion 均值回归策略 TDD 测试

测试 RSI 阈值交叉信号生成逻辑：
- RSI 下穿超卖阈值 → 买入信号 (LONG)
- RSI 上穿超买阈值 → 卖出信号 (SHORT)
"""

import pytest
from unittest.mock import MagicMock, patch
from datetime import datetime

from ginkgo.trading.strategies.mean_reversion import MeanReversion
from ginkgo.trading.events.price_update import EventPriceUpdate
from ginkgo.enums import DIRECTION_TYPES


def _make_bar(close_price):
    """创建模拟 bar 对象，只有 close 属性"""
    bar = MagicMock()
    bar.close = close_price
    return bar


def _make_portfolio_info(portfolio_id="test_portfolio", now=None):
    """创建模拟 portfolio_info 字典"""
    return {
        "uuid": portfolio_id,
        "now": now or datetime(2025, 1, 15),
    }


def _make_price_event(code="000001.SZ", timestamp=None, price=10.0):
    """创建模拟 EventPriceUpdate"""
    event = MagicMock(spec=EventPriceUpdate)
    event.code = code
    event.timestamp = timestamp or datetime(2025, 1, 15)
    event.transaction_price = price
    return event


def _make_strategy(engine_id="test_engine", run_id="test_run", **kwargs):
    """创建策略并注入 context"""
    strategy = MeanReversion(**kwargs)
    strategy._context = type('C', (), {
        'engine_id': engine_id,
        'portfolio_id': 'test_portfolio',
        'run_id': run_id,
    })()
    return strategy


# ============================================================
# RSI 计算辅助
# ============================================================

def _generate_rsi_series(rsi_period, target_rsi, n_bars):
    """
    生成一组收盘价，使得最后一根 bar 的 RSI 接近 target_rsi。

    简化方法：通过控制涨跌比例来近似 RSI。
    RSI = 100 - 100/(1 + RS)，其中 RS = avg_gain / avg_loss。
    """
    # 对于目标 RSI，反推 RS
    # RSI = 100 - 100/(1+RS) => RS = RSI/(100-RSI)
    if target_rsi >= 100:
        rs = float('inf')
    elif target_rsi <= 0:
        rs = 0.0
    else:
        rs = target_rsi / (100.0 - target_rsi)

    prices = [100.0]
    # 生成 rsi_period 个变化量，使得 avg_gain / avg_loss ≈ rs
    # 简单做法：交替产生 gain 和 loss
    if rs == float('inf'):
        # 全涨
        for _ in range(n_bars - 1):
            prices.append(prices[-1] + 1.0)
    elif rs == 0:
        # 全跌
        for _ in range(n_bars - 1):
            prices.append(prices[-1] - 1.0)
    else:
        # 部分涨部分跌，使得 RS ≈ rs
        # avg_gain = gain_avg, avg_loss = loss_avg, RS = gain_avg/loss_avg
        gain_step = 1.0
        loss_step = rs * 1.0  # 这样 gain/loss = 1/rs... 不对
        # RS = avg_gain / avg_loss = rs
        # 如果 num_gain 次涨 gain_step，num_loss 次跌 loss_step
        # avg_gain = num_gain * gain_step / rsi_period
        # avg_loss = num_loss * loss_step / rsi_period
        # RS = num_gain * gain_step / (num_loss * loss_step)
        # 设 gain_step = loss_step = 1, 则 RS = num_gain / num_loss
        # num_gain / num_loss = rs
        # num_gain + num_loss = rsi_period
        # num_gain = rs * num_loss
        # rs * num_loss + num_loss = rsi_period
        # num_loss = rsi_period / (1 + rs)
        num_loss = int(rsi_period / (1.0 + rs))
        num_gain = rsi_period - num_loss
        # 但因为取整可能不精确，先凑满 rsi_period 次
        # 然后补 n_bars - 1 - rsi_period 次中性变化(不变)
        import math
        num_loss = max(1, num_loss)
        num_gain = max(1, num_gain)
        # 确保 num_gain + num_loss <= rsi_period
        while num_gain + num_loss > rsi_period:
            if num_gain > num_loss:
                num_gain -= 1
            else:
                num_loss -= 1

        changes = [1.0] * num_gain + [-1.0] * num_loss
        # 打乱
        import random
        random.seed(42)
        random.shuffle(changes)

        for i in range(len(changes)):
            prices.append(prices[-1] + changes[i])

        # 补齐剩余的 bar
        while len(prices) < n_bars:
            prices.append(prices[-1])  # 平盘

    return [_make_bar(p) for p in prices]


@pytest.mark.unit
class TestMeanReversionConstruction:
    """1. 构造和初始化测试"""

    def test_default_params(self):
        """默认参数：rsi_period=14, oversold=30, overbought=70, frequency='1d'"""
        strategy = MeanReversion()
        assert strategy.rsi_period == 14
        assert strategy.oversold == 30
        assert strategy.overbought == 70
        assert strategy.frequency == '1d'

    def test_custom_params(self):
        """自定义参数"""
        strategy = MeanReversion(
            name="MyMR",
            rsi_period=10,
            oversold=20,
            overbought=80,
            frequency='1h',
        )
        assert strategy.name == "MyMR"
        assert strategy.rsi_period == 10
        assert strategy.oversold == 20
        assert strategy.overbought == 80
        assert strategy.frequency == '1h'

    def test_invalid_params_overbought_not_greater_than_oversold(self):
        """overbought 必须 > oversold，否则 ValueError"""
        with pytest.raises(ValueError, match="overbought.*oversold"):
            MeanReversion(oversold=70, overbought=30)

    def test_invalid_params_equal_thresholds(self):
        """overbought == oversold 也不行"""
        with pytest.raises(ValueError):
            MeanReversion(oversold=50, overbought=50)

    def test_invalid_rsi_period_too_small(self):
        """rsi_period 必须 >= 2"""
        with pytest.raises(ValueError):
            MeanReversion(rsi_period=1)


@pytest.mark.unit
class TestMeanReversionCal:
    """2. cal() 信号生成测试"""

    def test_returns_empty_for_non_price_event(self):
        """非 EventPriceUpdate 事件返回空列表"""
        strategy = _make_strategy()
        event = MagicMock()  # 不是 EventPriceUpdate
        result = strategy.cal(_make_portfolio_info(), event)
        assert result == []

    def test_returns_empty_when_insufficient_data(self):
        """数据不足时返回空列表"""
        strategy = _make_strategy(rsi_period=14)
        event = _make_price_event()
        bars = [_make_bar(10.0)] * 5  # 只有 5 根 bar，不够 15 根

        with patch.object(strategy, 'get_bars_cached', return_value=bars):
            result = strategy.cal(_make_portfolio_info(), event)
        assert result == []

    def test_returns_empty_on_first_call_no_prev_rsi(self):
        """首次调用没有 prev_rsi，不产生信号"""
        strategy = _make_strategy(rsi_period=5, oversold=30, overbought=70)
        event = _make_price_event()
        # 需要 rsi_period + 1 = 6 根 bar
        bars = _generate_rsi_series(rsi_period=5, target_rsi=20, n_bars=6)

        with patch.object(strategy, 'get_bars_cached', return_value=bars):
            result = strategy.cal(_make_portfolio_info(), event)
        assert result == []

    def test_generates_buy_signal_when_rsi_crosses_below_oversold(self):
        """RSI 从上方穿越超卖线 → 买入信号 (LONG)"""
        strategy = _make_strategy(rsi_period=5, oversold=30, overbought=70)
        portfolio_info = _make_portfolio_info()
        event = _make_price_event()

        # 第一次调用：RSI = 40（中性区），不产生信号
        bars_above = _generate_rsi_series(rsi_period=5, target_rsi=40, n_bars=6)
        with patch.object(strategy, 'get_bars_cached', return_value=bars_above):
            result1 = strategy.cal(portfolio_info, event)
        assert result1 == []

        # 第二次调用：RSI = 20（穿越到超卖区以下），产生买入信号
        bars_below = _generate_rsi_series(rsi_period=5, target_rsi=20, n_bars=6)
        with patch.object(strategy, 'get_bars_cached', return_value=bars_below):
            result2 = strategy.cal(portfolio_info, event)

        assert len(result2) == 1
        assert result2[0].direction == DIRECTION_TYPES.LONG
        assert result2[0].code == "000001.SZ"
        assert result2[0].portfolio_id == "test_portfolio"
        assert result2[0].engine_id == "test_engine"
        assert result2[0].run_id == "test_run"

    def test_generates_sell_signal_when_rsi_crosses_above_overbought(self):
        """RSI 从下方穿越超买线 → 卖出信号 (SHORT)"""
        strategy = _make_strategy(rsi_period=5, oversold=30, overbought=70)
        portfolio_info = _make_portfolio_info()
        event = _make_price_event()

        # 第一次调用：RSI = 60（中性区）
        bars_below = _generate_rsi_series(rsi_period=5, target_rsi=60, n_bars=6)
        with patch.object(strategy, 'get_bars_cached', return_value=bars_below):
            result1 = strategy.cal(portfolio_info, event)
        assert result1 == []

        # 第二次调用：RSI = 80（穿越到超买区以上），产生卖出信号
        bars_above = _generate_rsi_series(rsi_period=5, target_rsi=80, n_bars=6)
        with patch.object(strategy, 'get_bars_cached', return_value=bars_above):
            result2 = strategy.cal(portfolio_info, event)

        assert len(result2) == 1
        assert result2[0].direction == DIRECTION_TYPES.SHORT
        assert result2[0].code == "000001.SZ"

    def test_no_signal_when_rsi_stays_in_neutral_zone(self):
        """RSI 始终在中性区，不产生信号"""
        strategy = _make_strategy(rsi_period=5, oversold=30, overbought=70)
        portfolio_info = _make_portfolio_info()
        event = _make_price_event()

        # 两次调用 RSI 都在 50 附近
        bars_neutral = _generate_rsi_series(rsi_period=5, target_rsi=50, n_bars=6)
        with patch.object(strategy, 'get_bars_cached', return_value=bars_neutral):
            result1 = strategy.cal(portfolio_info, event)
        assert result1 == []

        bars_neutral2 = _generate_rsi_series(rsi_period=5, target_rsi=55, n_bars=6)
        with patch.object(strategy, 'get_bars_cached', return_value=bars_neutral2):
            result2 = strategy.cal(portfolio_info, event)
        assert result2 == []

    def test_no_signal_when_rsi_stays_below_oversold(self):
        """RSI 已经在超卖区，第二次依然在超卖区，不产生信号（无穿越）"""
        strategy = _make_strategy(rsi_period=5, oversold=30, overbought=70)
        portfolio_info = _make_portfolio_info()
        event = _make_price_event()

        bars_low1 = _generate_rsi_series(rsi_period=5, target_rsi=20, n_bars=6)
        with patch.object(strategy, 'get_bars_cached', return_value=bars_low1):
            result1 = strategy.cal(portfolio_info, event)
        assert result1 == []

        bars_low2 = _generate_rsi_series(rsi_period=5, target_rsi=15, n_bars=6)
        with patch.object(strategy, 'get_bars_cached', return_value=bars_low2):
            result2 = strategy.cal(portfolio_info, event)
        assert result2 == []

    def test_no_signal_when_rsi_stays_above_overbought(self):
        """RSI 已经在超买区，第二次依然在超买区，不产生信号（无穿越）"""
        strategy = _make_strategy(rsi_period=5, oversold=30, overbought=70)
        portfolio_info = _make_portfolio_info()
        event = _make_price_event()

        bars_high1 = _generate_rsi_series(rsi_period=5, target_rsi=80, n_bars=6)
        with patch.object(strategy, 'get_bars_cached', return_value=bars_high1):
            result1 = strategy.cal(portfolio_info, event)
        assert result1 == []

        bars_high2 = _generate_rsi_series(rsi_period=5, target_rsi=85, n_bars=6)
        with patch.object(strategy, 'get_bars_cached', return_value=bars_high2):
            result2 = strategy.cal(portfolio_info, event)
        assert result2 == []

    def test_buy_signal_includes_reason_with_rsi_value(self):
        """买入信号的 reason 包含 RSI 值"""
        strategy = _make_strategy(rsi_period=5, oversold=30, overbought=70)
        portfolio_info = _make_portfolio_info()
        event = _make_price_event()

        # 第一次：RSI 在超卖线以上
        bars_above = _generate_rsi_series(rsi_period=5, target_rsi=35, n_bars=6)
        with patch.object(strategy, 'get_bars_cached', return_value=bars_above):
            strategy.cal(portfolio_info, event)

        # 第二次：RSI 穿越
        bars_below = _generate_rsi_series(rsi_period=5, target_rsi=20, n_bars=6)
        with patch.object(strategy, 'get_bars_cached', return_value=bars_below):
            result = strategy.cal(portfolio_info, event)

        assert len(result) == 1
        assert "RSI" in result[0].reason
        assert result[0].reason != ""


@pytest.mark.unit
class TestMeanReversionResetState:
    """3. 状态重置测试"""

    def test_reset_state_clears_cache(self):
        """reset_state() 清除 RSI 历史缓存"""
        strategy = _make_strategy(rsi_period=5)
        portfolio_info = _make_portfolio_info()
        event = _make_price_event()

        bars = _generate_rsi_series(rsi_period=5, target_rsi=50, n_bars=6)
        with patch.object(strategy, 'get_bars_cached', return_value=bars):
            strategy.cal(portfolio_info, event)

        # 确认有状态
        assert len(strategy._prev_rsi) == 1

        # 重置
        strategy.reset_state()

        # 验证缓存已清空
        assert len(strategy._prev_rsi) == 0
