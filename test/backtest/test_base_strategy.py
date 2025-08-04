import unittest
import pandas as pd
from datetime import datetime
from unittest.mock import Mock

from ginkgo.backtest.strategy.strategies.base_strategy import StrategyBase
from ginkgo.backtest.entities.signal import Signal


class StrategiesTest(unittest.TestCase):
    """
    测试策略模块 - 仅测试StrategyBase
    """

    def setUp(self):
        """初始化测试用的StrategyBase实例"""
        self.strategy = StrategyBase("test_strategy")
        self.test_time = datetime(2024, 1, 1, 10, 0, 0)
        self.strategy.on_time_goes_by(self.test_time)

        # 创建测试用的portfolio_info和event
        self.portfolio_info = {"cash": 100000, "positions": {}, "net_value": 100000}
        self.mock_event = Mock()

    def test_StrategyBase_Init(self):
        """测试基础策略初始化"""
        strategy = StrategyBase("test_strategy")
        self.assertIsNotNone(strategy)

        # 检查基本属性
        self.assertTrue(hasattr(strategy, "_name"))
        self.assertEqual(strategy._name, "test_strategy")
        self.assertEqual(strategy._raw, {})
        self.assertIsNone(strategy._data_feeder)

    def test_name_property(self):
        """测试name属性"""
        self.assertEqual(self.strategy.name, "test_strategy")

    def test_bind_data_feeder(self):
        """测试绑定数据源"""
        mock_feeder = Mock()
        self.strategy.bind_data_feeder(mock_feeder)

        # 验证数据源已绑定
        self.assertEqual(self.strategy._data_feeder, mock_feeder)
        self.assertEqual(self.strategy.data_feeder, mock_feeder)

    def test_data_feeder_property(self):
        """测试data_feeder属性"""
        # 初始状态应该为None
        self.assertIsNone(self.strategy.data_feeder)

        # 绑定数据源后应该返回绑定的数据源
        mock_feeder = Mock()
        self.strategy.bind_data_feeder(mock_feeder)
        self.assertEqual(self.strategy.data_feeder, mock_feeder)

    def test_cal_method_interface(self):
        """测试cal方法接口"""
        # cal方法应该存在
        self.assertTrue(hasattr(self.strategy, "cal"))
        self.assertTrue(callable(self.strategy.cal))

        # 调用cal方法应该返回信号列表
        result = self.strategy.cal(self.portfolio_info, self.mock_event)
        self.assertIsInstance(result, list)
        # 对于基础策略，应该返回空列表
        self.assertEqual(result, [])

    def test_cal_method_with_different_inputs(self):
        """测试cal方法对不同输入的处理"""
        # 测试正常输入
        result = self.strategy.cal(self.portfolio_info, self.mock_event)
        self.assertIsInstance(result, list)

        # 测试空portfolio_info
        result = self.strategy.cal({}, self.mock_event)
        self.assertIsInstance(result, list)

        # 测试None输入
        result = self.strategy.cal(None, self.mock_event)
        self.assertIsInstance(result, list)

        result = self.strategy.cal(self.portfolio_info, None)
        self.assertIsInstance(result, list)

    def test_inheritance_from_backtest_base(self):
        """测试是否正确继承BacktestBase"""
        from ginkgo.backtest.backtest_base import BacktestBase

        # 验证继承关系
        self.assertIsInstance(self.strategy, BacktestBase)

        # 验证继承的属性和方法
        self.assertTrue(hasattr(self.strategy, "on_time_goes_by"))
        self.assertTrue(hasattr(self.strategy, "now"))
        self.assertTrue(hasattr(self.strategy, "_name"))

    def test_raw_data_attribute(self):
        """测试_raw属性"""
        # 初始状态应该是空字典
        self.assertEqual(self.strategy._raw, {})
        self.assertIsInstance(self.strategy._raw, dict)

        # 可以修改_raw属性
        self.strategy._raw["test_key"] = "test_value"
        self.assertEqual(self.strategy._raw["test_key"], "test_value")

    def test_time_management(self):
        """测试时间管理功能（继承自BacktestBase）"""
        # 测试时间设置
        test_time = datetime(2024, 2, 1, 15, 30, 0)
        self.strategy.on_time_goes_by(test_time)
        self.assertEqual(self.strategy.now, test_time)

    def test_strategy_polymorphism(self):
        """测试策略多态性"""
        from ginkgo.enums import DIRECTION_TYPES, SOURCE_TYPES

        # 创建自定义策略类
        class CustomStrategy(StrategyBase):
            def cal(self, portfolio_info, event, *args, **kwargs):
                return [Signal(
                    portfolio_id="test_portfolio",
                    engine_id="test_engine", 
                    timestamp=datetime(2024, 1, 1),
                    code="TEST001",
                    direction=DIRECTION_TYPES.LONG,
                    reason="test_signal",
                    source=SOURCE_TYPES.OTHER
                )]

        custom_strategy = CustomStrategy("custom_test")
        result = custom_strategy.cal(self.portfolio_info, self.mock_event)

        # 验证自定义策略的cal方法被正确调用
        self.assertIsInstance(result, list)
        self.assertEqual(len(result), 1)
        self.assertIsInstance(result[0], Signal)
        self.assertEqual(result[0].code, "TEST001")
        self.assertEqual(result[0].direction, DIRECTION_TYPES.LONG)
