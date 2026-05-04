"""
边界测试 - 覆盖本次变更的边界条件

测试范围:
1. base_strategy: name=name 传递给 BacktestBase
2. time_controlled_engine: LIVE 模式走 else 分支
3. sim_broker: _get_field 额外边界
4. event_engine: _processed_events_count 与 _event_stats 同步
"""
import sys
import os
_path = os.path.join(os.path.dirname(__file__), '..', '..', '..')
if _path not in sys.path:
    sys.path.insert(0, _path)

import time
from decimal import Decimal
from unittest.mock import MagicMock, patch
import pytest

from ginkgo.trading.strategies.strategy_base import BaseStrategy
from ginkgo.trading.core.backtest_base import BacktestBase
from ginkgo.trading.brokers.sim_broker import SimBroker
from ginkgo.trading.engines.event_engine import EventEngine
from ginkgo.trading.engines.time_controlled_engine import TimeControlledEventEngine
from ginkgo.enums import EXECUTION_MODE, EVENT_TYPES, DIRECTION_TYPES, ORDER_TYPES


# ============================================================
# 1. BaseStrategy: name=name 传递给 BacktestBase
# ============================================================
class TestBaseStrategyNamePassThrough:
    """验证 name 参数正确传递到 BacktestBase"""

    def test_name_propagates_to_backtest_base(self):
        """name 应传递给 BacktestBase.__init__"""
        strategy = BaseStrategy(name="MyStrategy")
        assert strategy._name == "MyStrategy"
        assert strategy.name == "MyStrategy"

    def test_backtest_base_name_matches_strategy_name(self):
        """BacktestBase.name 属性应与 BaseStrategy.name 一致"""
        strategy = BaseStrategy(name="TestAlpha")
        assert isinstance(strategy, BacktestBase)
        assert strategy.name == "TestAlpha"

    def test_default_name(self):
        """默认 name 应为 'Strategy'"""
        strategy = BaseStrategy()
        assert strategy.name == "Strategy"


# ============================================================
# 2. TimeControlledEngine: LIVE 模式走 else 分支
# ============================================================
class TestTCEngineLiveModeBehavior:
    """验证非 BACKTEST 模式（LIVE）走 else 分支的行为"""

    def test_live_mode_uses_system_time_provider(self):
        """LIVE 模式应使用 SystemTimeProvider"""
        from ginkgo.trading.engines.time_controlled_engine import SystemTimeProvider
        engine = TimeControlledEventEngine(mode=EXECUTION_MODE.LIVE, name="live_test")
        engine._initialize_components()
        assert isinstance(engine._time_provider, SystemTimeProvider)

    def test_backtest_mode_uses_logical_time_provider(self):
        """BACKTEST 模式应使用 LogicalTimeProvider"""
        from ginkgo.trading.engines.time_controlled_engine import LogicalTimeProvider
        engine = TimeControlledEventEngine(mode=EXECUTION_MODE.BACKTEST, name="bt_test")
        engine._initialize_components()
        assert isinstance(engine._time_provider, LogicalTimeProvider)

    def test_live_mode_has_executor(self):
        """LIVE 模式应初始化 ThreadPoolExecutor"""
        engine = TimeControlledEventEngine(mode=EXECUTION_MODE.LIVE, name="live_exec")
        engine._initialize_components()
        assert engine._executor is not None

    def test_backtest_mode_no_executor(self):
        """BACKTEST 模式不应初始化 ThreadPoolExecutor"""
        engine = TimeControlledEventEngine(mode=EXECUTION_MODE.BACKTEST, name="bt_exec")
        engine._initialize_components()
        assert engine._executor is None

    def test_live_mode_advance_time_returns_false(self):
        """LIVE 模式 advance_time_to 应返回 False"""
        engine = TimeControlledEventEngine(mode=EXECUTION_MODE.LIVE, name="live_adv")
        engine._initialize_components()
        from datetime import datetime, timezone
        result = engine.advance_time_to(datetime(2024, 1, 1, tzinfo=timezone.utc))
        assert result is False

    def test_live_mode_should_advance_time_returns_true(self):
        """LIVE 模式 _should_advance_time 应返回 True"""
        engine = TimeControlledEventEngine(mode=EXECUTION_MODE.LIVE, name="live_cont")
        assert engine._should_advance_time() is True

    def test_backtest_mode_should_advance_time_depends_on_finish(self):
        """BACKTEST 模式未设置时间范围时应继续推进"""
        engine = TimeControlledEventEngine(mode=EXECUTION_MODE.BACKTEST, name="bt_adv")
        engine._initialize_components()
        # 未设置时间范围时 _is_backtest_finished 返回 False → _should_advance_time 返回 True
        assert engine._should_advance_time() is True

    def test_live_mode_is_backtest_finished_returns_false(self):
        """LIVE 模式 _is_backtest_finished 应返回 False"""
        engine = TimeControlledEventEngine(mode=EXECUTION_MODE.LIVE, name="live_fin")
        assert engine._is_backtest_finished() is False


# ============================================================
# 3. SimBroker: _get_field 额外边界
# ============================================================
class TestGetFieldBoundaryConditions:
    """_get_field 额外边界条件"""

    def test_object_with_zero_value(self):
        """属性值为 0 时应返回 0，不回退到 dict"""
        obj = MagicMock()
        obj.low = 0
        obj.high = 10
        assert SimBroker._get_field(obj, 'low', 99) == 0
        assert SimBroker._get_field(obj, 'high', 99) == 10

    def test_dict_with_zero_value(self):
        """dict 值为 0 时应返回 0"""
        assert SimBroker._get_field({'low': 0}, 'low', 99) == 0

    def test_dict_missing_key_with_none_default(self):
        """dict 缺少 key 且 default=None 时返回 None"""
        assert SimBroker._get_field({'high': 10}, 'low', None) is None

    def test_object_with_false_value(self):
        """属性值为 False 时应返回 False"""
        obj = MagicMock()
        obj.active = False
        assert SimBroker._get_field(obj, 'active', True) is False

    def test_dict_with_empty_string(self):
        """dict 值为空字符串时返回空字符串"""
        assert SimBroker._get_field({'code': ''}, 'code', 'default') == ''

    def test_int_input(self):
        """整数输入（无目标属性）返回默认值"""
        assert SimBroker._get_field(42, 'low', 0) == 0

    def test_list_input(self):
        """列表输入返回默认值"""
        assert SimBroker._get_field([1, 2, 3], 'low', 0) == 0

    def test_real_object_with_none_vs_missing(self):
        """区分真实对象的 None 属性和不存在的属性"""
        class SimpleObj:
            def __init__(self):
                self.limit_up = None

        obj = SimpleObj()
        # hasattr 返回 True, getattr 返回 None → 不走 dict 分支
        assert SimBroker._get_field(obj, 'limit_up', 99) is None
        # 不存在的属性
        assert SimBroker._get_field(obj, 'nonexistent', 99) == 99


# ============================================================
# 4. EventEngine: 计数器同步一致性
# ============================================================
class TestEventEngineCounterConsistency:
    """验证 _processed_events_count 与 _event_stats['completed_events'] 同步"""

    def test_counters_increment_together(self):
        """两个计数器应在每次成功处理后同步递增"""
        engine = EventEngine(name="sync_test")
        engine.start()
        try:
            for i in range(5):
                event = MagicMock()
                event.event_type = EVENT_TYPES.PRICEUPDATE
                engine.put(event)
            time.sleep(0.2)
            assert engine._processed_events_count == engine._event_stats['completed_events']
        finally:
            engine.stop()

    def test_failed_event_does_not_increment_completed(self):
        """失败事件不应递增 completed_events"""
        engine = EventEngine(name="fail_test")
        handler_called = False

        def failing_handler(event):
            nonlocal handler_called
            handler_called = True
            raise RuntimeError("Test failure")

        engine.start()
        engine.register(EVENT_TYPES.PRICEUPDATE, failing_handler)
        try:
            event = MagicMock()
            event.event_type = EVENT_TYPES.PRICEUPDATE
            engine.put(event)
            time.sleep(0.2)
            assert handler_called
            assert engine._event_stats['completed_events'] == 0
            assert engine._event_stats['failed_events'] == 1
            assert engine._processed_events_count == 0
        finally:
            engine.stop()

    def test_processing_start_time_set_on_first_event(self):
        """_processing_start_time 应在第一个事件处理时设置"""
        engine = EventEngine(name="start_time_test")
        engine.start()
        try:
            assert engine._processing_start_time is None
            event = MagicMock()
            event.event_type = EVENT_TYPES.PRICEUPDATE
            engine.put(event)
            time.sleep(0.2)
            assert engine._processing_start_time is not None
        finally:
            engine.stop()

    def test_processing_rate_calculation(self):
        """processing_rate 应基于 _processing_start_time 和 _processed_events_count"""
        engine = EventEngine(name="rate_test")
        engine.start()
        try:
            for i in range(3):
                event = MagicMock()
                event.event_type = EVENT_TYPES.PRICEUPDATE
                engine.put(event)
            time.sleep(0.3)
            stats = engine.get_event_stats()
            assert stats.processed_events == 3
            assert stats.processing_rate > 0
        finally:
            engine.stop()
