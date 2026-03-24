# Upstream: BaseEngine (回测引擎)
# Downstream: pytest (测试框架)
# Role: 验证回测过程中 trace_id 的统一传播

import pytest
from unittest.mock import Mock, patch
from uuid import uuid4
from datetime import datetime

from ginkgo.libs import GLOG
from ginkgo.trading.engines.event_engine import EventEngine
from ginkgo.enums import EXECUTION_MODE, ENGINESTATUS_TYPES


class TestBacktestTraceIdPropagation:
    """验证回测引擎 trace_id 传播"""

    def test_engine_generates_trace_id_on_start(self):
        """测试引擎启动时生成 trace_id"""
        engine = EventEngine(
            name="TestEngine",
            mode=EXECUTION_MODE.BACKTEST
        )

        # 启动引擎（会生成 run_id 和 trace_id）
        engine.start()

        # 验证 trace_id 已设置
        trace_id = GLOG.get_trace_id()
        assert trace_id is not None, "trace_id 应该在引擎启动后设置"
        assert trace_id == engine.run_id, "trace_id 应该等于 run_id"

        # 清理
        engine.stop()
        assert GLOG.get_trace_id() is None, "trace_id 应该在停止后清理"

    def test_components_inherit_trace_id(self):
        """测试组件自动继承 trace_id"""
        engine = EventEngine(
            name="TestEngine",
            mode=EXECUTION_MODE.BACKTEST
        )

        # 启动引擎
        engine.start()
        expected_trace_id = engine.run_id

        # 模拟组件方法
        def simulate_strategy_cal():
            return GLOG.get_trace_id()

        def simulate_portfolio_on_order():
            return GLOG.get_trace_id()

        def simulate_risk_check():
            return GLOG.get_trace_id()

        # 验证所有组件获得相同的 trace_id
        assert simulate_strategy_cal() == expected_trace_id
        assert simulate_portfolio_on_order() == expected_trace_id
        assert simulate_risk_check() == expected_trace_id

        engine.stop()

    def test_multiple_backtests_have_different_trace_ids(self):
        """测试不同回测有不同 trace_id"""
        # 第一次回测
        engine1 = EventEngine(
            name="TestEngine1",
            mode=EXECUTION_MODE.BACKTEST
        )
        engine1.start()
        trace_id_1 = GLOG.get_trace_id()
        engine1.stop()

        # 第二次回测（使用新引擎实例）
        engine2 = EventEngine(
            name="TestEngine2",
            mode=EXECUTION_MODE.BACKTEST
        )
        engine2.start()
        trace_id_2 = GLOG.get_trace_id()
        engine2.stop()

        # 验证两次回测的 trace_id 不同
        assert trace_id_1 != trace_id_2, "不同回测应该有不同的 trace_id"

    def test_trace_id_in_log_output(self):
        """测试日志输出包含 trace_id"""
        from ginkgo.libs.core.logger import ecs_processor

        engine = EventEngine(
            name="TestEngine",
            mode=EXECUTION_MODE.BACKTEST
        )

        engine.start()
        expected_trace_id = engine.run_id

        # 模拟日志事件
        event_dict = {
            'event': 'Test message',
            'level': 'info',
            'logger_name': 'test'
        }

        # 通过 ecs_processor 处理
        result = ecs_processor(None, None, event_dict)

        # 验证 trace 字段存在且值正确
        assert 'trace' in result, "日志应该包含 trace 字段"
        assert result['trace']['id'] == expected_trace_id, "trace ID 应该匹配 run_id"

        engine.stop()

    def test_nested_function_calls_propagate_trace_id(self):
        """测试嵌套函数调用自动传播 trace_id"""
        engine = EventEngine(
            name="TestEngine",
            mode=EXECUTION_MODE.BACKTEST
        )

        engine.start()
        expected_trace_id = engine.run_id

        # 深层嵌套调用
        def level_3():
            return GLOG.get_trace_id()

        def level_2():
            return level_3()

        def level_1():
            return level_2()

        # 验证深层嵌套仍能获得 trace_id
        assert level_1() == expected_trace_id

        engine.stop()
