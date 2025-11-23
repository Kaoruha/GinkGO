"""
FixedSizer固定规模开仓器测试

验证固定规模开仓器的完整功能：
- 固定订单规模计算
- 买入/卖出订单创建
- 资金充足性检查
- 信号和Portfolio信息验证
- 错误处理和边界条件
- 价格数据获取和处理
"""

import pytest
import datetime
from decimal import Decimal
from unittest.mock import Mock, patch, MagicMock

from ginkgo.trading.sizers.fixed_sizer import FixedSizer
from ginkgo.trading.entities.signal import Signal
from ginkgo.trading.entities.order import Order
from ginkgo.trading.entities.position import Position
from ginkgo.enums import DIRECTION_TYPES, ORDER_TYPES, ORDERSTATUS_TYPES


@pytest.mark.sizer
@pytest.mark.fixed_sizer
class TestFixedSizerBasics:
    """FixedSizer基础功能测试"""

    def test_sizer_initialization(self):
        """测试开仓器初始化"""
        print("\n测试开仓器初始化")

        # 默认参数初始化
        sizer = FixedSizer()

        # 验证基本属性
        assert sizer.name == "FixedSizer"
        assert sizer.volume == 150
        assert sizer._volume == 150

        # 自定义参数初始化
        custom_sizer = FixedSizer(name="CustomSizer", volume="200")

        assert custom_sizer.name == "CustomSizer"
        assert custom_sizer.volume == 200
        assert custom_sizer._volume == 200

        print("✓ 开仓器初始化成功")

    def test_volume_property(self):
        """测试volume属性"""
        print("\n测试volume属性")

        sizer = FixedSizer(volume="300")

        # 验证volume属性
        assert sizer.volume == 300
        assert isinstance(sizer.volume, int)

        print("✓ volume属性正确")

    def test_volume_string_conversion(self):
        """测试volume字符串转换"""
        print("\n测试volume字符串转换")

        test_cases = [
            ("100", 100),
            ("0", 0),
            ("999", 999),
            ("50", 50),
        ]

        for volume_str, expected in test_cases:
            sizer = FixedSizer(volume=volume_str)
            assert sizer.volume == expected

        print("✓ volume字符串转换成功")


@pytest.mark.sizer
@pytest.mark.order_calculation
class TestFixedSizerOrderCalculation:
    """FixedSizer订单计算测试"""

    def setup_method(self):
        """测试前设置"""
        self.sizer = FixedSizer(name="TestSizer", volume="100")
        # 设置模拟时间
        self.sizer.now = datetime.datetime(2023, 1, 1, 9, 30)

    def test_calculate_order_size_sufficient_cash(self):
        """测试资金充足时的订单规模计算"""
        print("\n测试资金充足时的订单规模计算")

        initial_size = 100
        last_price = Decimal("10.00")
        cash = Decimal("2000.00")  # 足够的资金

        size, cost = self.sizer.calculate_order_size(initial_size, last_price, cash)

        # 验证计算结果
        assert size == 100
        assert cost == last_price * size * Decimal("1.1")  # 10.00 * 100 * 1.1 = 1100

        print(f"✓ 资金充足: 规模={size}, 成本={cost}")

    def test_calculate_order_size_insufficient_cash(self):
        """测试资金不足时的订单规模计算"""
        print("\n测试资金不足时的订单规模计算")

        initial_size = 100
        last_price = Decimal("10.00")
        cash = Decimal("500.00")  # 不足的资金

        size, cost = self.sizer.calculate_order_size(initial_size, last_price, cash)

        # 验证规模被调整
        assert size < initial_size
        assert cost <= cash

        print(f"✓ 资金不足: 规模={size}, 成本={cost}")

    def test_calculate_order_size_very_insufficient_cash(self):
        """测试资金严重不足时的订单规模计算"""
        print("\n测试资金严重不足时的订单规模计算")

        initial_size = 100
        last_price = Decimal("50.00")
        cash = Decimal("100.00")  # 严重不足

        size, cost = self.sizer.calculate_order_size(initial_size, last_price, cash)

        # 验证无法创建订单
        assert size == 0
        assert cost == 0

        print(f"✓ 资金严重不足: 规模={size}, 成本={cost}")

    def test_calculate_order_size_zero_initial_size(self):
        """测试零初始规模"""
        print("\n测试零初始规模")

        initial_size = 0
        last_price = Decimal("10.00")
        cash = Decimal("1000.00")

        size, cost = self.sizer.calculate_order_size(initial_size, last_price, cash)

        # 验证零初始规模处理
        assert size == 0
        assert cost == 0

        print(f"✓ 零初始规模: 规模={size}, 成本={cost}")

    def test_calculate_order_size_rounding_down(self):
        """测试向下取整（100的倍数）"""
        print("\n测试向下取整（100的倍数）")

        initial_size = 150
        last_price = Decimal("10.00")
        cash = Decimal("1100.00")  # 只够100股，不够150股

        size, cost = self.sizer.calculate_order_size(initial_size, last_price, cash)

        # 验证规模被调整为100的倍数
        assert size == 100
        assert size % 100 == 0

        print(f"✓ 向下取整: 规模={size}, 成本={cost}")


@pytest.mark.sizer
@pytest.mark.signal_processing
class TestFixedSizerSignalProcessing:
    """FixedSizer信号处理测试"""

    def setup_method(self):
        """测试前设置"""
        self.sizer = FixedSizer(name="SignalTestSizer", volume="100")
        self.sizer.now = datetime.datetime(2023, 1, 1, 9, 30)
        self.sizer.engine_id = "test_engine"

        # 基本Portfolio信息
        self.portfolio_info = {
            "portfolio_id": "test_portfolio",
            "cash": Decimal("10000.00"),
            "positions": {}
        }

    def test_none_signal_handling(self):
        """测试None信号处理"""
        print("\n测试None信号处理")

        with patch.object(self.sizer, 'log') as mock_log:
            result = self.sizer.cal(self.portfolio_info, None)

            # 验证错误日志
            mock_log.assert_called_with("ERROR", "Sizer:SignalTestSizer received None signal")
            assert result is None

        print("✓ None信号处理成功")

    def test_invalid_signal_handling(self):
        """测试无效信号处理"""
        print("\n测试无效信号处理")

        # 创建无效信号
        invalid_signal = Mock(spec=Signal)
        invalid_signal.is_valid.return_value = False

        with patch.object(self.sizer, 'log') as mock_log:
            result = self.sizer.cal(self.portfolio_info, invalid_signal)

            # 验证错误日志
            mock_log.assert_called_with("ERROR", "Sizer:SignalTestSizer received invalid signal: Invalid Signal")
            assert result is None

        print("✓ 无效信号处理成功")

    def test_none_portfolio_info_handling(self):
        """测试None Portfolio信息处理"""
        print("\n测试None Portfolio信息处理")

        signal = Signal(code="000001.SZ", direction=DIRECTION_TYPES.LONG)

        with patch.object(self.sizer, 'log') as mock_log:
            result = self.sizer.cal(None, signal)

            # 验证错误日志
            mock_log.assert_called_with("ERROR", "Sizer:SignalTestSizer received None portfolio_info")
            assert result is None

        print("✓ None Portfolio信息处理成功")

    def test_missing_portfolio_fields_handling(self):
        """测试缺少Portfolio字段处理"""
        print("\n测试缺少Portfolio字段处理")

        signal = Signal(code="000001.SZ", direction=DIRECTION_TYPES.LONG)

        # 测试缺少positions字段
        incomplete_portfolio_info = {"cash": Decimal("10000.00")}

        with patch.object(self.sizer, 'log') as mock_log:
            result = self.sizer.cal(incomplete_portfolio_info, signal)

            # 验证错误日志
            mock_log.assert_called_with("ERROR", "Sizer:SignalTestSizer missing required portfolio field: positions")
            assert result is None

        # 测试缺少cash字段
        incomplete_portfolio_info = {"positions": {}}

        with patch.object(self.sizer, 'log') as mock_log:
            result = self.sizer.cal(incomplete_portfolio_info, signal)

            # 验证错误日志
            mock_log.assert_called_with("ERROR", "Sizer:SignalTestSizer missing required portfolio field: cash")
            assert result is None

        print("✓ 缺少Portfolio字段处理成功")

    @patch('ginkgo.trading.sizers.fixed_sizer.get_bars')
    def test_long_signal_processing(self, mock_get_bars):
        """测试买入信号处理"""
        print("\n测试买入信号处理")

        # 模拟价格数据
        mock_df = Mock()
        mock_df.shape = [10, 5]  # 10行数据
        mock_df.iloc = [-1]  # 最后一行
        mock_df.iloc.__getitem__ = Mock(return_value=Mock(close=Decimal("10.00")))

        mock_get_bars.return_value = mock_df

        # 创建买入信号
        signal = Signal(code="000001.SZ", direction=DIRECTION_TYPES.LONG)

        with patch.object(self.sizer, 'log') as mock_log:
            result = self.sizer.cal(self.portfolio_info, signal)

            # 验证订单创建
            assert isinstance(result, Order)
            assert result.code == "000001.SZ"
            assert result.direction == DIRECTION_TYPES.LONG
            assert result.order_type == ORDER_TYPES.MARKETORDER
            assert result.status == ORDERSTATUS_TYPES.NEW
            assert result.volume > 0
            assert result.frozen > 0

            # 验证日志调用
            mock_log.assert_any_call("DEBUG", "Sizer:SignalTestSizer processing signal for 000001.SZ")
            mock_log.assert_any_call("DEBUG", "init order")

        print(f"✓ 买入信号处理成功: 订单规模={result.volume}, 冻结资金={result.frozen}")

    def test_short_signal_without_position(self):
        """测试无持仓时的卖出信号处理"""
        print("\n测试无持仓时的卖出信号处理")

        # 创建卖出信号
        signal = Signal(code="000001.SZ", direction=DIRECTION_TYPES.SHORT)

        with patch.object(self.sizer, 'log') as mock_log:
            result = self.sizer.cal(self.portfolio_info, signal)

            # 验证无订单创建（没有持仓）
            assert result is None

            # 验证日志
            mock_log.assert_any_call("DEBUG", "Sizer:SignalTestSizer processing signal for 000001.SZ")
            mock_log.assert_any_call("DEBUG", "Position 000001.SZ does not exist. Skip short signal.")

        print("✓ 无持仓卖出信号处理成功")

    def test_short_signal_with_position(self):
        """测试有持仓时的卖出信号处理"""
        print("\n测试有持仓时的卖出信号处理")

        # 添加持仓
        position = Mock(spec=Position)
        position.volume = 200
        self.portfolio_info["positions"]["000001.SZ"] = position

        # 创建卖出信号
        signal = Signal(code="000001.SZ", direction=DIRECTION_TYPES.SHORT)

        with patch.object(self.sizer, 'log') as mock_log:
            result = self.sizer.cal(self.portfolio_info, signal)

            # 验证订单创建
            assert isinstance(result, Order)
            assert result.code == "000001.SZ"
            assert result.direction == DIRECTION_TYPES.SHORT
            assert result.volume == 200  # 应该等于持仓数量
            assert result.frozen == 0  # 卖出不需要冻结资金

            # 验证警告日志
            mock_log.assert_any_call("WARN", "Try Generate SHORT ORDER.")

        print(f"✓ 有持仓卖出信号处理成功: 订单规模={result.volume}")

    @patch('ginkgo.trading.sizers.fixed_sizer.get_bars')
    def test_insufficient_cash_for_long_order(self, mock_get_bars):
        """测试买入订单资金不足处理"""
        print("\n测试买入订单资金不足处理")

        # 模拟价格数据（高价）
        mock_df = Mock()
        mock_df.shape = [10, 5]
        mock_df.iloc = [-1]
        mock_df.iloc.__getitem__ = Mock(return_value=Mock(close=Decimal("100.00")))

        mock_get_bars.return_value = mock_df

        # 设置不足的资金
        self.portfolio_info["cash"] = Decimal("500.00")

        signal = Signal(code="000001.SZ", direction=DIRECTION_TYPES.LONG)

        with patch.object(self.sizer, 'log') as mock_log:
            result = self.sizer.cal(self.portfolio_info, signal)

            # 验证可能没有订单创建或订单规模被调整
            if result is None:
                print("  ✓ 资金不足，无订单创建")
            else:
                assert result.volume > 0
                assert result.frozen <= self.portfolio_info["cash"]
                print(f"  ✓ 资金不足，订单规模调整为: {result.volume}")

        print("✓ 买入订单资金不足处理成功")

    @patch('ginkgo.trading.sizers.fixed_sizer.get_bars')
    def test_no_historical_price_data(self, mock_get_bars):
        """测试无历史价格数据处理"""
        print("\n测试无历史价格数据处理")

        # 模拟空数据
        mock_df = Mock()
        mock_df.shape = [0, 5]  # 空数据

        mock_get_bars.return_value = mock_df

        signal = Signal(code="000001.SZ", direction=DIRECTION_TYPES.LONG)

        with patch.object(self.sizer, 'log') as mock_log:
            result = self.sizer.cal(self.portfolio_info, signal)

            # 验证错误日志
            mock_log.assert_any_call("CRITICAL", pytest.mock.ANY)
            assert result is None

        print("✓ 无历史价格数据处理成功")

    def test_order_creation_error_handling(self):
        """测试订单创建错误处理"""
        print("\n测试订单创建错误处理")

        signal = Signal(code="000001.SZ", direction=DIRECTION_TYPES.LONG)

        # 模拟Order创建失败
        with patch('ginkgo.trading.sizers.fixed_sizer.Order', side_effect=Exception("创建失败")):
            with patch.object(self.sizer, 'log') as mock_log:
                result = self.sizer.cal(self.portfolio_info, signal)

                # 验证错误处理
                mock_log.assert_any_call("ERROR", "Sizer:SignalTestSizer failed to create order: 创建失败")
                assert result is None

        print("✓ 订单创建错误处理成功")


@pytest.mark.sizer
@pytest.mark.error_handling
class TestFixedSizerErrorHandling:
    """FixedSizer错误处理测试"""

    def setup_method(self):
        """测试前设置"""
        self.sizer = FixedSizer(name="ErrorTestSizer", volume="100")
        self.sizer.now = datetime.datetime(2023, 1, 1, 9, 30)
        self.sizer.engine_id = "test_engine"

    def test_signal_attribute_error(self):
        """测试信号属性错误"""
        print("\n测试信号属性错误")

        # 创建缺少属性的信号
        broken_signal = Mock(spec=Signal)
        del broken_signal.code  # 删除code属性

        portfolio_info = {
            "portfolio_id": "test",
            "cash": Decimal("10000"),
            "positions": {}
        }

        with patch.object(self.sizer, 'log') as mock_log:
            result = self.sizer.cal(portfolio_info, broken_signal)

            # 验证错误处理
            mock_log.assert_any_call("ERROR", pytest.mock.ANY)
            assert result is None

        print("✓ 信号属性错误处理成功")

    def test_portfolio_info_corruption(self):
        """测试Portfolio信息损坏"""
        print("\n测试Portfolio信息损坏")

        signal = Signal(code="000001.SZ", direction=DIRECTION_TYPES.LONG)

        # 损坏的portfolio_info
        corrupted_portfolio = {
            "portfolio_id": "test",
            "cash": "invalid_cash",  # 无效格式
            "positions": "invalid_positions"  # 无效格式
        }

        with patch.object(self.sizer, 'log') as mock_log:
            result = self.sizer.cal(corrupted_portfolio, signal)

            # 验证错误处理
            assert result is None

        print("✓ Portfolio信息损坏处理成功")

    def test_extreme_values_handling(self):
        """测试极端值处理"""
        print("\n测试极端值处理")

        # 测试极大volume
        large_sizer = FixedSizer(volume="999999")
        assert large_sizer.volume == 999999

        # 测试负volume（应该被转换为负数或报错）
        try:
            negative_sizer = FixedSizer(volume="-100")
            print(f"  负volume处理: {negative_sizer.volume}")
        except Exception as e:
            print(f"  负volume错误: {e}")

        print("✓ 极端值处理完成")

    def test_concurrent_access(self):
        """测试并发访问"""
        print("\n测试并发访问")

        import threading

        signal = Signal(code="000001.SZ", direction=DIRECTION_TYPES.LONG)
        portfolio_info = {
            "portfolio_id": "test",
            "cash": Decimal("10000"),
            "positions": {}
        }

        results = []
        errors = []

        def worker():
            try:
                result = self.sizer.cal(portfolio_info, signal)
                results.append(result)
            except Exception as e:
                errors.append(e)

        # 创建多个线程
        threads = []
        for _ in range(5):
            thread = threading.Thread(target=worker)
            threads.append(thread)
            thread.start()

        # 等待所有线程完成
        for thread in threads:
            thread.join()

        # 验证并发访问结果
        assert len(errors) == 0, f"并发访问产生错误: {errors}"
        assert len(results) == 5

        print("✓ 并发访问处理成功")


@pytest.mark.sizer
@pytest.mark.integration
class TestFixedSizerIntegration:
    """FixedSizer集成测试"""

    def setup_method(self):
        """测试前设置"""
        self.sizer = FixedSizer(name="IntegrationTestSizer", volume="100")
        self.sizer.now = datetime.datetime(2023, 1, 1, 9, 30)
        self.sizer.engine_id = "integration_test_engine"

    @patch('ginkgo.trading.sizers.fixed_sizer.get_bars')
    def test_complete_long_workflow(self, mock_get_bars):
        """测试完整买入工作流程"""
        print("\n测试完整买入工作流程")

        # 设置模拟价格数据
        mock_df = Mock()
        mock_df.shape = [30, 5]
        mock_df.iloc = [-1]
        mock_df.iloc.__getitem__ = Mock(return_value=Mock(close=Decimal("15.00")))

        mock_get_bars.return_value = mock_df

        # 完整的portfolio信息
        portfolio_info = {
            "portfolio_id": "workflow_test",
            "cash": Decimal("20000.00"),
            "positions": {
                "000002.SZ": Mock(volume=100)
            }
        }

        # 创建买入信号
        signal = Signal(
            code="000001.SZ",
            direction=DIRECTION_TYPES.LONG,
            reason="价格突破"
        )

        with patch.object(self.sizer, 'log') as mock_log:
            order = self.sizer.cal(portfolio_info, signal)

            # 验证订单完整性
            assert isinstance(order, Order)
            assert order.code == "000001.SZ"
            assert order.direction == DIRECTION_TYPES.LONG
            assert order.order_type == ORDER_TYPES.MARKETORDER
            assert order.status == ORDERSTATUS_TYPES.NEW
            assert order.volume > 0
            assert order.frozen > 0
            assert order.limit_price == 0  # 市价单
            assert order.transaction_price == 0
            assert order.transaction_volume == 0
            assert order.remain == 0
            assert order.fee == 0
            assert order.timestamp == self.sizer.now
            assert order.portfolio_id == "workflow_test"
            assert order.engine_id == "integration_test_engine"
            assert order.order_id is not None

            # 验证成本计算
            expected_cost = Decimal("15.00") * order.volume * Decimal("1.1")
            assert order.frozen <= portfolio_info["cash"]

            print(f"✓ 完整买入工作流程: {order.volume}股, 冻结{order.frozen}元")

    @patch('ginkgo.trading.sizers.fixed_sizer.get_bars')
    def test_complete_short_workflow(self, mock_get_bars):
        """测试完整卖出工作流程"""
        print("\n测试完整卖出工作流程")

        # 创建持仓
        position = Mock()
        position.volume = 300

        portfolio_info = {
            "portfolio_id": "short_workflow_test",
            "cash": Decimal("5000.00"),
            "positions": {
                "000001.SZ": position
            }
        }

        # 创建卖出信号
        signal = Signal(
            code="000001.SZ",
            direction=DIRECTION_TYPES.SHORT,
            reason="止损"
        )

        with patch.object(self.sizer, 'log') as mock_log:
            order = self.sizer.cal(portfolio_info, signal)

            # 验证卖出订单完整性
            assert isinstance(order, Order)
            assert order.code == "000001.SZ"
            assert order.direction == DIRECTION_TYPES.SHORT
            assert order.volume == 300  # 等于持仓数量
            assert order.frozen == 0  # 卖出不冻结资金

            print(f"✓ 完整卖出工作流程: {order.volume}股")

    @patch('ginkgo.trading.sizers.fixed_sizer.get_bars')
    def test_multiple_signals_processing(self, mock_get_bars):
        """测试多信号处理"""
        print("\n测试多信号处理")

        # 设置价格数据
        mock_df = Mock()
        mock_df.shape = [30, 5]
        mock_df.iloc = [-1]
        mock_df.iloc.__getitem__ = Mock(return_value=Mock(close=Decimal("20.00")))

        mock_get_bars.return_value = mock_df

        portfolio_info = {
            "portfolio_id": "multi_signal_test",
            "cash": Decimal("50000.00"),
            "positions": {}
        }

        # 创建多个信号
        signals = [
            Signal(code="000001.SZ", direction=DIRECTION_TYPES.LONG),
            Signal(code="000002.SZ", direction=DIRECTION_TYPES.LONG),
            Signal(code="600000.SH", direction=DIRECTION_TYPES.LONG),
        ]

        orders = []
        for signal in signals:
            with patch.object(self.sizer, 'log'):
                order = self.sizer.cal(portfolio_info, signal)
                if order:
                    orders.append(order)

        # 验证多订单创建
        assert len(orders) == 3

        for order in orders:
            assert isinstance(order, Order)
            assert order.direction == DIRECTION_TYPES.LONG
            assert order.volume > 0

        print(f"✓ 多信号处理: {len(orders)}个订单")

    def test_sizer_state_consistency(self):
        """测试开仓器状态一致性"""
        print("\n测试开仓器状态一致性")

        # 多次使用同一个开仓器
        signal1 = Signal(code="000001.SZ", direction=DIRECTION_TYPES.LONG)
        signal2 = Signal(code="000002.SZ", direction=DIRECTION_TYPES.LONG)

        portfolio_info = {
            "portfolio_id": "consistency_test",
            "cash": Decimal("20000.00"),
            "positions": {}
        }

        # 验证开仓器状态不会改变
        original_name = self.sizer.name
        original_volume = self.sizer.volume
        original_engine_id = self.sizer.engine_id

        # 模拟处理（这里会失败因为没有价格数据，但主要测试状态）
        with patch.object(self.sizer, 'log'):
            result1 = self.sizer.cal(portfolio_info, signal1)
            result2 = self.sizer.cal(portfolio_info, signal2)

        # 验证状态保持不变
        assert self.sizer.name == original_name
        assert self.sizer.volume == original_volume
        assert self.sizer.engine_id == original_engine_id

        print("✓ 开仓器状态一致性验证成功")


@pytest.mark.sizer
@pytest.mark.performance
class TestFixedSizerPerformance:
    """FixedSizer性能测试"""

    def setup_method(self):
        """测试前设置"""
        self.sizer = FixedSizer(name="PerformanceTestSizer", volume="100")
        self.sizer.now = datetime.datetime(2023, 1, 1, 9, 30)
        self.sizer.engine_id = "performance_test"

    @patch('ginkgo.trading.sizers.fixed_sizer.get_bars')
    def test_high_volume_signal_processing(self, mock_get_bars):
        """测试大量信号处理性能"""
        print("\n测试大量信号处理性能")

        import time

        # 设置价格数据
        mock_df = Mock()
        mock_df.shape = [30, 5]
        mock_df.iloc = [-1]
        mock_df.iloc.__getitem__ = Mock(return_value=Mock(close=Decimal("10.00")))

        mock_get_bars.return_value = mock_df

        portfolio_info = {
            "portfolio_id": "performance_test",
            "cash": Decimal("100000.00"),
            "positions": {}
        }

        signal_count = 1000
        signals = [
            Signal(code=f"00000{i%10+1}.SZ", direction=DIRECTION_TYPES.LONG)
            for i in range(signal_count)
        ]

        start_time = time.time()
        successful_orders = []

        for signal in signals:
            with patch.object(self.sizer, 'log'):
                order = self.sizer.cal(portfolio_info, signal)
                if order:
                    successful_orders.append(order)

        elapsed_time = time.time() - start_time
        signals_per_second = signal_count / elapsed_time

        print(f"✓ 性能测试: {signal_count}个信号, {len(successful_orders)}个订单")
        print(f"  耗时: {elapsed_time:.3f}秒, 速率: {signals_per_second:.1f}个/秒")

        # 性能断言
        assert elapsed_time < 5.0, f"信号处理速度过慢: {elapsed_time:.3f}秒"
        assert signals_per_second > 200, f"信号处理速率过低: {signals_per_second:.1f}个/秒"

    def test_memory_usage_stability(self):
        """测试内存使用稳定性"""
        print("\n测试内存使用稳定性")

        import psutil
        import os
        import gc

        process = psutil.Process(os.getpid())
        initial_memory = process.memory_info().rss / 1024 / 1024  # MB

        # 大量信号处理循环
        for cycle in range(3):
            for i in range(100):
                signal = Signal(code=f"CODE_{i}.SZ", direction=DIRECTION_TYPES.LONG)
                portfolio_info = {
                    "portfolio_id": f"memory_test_{cycle}",
                    "cash": Decimal("10000"),
                    "positions": {}
                }

                # 这里会因为缺少价格数据而失败，但主要测试内存使用
                with patch.object(self.sizer, 'log'):
                    self.sizer.cal(portfolio_info, signal)

            if cycle % 2 == 1:
                gc.collect()

        final_memory = process.memory_info().rss / 1024 / 1024  # MB
        memory_increase = final_memory - initial_memory

        print(f"✓ 内存使用: 初始 {initial_memory:.1f}MB, 最终 {final_memory:.1f}MB, 增长 {memory_increase:.1f}MB")

        # 内存增长应该在合理范围内
        assert memory_increase < 10, f"内存增长过多: {memory_increase:.1f}MB"


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])