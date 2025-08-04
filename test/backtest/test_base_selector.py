import unittest
from datetime import datetime, timedelta
from unittest.mock import Mock, patch

from ginkgo.backtest.strategy.selectors.base_selector import BaseSelector
from ginkgo.backtest.strategy.selectors.fixed_selector import FixedSelector
from ginkgo.backtest.feeders.base_feeder import BaseFeeder


class BaseSelectorTest(unittest.TestCase):
    """
    测试BaseSelector模块 - 测试基础选择器功能
    """

    def setUp(self):
        """初始化测试用的BaseSelector实例"""
        self.selector = BaseSelector("test_selector")
        self.test_time = datetime(2024, 1, 1, 10, 0, 0)
        self.selector.on_time_goes_by(self.test_time)

    def test_base_selector_init(self):
        """测试基础选择器初始化"""
        selector = BaseSelector("test_selector")
        self.assertIsNotNone(selector)

        # 检查基本属性
        self.assertTrue(hasattr(selector, "_name"))
        self.assertEqual(selector._name, "test_selector")
        self.assertTrue(hasattr(selector, "_data_feeder"))
        self.assertIsNone(selector._data_feeder)

    def test_default_initialization(self):
        """测试默认初始化"""
        selector = BaseSelector()
        self.assertEqual(selector._name, "BaseSelector")
        self.assertIsNone(selector._data_feeder)

    def test_name_property(self):
        """测试name属性"""
        self.assertEqual(self.selector.name, "test_selector")

    def test_bind_data_feeder(self):
        """测试数据源绑定功能"""
        # 创建mock数据源
        mock_feeder = Mock(spec=BaseFeeder)
        
        # 初始状态应该没有绑定数据源
        self.assertIsNone(self.selector._data_feeder)
        
        # 绑定数据源
        self.selector.bind_data_feeder(mock_feeder)
        
        # 验证绑定成功
        self.assertEqual(self.selector._data_feeder, mock_feeder)

    def test_bind_data_feeder_with_args_kwargs(self):
        """测试带参数的数据源绑定"""
        mock_feeder = Mock()
        test_args = ("arg1", "arg2")
        test_kwargs = {"param1": "value1", "param2": "value2"}
        
        # 绑定数据源并传递参数
        self.selector.bind_data_feeder(mock_feeder, *test_args, **test_kwargs)
        
        # 验证绑定成功
        self.assertEqual(self.selector._data_feeder, mock_feeder)

    def test_default_pick_method(self):
        """测试默认的pick方法"""
        # 默认pick方法应该返回空列表
        result = self.selector.pick()
        self.assertIsInstance(result, list)
        self.assertEqual(len(result), 0)

    def test_pick_method_with_time_parameter(self):
        """测试带时间参数的pick方法"""
        test_time = datetime(2024, 1, 1, 15, 30, 0)
        
        result = self.selector.pick(time=test_time)
        self.assertIsInstance(result, list)
        self.assertEqual(len(result), 0)

    def test_pick_method_with_args_kwargs(self):
        """测试带任意参数的pick方法"""
        test_args = ("arg1", "arg2")
        test_kwargs = {"param1": "value1", "param2": "value2"}
        
        result = self.selector.pick("time", *test_args, **test_kwargs)
        self.assertIsInstance(result, list)
        self.assertEqual(len(result), 0)

    def test_inheritance_from_backtest_base(self):
        """测试是否正确继承BacktestBase"""
        from ginkgo.backtest.core.backtest_base import BacktestBase
        
        # 验证继承关系
        self.assertIsInstance(self.selector, BacktestBase)
        
        # 验证继承的属性和方法
        self.assertTrue(hasattr(self.selector, "on_time_goes_by"))
        self.assertTrue(hasattr(self.selector, "now"))
        self.assertTrue(hasattr(self.selector, "_name"))
        self.assertTrue(hasattr(self.selector, "log"))

    def test_time_management(self):
        """测试时间管理功能（继承自BacktestBase）"""
        # 测试时间设置
        test_time = datetime(2024, 2, 1, 15, 30, 0)
        self.selector.on_time_goes_by(test_time)
        self.assertEqual(self.selector.now, test_time)

    def test_logging_functionality(self):
        """测试日志功能（继承自BacktestBase）"""
        with patch.object(self.selector, 'log') as mock_log:
            # 调用log方法
            self.selector.log("INFO", "Test message")
            
            # 验证log方法被调用
            mock_log.assert_called_once_with("INFO", "Test message")

    # =========================
    # 具体实现测试（使用FixedSelector作为示例）
    # =========================

    def test_concrete_selector_implementation(self):
        """测试具体选择器实现（FixedSelector）"""
        # 测试有效的JSON字符串
        valid_codes = '["000001.SZ", "000002.SZ", "600000.SH"]'
        selector = FixedSelector("fixed_test", valid_codes)
        
        # 验证初始化成功
        self.assertIsNotNone(selector)
        self.assertEqual(selector.name, "fixed_test")
        self.assertIsInstance(selector, BaseSelector)

    def test_fixed_selector_pick_functionality(self):
        """测试FixedSelector的pick功能"""
        codes = '["000001.SZ", "000002.SZ", "600000.SH"]'
        selector = FixedSelector("fixed_test", codes)
        
        # 测试pick方法
        result = selector.pick()
        expected = ["000001.SZ", "000002.SZ", "600000.SH"]
        
        self.assertEqual(result, expected)
        self.assertIsInstance(result, list)
        self.assertEqual(len(result), 3)

    def test_fixed_selector_invalid_json(self):
        """测试FixedSelector处理无效JSON的情况"""
        invalid_codes = "invalid json string"
        
        # 应该能创建实例，但_interested应该为空列表
        selector = FixedSelector("invalid_json_test", invalid_codes)
        
        # pick应该返回空列表
        result = selector.pick()
        self.assertEqual(result, [])

    def test_fixed_selector_with_logging(self):
        """测试FixedSelector的日志记录"""
        codes = '["TEST001", "TEST002"]'
        selector = FixedSelector("logging_test", codes)
        
        with patch.object(selector, 'log') as mock_log:
            result = selector.pick()
            
            # 验证日志被记录
            mock_log.assert_called_once()
            call_args = mock_log.call_args[0]
            self.assertEqual(call_args[0], "DEBUG")
            self.assertIn("pick", call_args[1])

    # =========================
    # 边界和错误处理测试
    # =========================

    def test_data_feeder_rebinding(self):
        """测试数据源重新绑定"""
        mock_feeder1 = Mock()
        mock_feeder2 = Mock()
        
        # 绑定第一个数据源
        self.selector.bind_data_feeder(mock_feeder1)
        self.assertEqual(self.selector._data_feeder, mock_feeder1)
        
        # 重新绑定第二个数据源
        self.selector.bind_data_feeder(mock_feeder2)
        self.assertEqual(self.selector._data_feeder, mock_feeder2)

    def test_data_feeder_none_binding(self):
        """测试绑定None数据源"""
        # 先绑定一个正常的数据源
        mock_feeder = Mock()
        self.selector.bind_data_feeder(mock_feeder)
        self.assertEqual(self.selector._data_feeder, mock_feeder)
        
        # 绑定None应该覆盖之前的绑定
        self.selector.bind_data_feeder(None)
        self.assertIsNone(self.selector._data_feeder)

    def test_pick_with_none_time(self):
        """测试时间为None时的pick方法"""
        result = self.selector.pick(time=None)
        self.assertIsInstance(result, list)
        self.assertEqual(len(result), 0)

    def test_multiple_selectors_independence(self):
        """测试多个选择器实例的独立性"""
        selector1 = BaseSelector("selector1")
        selector2 = BaseSelector("selector2")
        
        mock_feeder1 = Mock()
        mock_feeder2 = Mock()
        
        # 分别绑定不同的数据源
        selector1.bind_data_feeder(mock_feeder1)
        selector2.bind_data_feeder(mock_feeder2)
        
        # 验证独立性
        self.assertEqual(selector1._data_feeder, mock_feeder1)
        self.assertEqual(selector2._data_feeder, mock_feeder2)
        self.assertNotEqual(selector1._data_feeder, selector2._data_feeder)

    def test_selector_time_independence(self):
        """测试选择器时间设置的独立性"""
        selector1 = BaseSelector("selector1")
        selector2 = BaseSelector("selector2")
        
        time1 = datetime(2024, 1, 1, 10, 0, 0)
        time2 = datetime(2024, 1, 2, 15, 30, 0)
        
        # 设置不同的时间
        selector1.on_time_goes_by(time1)
        selector2.on_time_goes_by(time2)
        
        # 验证时间独立性
        self.assertEqual(selector1.now, time1)
        self.assertEqual(selector2.now, time2)

    # =========================
    # 性能和资源管理测试
    # =========================

    def test_selector_resource_cleanup(self):
        """测试选择器资源清理"""
        selectors = []
        
        # 创建多个选择器实例
        for i in range(10):
            selector = BaseSelector(f"selector_{i}")
            selector.bind_data_feeder(Mock())
            selectors.append(selector)
        
        # 验证所有选择器都正常工作
        for selector in selectors:
            self.assertIsNotNone(selector._data_feeder)
            result = selector.pick()
            self.assertIsInstance(result, list)
        
        # 清理引用
        selectors.clear()
        
        # 原始选择器应该仍然正常工作
        self.assertIsNone(self.selector._data_feeder)
        result = self.selector.pick()
        self.assertIsInstance(result, list)

    def test_selector_with_large_time_range(self):
        """测试选择器在大时间范围内的稳定性"""
        start_time = datetime(2020, 1, 1)
        
        # 测试大时间跨度
        for i in range(1000):
            test_time = start_time + timedelta(days=i)
            self.selector.on_time_goes_by(test_time)
            result = self.selector.pick(time=test_time)
            
            # 每次调用都应该返回空列表
            self.assertIsInstance(result, list)
            self.assertEqual(len(result), 0)
        
        # 验证最终时间设置正确
        expected_final_time = start_time + timedelta(days=999)
        self.assertEqual(self.selector.now, expected_final_time)

    def test_abstract_behavior_enforcement(self):
        """测试抽象行为的强制执行"""
        # BaseSelector不是真正的抽象类，但应该被子类重写
        # 这里测试默认行为是否符合预期
        
        # 默认pick方法应该返回空列表，提示需要重写
        result = self.selector.pick()
        self.assertEqual(result, [])
        
        # 子类应该重写这个方法来提供具体实现
        class ConcreteSelector(BaseSelector):
            def pick(self, time=None, *args, **kwargs):
                return ["OVERRIDDEN"]
        
        concrete = ConcreteSelector("concrete")
        result = concrete.pick()
        self.assertEqual(result, ["OVERRIDDEN"])

    def test_selector_repr_method(self):
        """测试选择器的字符串表示"""
        repr_str = repr(self.selector)
        self.assertIsInstance(repr_str, str)
        self.assertIn("test_selector", repr_str)

    def test_engine_id_access(self):
        """测试engine_id访问（继承自BacktestBase）"""
        # engine_id应该可以访问和设置
        self.assertTrue(hasattr(self.selector, "engine_id"))
        
        test_id = "test_engine_123"
        self.selector.engine_id = test_id
        self.assertEqual(self.selector.engine_id, test_id)


if __name__ == '__main__':
    unittest.main()