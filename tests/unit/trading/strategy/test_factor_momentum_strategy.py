"""FactorMomentumStrategy TDD -- #6791 Phase 0 tracer

验证 BaseStrategy factor_reader 钩子的端到端用法:
策略 cal() 读 PIT 因子值,据此发信号,且用 portfolio_info["now"] 作 at_time(不读未来)。
"""
import pytest
from datetime import datetime
from unittest.mock import MagicMock

from ginkgo.trading.strategies.factor_momentum import FactorMomentumStrategy
from ginkgo.enums import DIRECTION_TYPES


def _set_context(strategy):
    """复用 test_base_strategy 的 context helper。"""
    strategy._context = type('C', (), {
        'engine_id': 'e', 'portfolio_id': 'p', 'task_id': 't',
    })()


def _event(code="000001.SZ", ts=None):
    return type('E', (), {'code': code, 'timestamp': ts or datetime(2024, 6, 1)})()


@pytest.mark.unit
class TestFactorMomentumStrategy:
    def test_cal_emits_long_when_factor_above_buy_threshold(self):
        strat = FactorMomentumStrategy(buy_threshold=0.0, sell_threshold=-1.0)
        _set_context(strat)
        reader = MagicMock()
        reader.get_factor_value.return_value = 0.05  # ROC5 = +5%
        strat.bind_factor_reader(reader)

        signals = strat.cal({"now": datetime(2024, 6, 1)}, _event())

        assert len(signals) == 1
        assert signals[0].direction == DIRECTION_TYPES.LONG
        reader.get_factor_value.assert_called_once_with("000001.SZ", "ROC5", datetime(2024, 6, 1))

    def test_cal_emits_short_when_factor_below_sell_threshold(self):
        strat = FactorMomentumStrategy(buy_threshold=1.0, sell_threshold=0.0)
        _set_context(strat)
        reader = MagicMock()
        reader.get_factor_value.return_value = -0.05
        strat.bind_factor_reader(reader)

        signals = strat.cal({"now": datetime(2024, 6, 1)}, _event())

        assert len(signals) == 1
        assert signals[0].direction == DIRECTION_TYPES.SHORT

    def test_cal_no_signal_when_factor_missing(self):
        strat = FactorMomentumStrategy()
        _set_context(strat)
        reader = MagicMock()
        reader.get_factor_value.return_value = None
        strat.bind_factor_reader(reader)

        assert strat.cal({"now": datetime(2024, 6, 1)}, _event()) == []

    def test_cal_uses_portfolio_now_as_pit_time(self):
        """PIT: at_time 取 portfolio_info['now'](回测当前时间),优先于 event.timestamp。"""
        strat = FactorMomentumStrategy()
        _set_context(strat)
        reader = MagicMock()
        reader.get_factor_value.return_value = None
        strat.bind_factor_reader(reader)

        now = datetime(2024, 6, 1)
        strat.cal({"now": now}, _event(ts=datetime(2024, 5, 1)))

        called_time = reader.get_factor_value.call_args.args[2]
        assert called_time == now

    def test_cal_falls_back_to_event_timestamp_without_portfolio_now(self):
        """portfolio_info 无 'now' 时,fallback event.timestamp(仍 PIT)。"""
        strat = FactorMomentumStrategy()
        _set_context(strat)
        reader = MagicMock()
        reader.get_factor_value.return_value = None
        strat.bind_factor_reader(reader)

        ts = datetime(2024, 5, 1)
        strat.cal({}, _event(ts=ts))

        assert reader.get_factor_value.call_args.args[2] == ts

    def test_cal_no_code_returns_empty(self):
        strat = FactorMomentumStrategy()
        _set_context(strat)
        strat.bind_factor_reader(MagicMock())
        event_no_code = type('E', (), {'timestamp': datetime(2024, 6, 1)})()
        assert strat.cal({"now": datetime(2024, 6, 1)}, event_no_code) == []
