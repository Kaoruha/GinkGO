import unittest
from datetime import datetime, timedelta
from unittest.mock import Mock, patch, MagicMock
from decimal import Decimal

from ginkgo.backtest.strategy.sizers.base_sizer import BaseSizer
from ginkgo.backtest.strategy.sizers.fixed_sizer import FixedSizer
from ginkgo.backtest.entities.signal import Signal
from ginkgo.backtest.entities.order import Order
from ginkgo.backtest.feeders.base_feeder import BaseFeeder
from ginkgo.enums import DIRECTION_TYPES, ORDER_TYPES, ORDERSTATUS_TYPES


class BaseSizerTest(unittest.TestCase):
    """
    测试BaseSizer模块 - 测试基础仓位管理器功能
    """

    def setUp(self):
        """初始化测试用的BaseSizer实例"""
        self.sizer = BaseSizer("test_sizer")
        self.test_time = datetime(2024, 1, 1, 10, 0, 0)
        self.sizer.on_time_goes_by(self.test_time)

    def test_base_sizer_init(self):
        """测试基础仓位管理器初始化"""
        sizer = BaseSizer("test_sizer")
        self.assertIsNotNone(sizer)

        # 检查基本属性
        self.assertTrue(hasattr(sizer, "_name"))
        self.assertEqual(sizer._name, "test_sizer")
        self.assertTrue(hasattr(sizer, "_data_feeder"))
        self.assertIsNone(sizer._data_feeder)

    def test_default_initialization(self):
        """测试默认初始化"""
        sizer = BaseSizer()
        self.assertEqual(sizer._name, "BaseSizer")
        self.assertIsNone(sizer._data_feeder)

    def test_name_property(self):
        """测试name属性"""
        self.assertEqual(self.sizer.name, "test_sizer")

    def test_bind_data_feeder(self):
        """测试数据源绑定功能"""
        # 创建mock数据源
        mock_feeder = Mock(spec=BaseFeeder)
        
        # 初始状态应该没有绑定数据源
        self.assertIsNone(self.sizer._data_feeder)
        
        # 绑定数据源
        self.sizer.bind_data_feeder(mock_feeder)
        
        # 验证绑定成功
        self.assertEqual(self.sizer._data_feeder, mock_feeder)

    def test_bind_data_feeder_with_args_kwargs(self):
        """测试带参数的数据源绑定"""
        mock_feeder = Mock()
        test_args = ("arg1", "arg2")
        test_kwargs = {"param1": "value1", "param2": "value2"}
        
        # 绑定数据源并传递参数
        self.sizer.bind_data_feeder(mock_feeder, *test_args, **test_kwargs)
        
        # 验证绑定成功
        self.assertEqual(self.sizer._data_feeder, mock_feeder)

    def test_cal_method_not_implemented(self):
        """测试抽象cal方法抛出NotImplemented错误"""
        mock_portfolio_info = {"cash": 10000, "positions": {}}
        mock_signal = Mock(spec=Signal)
        
        with self.assertRaises(Exception):  # NotImplemented应该是Exception子类
            self.sizer.cal(mock_portfolio_info, mock_signal)

    def test_inheritance_from_backtest_base(self):
        """测试是否正确继承BacktestBase"""
        from ginkgo.backtest.core.backtest_base import BacktestBase
        
        # 验证继承关系
        self.assertIsInstance(self.sizer, BacktestBase)
        
        # 验证继承的属性和方法
        self.assertTrue(hasattr(self.sizer, "on_time_goes_by"))
        self.assertTrue(hasattr(self.sizer, "now"))
        self.assertTrue(hasattr(self.sizer, "_name"))
        self.assertTrue(hasattr(self.sizer, "log"))

    def test_time_management(self):
        """测试时间管理功能（继承自BacktestBase）"""
        # 测试时间设置
        test_time = datetime(2024, 2, 1, 15, 30, 0)
        self.sizer.on_time_goes_by(test_time)
        self.assertEqual(self.sizer.now, test_time)

    def test_logging_functionality(self):
        """测试日志功能（继承自BacktestBase）"""
        with patch.object(self.sizer, 'log') as mock_log:
            # 调用log方法
            self.sizer.log("INFO", "Test message")
            
            # 验证log方法被调用
            mock_log.assert_called_once_with("INFO", "Test message")

    # =========================
    # 具体实现测试（使用FixedSizer作为示例）
    # =========================

    def test_concrete_sizer_implementation(self):
        """测试具体仓位管理器实现（FixedSizer）"""
        volume = "200"
        sizer = FixedSizer("fixed_test", volume)
        
        # 验证初始化成功
        self.assertIsNotNone(sizer)
        self.assertEqual(sizer.name, "fixed_test")
        self.assertIsInstance(sizer, BaseSizer)
        self.assertEqual(sizer.volume, 200)

    def test_fixed_sizer_volume_property(self):
        """测试FixedSizer的volume属性"""
        volume = "500"
        sizer = FixedSizer("volume_test", volume)
        
        self.assertEqual(sizer.volume, 500)
        self.assertIsInstance(sizer.volume, (int, float))

    def test_fixed_sizer_calculate_order_size(self):
        """测试FixedSizer的订单大小计算"""
        sizer = FixedSizer("calc_test", "100")
        
        # 测试充足资金情况
        initial_size = 100
        last_price = Decimal("10.0")
        cash = Decimal("2000.0")
        
        size, cost = sizer.calculate_order_size(initial_size, last_price, cash)
        
        # 验证计算结果
        self.assertEqual(size, 100)
        expected_cost = Decimal("10.0") * 100 * Decimal("1.1")
        self.assertEqual(cost, expected_cost)

    def test_fixed_sizer_calculate_order_size_insufficient_funds(self):
        """测试资金不足情况下的订单大小计算"""
        sizer = FixedSizer("insufficient_test", "1000")
        
        # 测试资金不足情况
        initial_size = 1000
        last_price = Decimal("10.0")
        cash = Decimal("500.0")  # 不足以购买1000股
        
        size, cost = sizer.calculate_order_size(initial_size, last_price, cash)
        
        # 应该返回0，表示无法下单
        self.assertEqual(size, 0)
        self.assertEqual(cost, 0)

    @patch('ginkgo.data.get_bars')
    def test_fixed_sizer_long_signal_processing(self, mock_get_bars):
        """测试FixedSizer处理LONG信号"""
        # 设置mock数据
        mock_df = Mock()
        mock_df.shape = [1, 5]  # 模拟有数据
        mock_df.iloc = [{"close": 10.5}]
        mock_get_bars.return_value = mock_df
        
        sizer = FixedSizer("long_test", "100")
        sizer.on_time_goes_by(self.test_time)
        sizer.engine_id = "test_engine"
        
        # 创建mock信号
        signal = Mock(spec=Signal)
        signal.code = "000001.SZ"
        signal.direction = DIRECTION_TYPES.LONG
        signal.is_valid.return_value = True
        
        # 创建portfolio信息
        portfolio_info = {
            "cash": Decimal("2000.0"),
            "positions": {},
            "portfolio_id": "test_portfolio"
        }
        
        # 调用cal方法
        order = sizer.cal(portfolio_info, signal)
        
        # 验证订单创建成功
        self.assertIsNotNone(order)
        self.assertIsInstance(order, Order)

    def test_fixed_sizer_short_signal_processing(self):
        """测试FixedSizer处理SHORT信号"""
        sizer = FixedSizer("short_test", "100")
        sizer.on_time_goes_by(self.test_time)
        sizer.engine_id = "test_engine"
        
        # 创建mock信号
        signal = Mock(spec=Signal)
        signal.code = "000001.SZ"
        signal.direction = DIRECTION_TYPES.SHORT
        signal.is_valid.return_value = True
        
        # 创建mock持仓
        mock_position = Mock()
        mock_position.volume = 200
        
        # 创建portfolio信息（包含持仓）
        portfolio_info = {
            "cash": Decimal("2000.0"),
            "positions": {"000001.SZ": mock_position},
            "portfolio_id": "test_portfolio"
        }
        
        # 调用cal方法
        order = sizer.cal(portfolio_info, signal)
        
        # 验证订单创建成功
        self.assertIsNotNone(order)
        self.assertIsInstance(order, Order)

    def test_fixed_sizer_short_signal_no_position(self):
        """测试FixedSizer处理SHORT信号但无持仓的情况"""
        sizer = FixedSizer("no_pos_test", "100")
        sizer.on_time_goes_by(self.test_time)
        
        # 创建mock信号
        signal = Mock(spec=Signal)
        signal.code = "000001.SZ"
        signal.direction = DIRECTION_TYPES.SHORT
        signal.is_valid.return_value = True
        
        # 创建portfolio信息（无持仓）
        portfolio_info = {
            "cash": Decimal("2000.0"),
            "positions": {},  # 空持仓
            "portfolio_id": "test_portfolio"
        }
        
        # 调用cal方法
        order = sizer.cal(portfolio_info, signal)
        
        # 应该返回None，因为没有持仓无法卖出
        self.assertIsNone(order)

    # =========================
    # 错误处理和边界测试
    # =========================

    def test_fixed_sizer_none_signal_handling(self):
        """测试FixedSizer处理None信号的情况"""
        sizer = FixedSizer("none_signal_test", "100")
        portfolio_info = {"cash": 1000, "positions": {}}
        
        with patch.object(sizer, 'log') as mock_log:
            result = sizer.cal(portfolio_info, None)
            
            # 应该返回None并记录错误日志
            self.assertIsNone(result)
            mock_log.assert_called_with("ERROR", unittest.mock.ANY)

    def test_fixed_sizer_invalid_signal_handling(self):
        """测试FixedSizer处理无效信号的情况"""
        sizer = FixedSizer("invalid_signal_test", "100")
        
        # 创建无效信号
        invalid_signal = Mock(spec=Signal)
        invalid_signal.is_valid.return_value = False
        
        portfolio_info = {"cash": 1000, "positions": {}}
        
        with patch.object(sizer, 'log') as mock_log:
            result = sizer.cal(portfolio_info, invalid_signal)
            
            # 应该返回None并记录错误日志
            self.assertIsNone(result)
            mock_log.assert_called_with("ERROR", unittest.mock.ANY)

    def test_fixed_sizer_none_portfolio_info_handling(self):
        """测试FixedSizer处理None portfolio_info的情况"""
        sizer = FixedSizer("none_portfolio_test", "100")
        
        signal = Mock(spec=Signal)
        signal.is_valid.return_value = True
        
        with patch.object(sizer, 'log') as mock_log:
            result = sizer.cal(None, signal)
            
            # 应该返回None并记录错误日志
            self.assertIsNone(result)
            mock_log.assert_called_with("ERROR", unittest.mock.ANY)

    def test_fixed_sizer_missing_portfolio_fields_handling(self):
        """测试FixedSizer处理缺失portfolio字段的情况"""
        sizer = FixedSizer("missing_fields_test", "100")
        
        signal = Mock(spec=Signal)
        signal.is_valid.return_value = True
        
        # 测试缺失positions字段
        incomplete_portfolio_info = {"cash": 1000}  # 缺失positions
        
        with patch.object(sizer, 'log') as mock_log:
            result = sizer.cal(incomplete_portfolio_info, signal)
            
            # 应该返回None并记录错误日志
            self.assertIsNone(result)
            mock_log.assert_called_with("ERROR", unittest.mock.ANY)

    @patch('ginkgo.data.get_bars')
    def test_fixed_sizer_no_price_data_handling(self, mock_get_bars):
        """测试FixedSizer处理无价格数据的情况"""
        # 设置mock返回空数据
        mock_df = Mock()
        mock_df.shape = [0, 5]  # 模拟无数据
        mock_get_bars.return_value = mock_df
        
        sizer = FixedSizer("no_data_test", "100")
        sizer.on_time_goes_by(self.test_time)
        
        signal = Mock(spec=Signal)
        signal.code = "000001.SZ"
        signal.direction = DIRECTION_TYPES.LONG
        signal.is_valid.return_value = True
        
        portfolio_info = {
            "cash": Decimal("2000.0"),
            "positions": {},
            "portfolio_id": "test_portfolio"
        }
        
        with patch.object(sizer, 'log') as mock_log:
            result = sizer.cal(portfolio_info, signal)
            
            # 应该返回None并记录CRITICAL日志
            self.assertIsNone(result)
            # 检查是否记录了CRITICAL级别的日志
            critical_logs = [call for call in mock_log.call_args_list if call[0][0] == "CRITICAL"]
            self.assertGreater(len(critical_logs), 0)

    # =========================
    # 资源管理和性能测试
    # =========================

    def test_data_feeder_rebinding(self):
        """测试数据源重新绑定"""
        mock_feeder1 = Mock()
        mock_feeder2 = Mock()
        
        # 绑定第一个数据源
        self.sizer.bind_data_feeder(mock_feeder1)
        self.assertEqual(self.sizer._data_feeder, mock_feeder1)
        
        # 重新绑定第二个数据源
        self.sizer.bind_data_feeder(mock_feeder2)
        self.assertEqual(self.sizer._data_feeder, mock_feeder2)

    def test_data_feeder_none_binding(self):
        """测试绑定None数据源"""
        # 先绑定一个正常的数据源
        mock_feeder = Mock()
        self.sizer.bind_data_feeder(mock_feeder)
        self.assertEqual(self.sizer._data_feeder, mock_feeder)
        
        # 绑定None应该覆盖之前的绑定
        self.sizer.bind_data_feeder(None)
        self.assertIsNone(self.sizer._data_feeder)

    def test_multiple_sizers_independence(self):
        """测试多个仓位管理器实例的独立性"""
        sizer1 = BaseSizer("sizer1")
        sizer2 = BaseSizer("sizer2")
        
        mock_feeder1 = Mock()
        mock_feeder2 = Mock()
        
        # 分别绑定不同的数据源
        sizer1.bind_data_feeder(mock_feeder1)
        sizer2.bind_data_feeder(mock_feeder2)
        
        # 验证独立性
        self.assertEqual(sizer1._data_feeder, mock_feeder1)
        self.assertEqual(sizer2._data_feeder, mock_feeder2)
        self.assertNotEqual(sizer1._data_feeder, sizer2._data_feeder)

    def test_sizer_time_independence(self):
        """测试仓位管理器时间设置的独立性"""
        sizer1 = BaseSizer("sizer1")
        sizer2 = BaseSizer("sizer2")
        
        time1 = datetime(2024, 1, 1, 10, 0, 0)
        time2 = datetime(2024, 1, 2, 15, 30, 0)
        
        # 设置不同的时间
        sizer1.on_time_goes_by(time1)
        sizer2.on_time_goes_by(time2)
        
        # 验证时间独立性
        self.assertEqual(sizer1.now, time1)
        self.assertEqual(sizer2.now, time2)

    def test_abstract_behavior_enforcement(self):
        """测试抽象行为的强制执行"""
        # BaseSizer的cal方法应该抛出NotImplemented错误
        mock_portfolio = {"cash": 1000, "positions": {}}
        mock_signal = Mock(spec=Signal)
        
        with self.assertRaises(Exception):
            self.sizer.cal(mock_portfolio, mock_signal)
        
        # 子类应该重写这个方法来提供具体实现
        class ConcreteSizer(BaseSizer):
            def cal(self, portfolio_info, signal, *args, **kwargs):
                return "OVERRIDDEN"
        
        concrete = ConcreteSizer("concrete")
        result = concrete.cal(mock_portfolio, mock_signal)
        self.assertEqual(result, "OVERRIDDEN")

    def test_sizer_resource_cleanup(self):
        """测试仓位管理器资源清理"""
        sizers = []
        
        # 创建多个仓位管理器实例
        for i in range(10):
            sizer = BaseSizer(f"sizer_{i}")
            sizer.bind_data_feeder(Mock())
            sizers.append(sizer)
        
        # 验证所有仓位管理器都正常工作
        for sizer in sizers:
            self.assertIsNotNone(sizer._data_feeder)
            # cal方法应该抛出NotImplemented
            with self.assertRaises(Exception):
                sizer.cal({}, Mock())
        
        # 清理引用
        sizers.clear()
        
        # 原始仓位管理器应该仍然正常工作
        self.assertIsNone(self.sizer._data_feeder)
        with self.assertRaises(Exception):
            self.sizer.cal({}, Mock())

    def test_sizer_repr_method(self):
        """测试仓位管理器的字符串表示"""
        repr_str = repr(self.sizer)
        self.assertIsInstance(repr_str, str)
        self.assertIn("test_sizer", repr_str)

    def test_engine_id_access(self):
        """测试engine_id访问（继承自BacktestBase）"""
        # engine_id应该可以访问和设置
        self.assertTrue(hasattr(self.sizer, "engine_id"))
        
        test_id = "test_engine_123"
        self.sizer.engine_id = test_id
        self.assertEqual(self.sizer.engine_id, test_id)

    def test_fixed_sizer_string_to_int_conversion(self):
        """测试FixedSizer字符串到整数的转换"""
        # 测试正常字符串转换
        sizer1 = FixedSizer("convert_test", "300")
        self.assertEqual(sizer1.volume, 300)
        
        # 测试默认值
        sizer2 = FixedSizer("default_test")  # 应该使用默认volume="150"
        self.assertEqual(sizer2.volume, 150)


if __name__ == '__main__':
    unittest.main()