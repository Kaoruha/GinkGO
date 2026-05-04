"""
性能: 273MB RSS, 2.52s, 16 tests [PASS]
"""

import unittest
from datetime import datetime, timedelta
from unittest.mock import Mock, patch, MagicMock
from decimal import Decimal

from ginkgo.trading.strategies.strategy_base import BaseStrategy
from ginkgo.entities import Signal
from ginkgo.entities import Bar
from ginkgo.trading.portfolios import PortfolioT1Backtest
from ginkgo.trading.selectors import FixedSelector
from ginkgo.trading.sizers import FixedSizer
from ginkgo.trading.analysis.analyzers.net_value import NetValue
from ginkgo.enums import DIRECTION_TYPES, RECORDSTAGE_TYPES, SOURCE_TYPES


def _make_signal(code="000001.SZ", direction=DIRECTION_TYPES.LONG):
    """Helper to create a valid Signal with all required fields."""
    return Signal(
        portfolio_id="test_portfolio",
        engine_id="test_engine",
        task_id="test_run",
        code=code,
        direction=direction,
        reason="test",
        source=SOURCE_TYPES.OTHER,
    )


class StrategyIntegrationTest(unittest.TestCase):
    """
    策略集成测试 - 测试策略与其他组件的集成工作
    """

    def setUp(self):
        """初始化测试环境"""
        self.test_time = datetime(2024, 1, 1, 10, 0, 0)

        # 创建基础策略
        self.strategy = BaseStrategy("test_strategy")
        self.strategy.set_business_timestamp(self.test_time)

        # 创建投资组合
        self.portfolio = PortfolioT1Backtest()
        self.portfolio.set_portfolio_name("integration_test_portfolio")

        # 创建基础组件
        self.selector = FixedSelector("test_selector", '["000001.SZ", "000002.SZ"]')
        self.sizer = FixedSizer("test_sizer", "100")
        self.analyzer = NetValue("test_net_value")

    def test_strategy_base_initialization(self):
        """测试策略基类初始化"""
        strategy = BaseStrategy("init_test")

        # 验证基本属性
        self.assertEqual(strategy.name, "init_test")
        self.assertTrue(hasattr(strategy, "_data_feeder"))
        self.assertIsNone(strategy._data_feeder)

    def test_strategy_cal_default_returns_empty(self):
        """测试策略基类cal方法默认返回空列表"""
        result = self.strategy.cal({}, Mock())
        self.assertEqual(result, [])

    def test_concrete_strategy_implementation(self):
        """测试具体策略实现"""

        class TestStrategy(BaseStrategy):
            def __init__(self, name):
                super().__init__(name)
                self.signals_generated = []

            def cal(self, portfolio_info, event):
                # 生成测试信号
                signal = _make_signal()
                self.signals_generated.append(signal)
                return [signal]

        concrete_strategy = TestStrategy("concrete_test")
        concrete_strategy.set_business_timestamp(self.test_time)

        # 调用cal方法
        signals = concrete_strategy.cal({}, Mock())

        # 验证信号生成
        self.assertIsInstance(signals, list)
        self.assertEqual(len(signals), 1)
        self.assertIsInstance(signals[0], Signal)
        self.assertEqual(signals[0].code, "000001.SZ")

    def test_strategy_portfolio_integration(self):
        """测试策略与投资组合的集成"""

        class IntegrationStrategy(BaseStrategy):
            def cal(self, portfolio_info, event):
                return [_make_signal()]

        strategy = IntegrationStrategy("portfolio_integration")
        strategy.set_business_timestamp(self.test_time)

        # 将策略添加到投资组合
        self.portfolio.add_strategy(strategy)

        # 验证策略已添加
        self.assertIn(strategy, self.portfolio.strategies)
        self.assertEqual(len(self.portfolio.strategies), 1)

    def test_strategy_selector_integration(self):
        """测试策略与选择器的集成"""

        # 绑定选择器到投资组合
        self.portfolio.bind_selector(self.selector)

        # 验证选择器绑定 (portfolio使用selectors复数形式)
        self.assertIn(self.selector, self.portfolio.selectors)

        # 测试选择器功能
        selected_codes = self.selector.pick(time=self.test_time)
        expected_codes = ["000001.SZ", "000002.SZ"]

        self.assertEqual(selected_codes, expected_codes)

    def test_strategy_sizer_integration(self):
        """测试策略与仓位管理器的集成"""

        # 绑定仓位管理器到投资组合
        self.portfolio.bind_sizer(self.sizer)

        # 验证仓位管理器绑定
        self.assertEqual(self.portfolio.sizer, self.sizer)

        # 测试仓位管理器功能
        self.assertEqual(self.sizer.volume, 100)

    def test_strategy_analyzer_integration(self):
        """测试策略与分析器的集成"""

        # 添加分析器到投资组合
        self.portfolio.add_analyzer(self.analyzer)

        # 验证分析器添加
        self.assertIn("test_net_value", self.portfolio.analyzers)
        self.assertEqual(self.portfolio.analyzers["test_net_value"], self.analyzer)

    def test_full_strategy_workflow(self):
        """测试完整的策略工作流程"""

        class WorkflowStrategy(BaseStrategy):
            def __init__(self, name):
                super().__init__(name)
                self.execution_count = 0

            def cal(self, portfolio_info, event):
                self.execution_count += 1
                # 根据简单逻辑生成信号
                if self.execution_count % 2 == 1:  # 奇数次执行时买入
                    return [_make_signal()]
                return []

        # 设置完整的工作流程
        strategy = WorkflowStrategy("workflow_test")
        strategy.set_business_timestamp(self.test_time)

        # 配置投资组合
        self.portfolio.add_strategy(strategy)
        self.portfolio.bind_selector(self.selector)
        self.portfolio.bind_sizer(self.sizer)
        self.portfolio.add_analyzer(self.analyzer)

        # 验证配置完整性
        self.assertTrue(self.portfolio.is_all_set())

        # 模拟策略执行
        signals = strategy.cal({}, Mock())

        # 验证第一次执行产生信号
        self.assertEqual(len(signals), 1)
        self.assertEqual(signals[0].code, "000001.SZ")
        self.assertEqual(signals[0].direction, DIRECTION_TYPES.LONG)

        # 模拟第二次执行
        signals = strategy.cal({}, Mock())
        self.assertEqual(len(signals), 0)  # 第二次不产生信号

    def test_strategy_time_synchronization(self):
        """测试策略与其他组件的时间同步"""

        # 设置不同的时间点
        times = [
            datetime(2024, 1, 1, 9, 30, 0),
            datetime(2024, 1, 1, 10, 0, 0),
            datetime(2024, 1, 1, 10, 30, 0),
        ]

        for test_time in times:
            # 更新所有组件的时间 (使用set_business_timestamp)
            self.strategy.set_business_timestamp(test_time)
            self.selector.set_business_timestamp(test_time)
            self.sizer.set_business_timestamp(test_time)
            self.analyzer.set_business_timestamp(test_time)

            # 验证时间同步 (使用business_timestamp属性)
            self.assertEqual(self.strategy.business_timestamp, test_time)
            self.assertEqual(self.selector.business_timestamp, test_time)
            self.assertEqual(self.sizer.business_timestamp, test_time)
            self.assertEqual(self.analyzer.business_timestamp, test_time)

    def test_strategy_error_propagation(self):
        """测试策略错误传播机制"""

        class ErrorStrategy(BaseStrategy):
            def __init__(self, name):
                super().__init__(name)
                self.should_error = False

            def cal(self, portfolio_info, event):
                if self.should_error:
                    raise RuntimeError("Strategy calculation error")
                return []

        error_strategy = ErrorStrategy("error_test")
        error_strategy.should_error = True

        # 策略错误应该能被捕获
        with self.assertRaises(RuntimeError):
            error_strategy.cal({}, Mock())

    def test_strategy_signal_validation(self):
        """测试策略信号验证"""

        # Signal构造函数会验证所有必需字段
        valid_signal = _make_signal()
        self.assertEqual(valid_signal.code, "000001.SZ")
        self.assertEqual(valid_signal.direction, DIRECTION_TYPES.LONG)

        # 创建无效信号（空代码）应该抛出异常
        with self.assertRaises(Exception):
            Signal(
                portfolio_id="test_portfolio",
                engine_id="test_engine",
                task_id="test_run",
                code="",  # 空代码
                direction=DIRECTION_TYPES.LONG,
                reason="test",
                source=SOURCE_TYPES.OTHER,
            )

        # 创建无效信号（空portfolio_id）应该抛出异常
        with self.assertRaises(Exception):
            Signal(
                portfolio_id="",  # 空portfolio_id
                engine_id="test_engine",
                task_id="test_run",
                code="000001.SZ",
                direction=DIRECTION_TYPES.LONG,
                reason="test",
                source=SOURCE_TYPES.OTHER,
            )

    def test_strategy_performance_tracking(self):
        """测试策略性能跟踪"""

        class PerformanceStrategy(BaseStrategy):
            def __init__(self, name):
                super().__init__(name)
                self.call_count = 0
                self.total_signals = 0

            def cal(self, portfolio_info, event):
                self.call_count += 1

                # 模拟不同的信号生成模式
                if self.call_count % 3 == 0:
                    signals = []
                else:
                    signal = _make_signal(code=f"00000{self.call_count % 2 + 1}.SZ")
                    signals = [signal]

                self.total_signals += len(signals)
                return signals

        perf_strategy = PerformanceStrategy("performance_test")
        perf_strategy.set_business_timestamp(self.test_time)

        # 执行多次策略计算
        total_signals = 0
        for i in range(10):
            signals = perf_strategy.cal({}, Mock())
            total_signals += len(signals)

        # 验证性能统计
        self.assertEqual(perf_strategy.call_count, 10)
        self.assertEqual(perf_strategy.total_signals, total_signals)

        # 预期模式：第3,6,9次不产生信号，其余7次产生信号
        expected_signals = 7
        self.assertEqual(total_signals, expected_signals)

    def test_strategy_data_dependency(self):
        """测试策略数据依赖管理"""

        class DataDependentStrategy(BaseStrategy):
            def __init__(self, name):
                super().__init__(name)
                self.required_data_fields = ["close", "volume", "high", "low"]
                self.data_cache = {}

            def cal(self, portfolio_info, event):
                # 模拟数据依赖检查
                for field in self.required_data_fields:
                    if field not in self.data_cache:
                        # 如果缺少必要数据，不生成信号
                        return []

                # 有完整数据时生成信号
                return [_make_signal()]

            def update_data(self, field, value):
                self.data_cache[field] = value

        data_strategy = DataDependentStrategy("data_dependent")
        data_strategy.set_business_timestamp(self.test_time)

        # 没有数据时不应产生信号
        signals = data_strategy.cal({}, Mock())
        self.assertEqual(len(signals), 0)

        # 添加部分数据，仍不应产生信号
        data_strategy.update_data("close", 10.5)
        data_strategy.update_data("volume", 1000)
        signals = data_strategy.cal({}, Mock())
        self.assertEqual(len(signals), 0)

        # 添加完整数据后应产生信号
        data_strategy.update_data("high", 11.0)
        data_strategy.update_data("low", 10.0)
        signals = data_strategy.cal({}, Mock())
        self.assertEqual(len(signals), 1)

    def test_strategy_resource_cleanup(self):
        """测试策略资源清理"""
        strategies = []

        # 创建多个策略实例
        for i in range(10):
            strategy = BaseStrategy(f"cleanup_test_{i}")
            strategy.set_business_timestamp(self.test_time)
            strategies.append(strategy)

        # 验证所有策略都正常工作（基类cal默认返回空列表）
        for strategy in strategies:
            self.assertIsNotNone(strategy.name)
            self.assertEqual(strategy.cal({}, Mock()), [])

        # 清理引用
        strategies.clear()

        # 原始策略应该仍然正常工作
        self.assertEqual(self.strategy.name, "test_strategy")
        self.assertEqual(self.strategy.cal({}, Mock()), [])

    def test_strategy_inheritance_and_polymorphism(self):
        """测试策略继承和多态性"""

        class LongOnlyStrategy(BaseStrategy):
            def cal(self, portfolio_info, event):
                return [_make_signal(direction=DIRECTION_TYPES.LONG)]

        class ShortOnlyStrategy(BaseStrategy):
            def cal(self, portfolio_info, event):
                return [_make_signal(direction=DIRECTION_TYPES.SHORT)]

        strategies = [
            LongOnlyStrategy("long_only"),
            ShortOnlyStrategy("short_only")
        ]

        # 测试多态行为
        for strategy in strategies:
            strategy.set_business_timestamp(self.test_time)
            signals = strategy.cal({}, Mock())

            self.assertEqual(len(signals), 1)
            self.assertEqual(signals[0].code, "000001.SZ")

            # 验证不同的方向
            if isinstance(strategy, LongOnlyStrategy):
                self.assertEqual(signals[0].direction, DIRECTION_TYPES.LONG)
            else:
                self.assertEqual(signals[0].direction, DIRECTION_TYPES.SHORT)

    def test_portfolio_complete_workflow(self):
        """测试投资组合完整工作流程"""

        class CompleteWorkflowStrategy(BaseStrategy):
            def cal(self, portfolio_info, event):
                return [_make_signal()]

        # 设置完整的投资组合
        strategy = CompleteWorkflowStrategy("complete_workflow")
        strategy.set_business_timestamp(self.test_time)

        self.portfolio.add_strategy(strategy)
        self.portfolio.bind_selector(self.selector)
        self.portfolio.bind_sizer(self.sizer)
        self.portfolio.add_analyzer(self.analyzer)

        # 验证投资组合配置完整
        self.assertTrue(self.portfolio.is_all_set())

        # 验证各组件都已正确绑定
        self.assertIn(strategy, self.portfolio.strategies)
        self.assertIn(self.selector, self.portfolio.selectors)
        self.assertEqual(self.portfolio.sizer, self.sizer)
        self.assertIn("test_net_value", self.portfolio.analyzers)

        # 模拟完整的交易流程
        signals = strategy.cal({}, Mock())
        self.assertEqual(len(signals), 1)

        selected_codes = self.selector.pick()
        self.assertEqual(len(selected_codes), 2)

        # 验证信号代码在选择的代码中
        self.assertIn(signals[0].code, selected_codes)


if __name__ == '__main__':
    unittest.main()
