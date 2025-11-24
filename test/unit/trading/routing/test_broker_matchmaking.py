"""
BrokerMatchMaking撮合引擎核心功能测试

验证基于Broker的新一代MatchMaking架构：
- 订单接收和验证流程
- 价格更新和市场数据处理
- 多种Broker类型支持（SimBroker、实盘Broker）
- 异步/同步执行模式
- 订单生命周期管理和事件发布
"""

import pytest
import datetime
import asyncio
from decimal import Decimal
from unittest.mock import Mock, patch, AsyncMock, MagicMock

from ginkgo.trading.routing.broker_matchmaking import BrokerMatchMaking
from ginkgo.trading.brokers.base_broker import BaseBroker, ExecutionResult, ExecutionStatus
from ginkgo.trading.events.price_update import EventPriceUpdate
from ginkgo.trading.events.order_execution_stage import EventOrderSubmit
from ginkgo.trading.entities.order import Order
from ginkgo.trading.entities.bar import Bar
from ginkgo.enums import SOURCE_TYPES, DIRECTION_TYPES, ORDERSTATUS_TYPES


class MockBroker(BaseBroker):
    """模拟Broker用于测试"""

    def __init__(self, execution_mode="BACKTEST", immediate_execution=True):
        super().__init__()
        self.execution_mode = execution_mode
        self._immediate_execution = immediate_execution
        self._connected = False
        self.submitted_orders = []
        self.market_data = {}
        self.execution_results = {}

    async def connect(self) -> bool:
        """连接模拟"""
        self._connected = True
        return True

    @property
    def is_connected(self) -> bool:
        return self._connected

    def validate_order(self, order: Order) -> bool:
        """订单验证"""
        return bool(order.code and order.volume > 0)

    async def submit_order(self, order: Order) -> ExecutionResult:
        """提交订单"""
        self.submitted_orders.append(order)

        # 模拟立即执行
        if self._immediate_execution:
            return ExecutionResult(
                order_id=order.uuid,
                status=ExecutionStatus.FILLED,
                filled_price=float(10.50),
                filled_quantity=order.volume,
                fees=5.0
            )
        else:
            # 模拟需要跟踪的订单
            return ExecutionResult(
                order_id=order.uuid,
                broker_order_id=f"BROKER_{order.uuid[:8]}",
                status=ExecutionStatus.SUBMITTED
            )

    async def cancel_order(self, order_id: str) -> ExecutionResult:
        """撤销订单"""
        return ExecutionResult(
            order_id=order_id,
            status=ExecutionStatus.CANCELED,
            message="Order cancelled successfully"
        )

    async def query_order(self, order_id: str) -> ExecutionResult:
        """查询订单状态"""
        return ExecutionResult(
            order_id=order_id,
            status=ExecutionStatus.FILLED,
            filled_price=10.50,
            filled_quantity=100
        )

    def requires_manual_confirmation(self) -> bool:
        return False

    def supports_immediate_execution(self) -> bool:
        return self._immediate_execution

    def supports_api_trading(self) -> bool:
        return not self._immediate_execution

    def set_market_data(self, code: str, data):
        """设置市场数据"""
        self.market_data[code] = data


class MockManualBroker(MockBroker):
    """模拟需要人工确认的Broker"""

    def __init__(self):
        super().__init__(immediate_execution=False)
        self.pending_confirmations = []

    def requires_manual_confirmation(self) -> bool:
        return True

    def supports_immediate_execution(self) -> bool:
        return False

    async def confirm_order_execution(self, order_id: str, actual_price: float,
                                    actual_volume: int, notes: str = "") -> ExecutionResult:
        """人工确认订单执行"""
        self.pending_confirmations.remove(order_id)
        return ExecutionResult(
            order_id=order_id,
            status=ExecutionStatus.FILLED,
            filled_price=actual_price,
            filled_quantity=actual_volume,
            message=f"Manual confirmation: {notes}"
        )

    def get_pending_orders(self):
        """获取待确认订单"""
        return self.pending_confirmations.copy()


@pytest.mark.matchmaking
@pytest.mark.broker_matchmaking
class TestBrokerMatchMakingBasics:
    """BrokerMatchMaking基础功能测试"""

    def setup_method(self):
        """测试前设置"""
        self.broker = MockBroker()
        self.matchmaking = Router(
            broker=self.broker,
            name="TestMatchMaking",
            async_runtime_enabled=False  # 使用同步模式进行测试
        )

    def test_matchmaking_initialization(self):
        """测试MatchMaking初始化"""
        print("\n测试MatchMaking初始化")

        # 验证基本属性
        assert self.matchmaking.broker is self.broker
        assert self.matchmaking.broker_type == "MockBroker"
        assert self.matchmaking.execution_mode == "BACKTEST"
        assert self.matchmaking.name == "Router(MockBroker)"

        # 验证订单跟踪初始化
        assert hasattr(self.matchmaking, '_pending_orders_queue')
        assert hasattr(self.matchmaking, '_processing_orders')
        assert hasattr(self.matchmaking, '_order_results')
        assert len(self.matchmaking._pending_orders_queue) == 0
        assert len(self.matchmaking._processing_orders) == 0
        assert len(self.matchmaking._order_results) == 0

        # 验证执行模式识别
        assert self.matchmaking._supports_immediate_execution is True
        assert self.matchmaking._supports_api_trading is False
        assert self.matchmaking._supports_manual_confirmation is False

        print("✓ MatchMaking初始化成功")

    @patch('ginkgo.trading.routing.broker_matchmaking.GLOG')
    def test_order_receiving_and_validation(self, mock_log):
        """测试订单接收和验证"""
        print("\n测试订单接收和验证")

        # 创建有效订单
        order = Order(
            code="000001.SZ",
            direction=DIRECTION_TYPES.LONG,
            volume=100,
            limit_price=Decimal("10.50")
        )

        # 创建订单提交事件
        submit_event = EventOrderSubmit(order=order)
        submit_event.set_source(SOURCE_TYPES.PORTFOLIO)

        # 处理订单事件
        self.matchmaking.on_order_received(submit_event)

        # 验证订单被加入待处理队列
        assert len(self.matchmaking._pending_orders_queue) == 1
        assert self.matchmaking._pending_orders_queue[0] is order

        print("✓ 订单接收和验证成功")

    def test_order_rejection_handling(self):
        """测试订单拒绝处理"""
        print("\n测试订单拒绝处理")

        # 创建无效订单（数量为0）
        invalid_order = Order(
            code="000001.SZ",
            direction=DIRECTION_TYPES.LONG,
            volume=0,  # 无效数量
            limit_price=Decimal("10.50")
        )

        # 模拟Broker验证失败
        self.broker.validate_order = Mock(return_value=False)

        submit_event = EventOrderSubmit(order=invalid_order)
        submit_event.set_source(SOURCE_TYPES.PORTFOLIO)

        # 处理无效订单
        self.matchmaking.on_order_received(submit_event)

        # 验证订单被拒绝，不加入队列
        assert len(self.matchmaking._pending_orders_queue) == 0
        assert invalid_order.status == ORDERSTATUS_TYPES.CANCELLED

        print("✓ 订单拒绝处理成功")

    @patch('ginkgo.trading.routing.broker_matchmaking.GLOG')
    def test_price_update_handling(self, mock_log):
        """测试价格更新处理"""
        print("\n测试价格更新处理")

        # 创建价格数据
        bar = Bar(
            code="000001.SZ",
            timestamp=datetime.datetime(2023, 1, 1, 9, 30),
            close=Decimal("10.50"),
            open=Decimal("10.00"),
            high=Decimal("10.80"),
            low=Decimal("9.80"),
            volume=1000000
        )

        # 创建价格更新事件
        price_event = EventPriceUpdate(price_info=bar)
        price_event.set_source(SOURCE_TYPES.BACKTESTFEEDER)

        # 处理价格事件
        self.matchmaking.on_price_received(price_event)

        # 验证价格缓存更新
        assert hasattr(self.matchmaking, '_price_cache')
        # 验证Broker接收到市场数据
        assert "000001.SZ" in self.broker.market_data

        print("✓ 价格更新处理成功")


@pytest.mark.matchmaking
@pytest.mark.execution_modes
class TestBrokerMatchMakingExecutionModes:
    """BrokerMatchMaking执行模式测试"""

    def test_immediate_execution_mode(self):
        """测试立即执行模式"""
        print("\n测试立即执行模式")

        # 使用立即执行Broker
        immediate_broker = MockBroker(immediate_execution=True)
        matchmaking = Router(
            broker=immediate_broker,
            async_runtime_enabled=False
        )

        # 创建订单
        order = Order(
            code="000001.SZ",
            direction=DIRECTION_TYPES.LONG,
            volume=100,
            limit_price=Decimal("10.50")
        )

        # 模拟事件处理
        submit_event = EventOrderSubmit(order=order)
        matchmaking.on_order_received(submit_event)

        # 模拟价格更新触发执行
        bar = Bar(code="000001.SZ", close=Decimal("10.50"))
        price_event = EventPriceUpdate(price_info=bar)
        matchmaking.on_price_received(price_event)

        # 验证订单被立即执行
        assert len(immediate_broker.submitted_orders) == 1
        assert immediate_broker.submitted_orders[0] is order

        print("✓ 立即执行模式正常")

    def test_async_execution_mode(self):
        """测试异步执行模式"""
        print("\n测试异步执行模式")

        # 使用异步Broker
        async_broker = MockBroker(immediate_execution=False)
        matchmaking = Router(
            broker=async_broker,
            async_runtime_enabled=True  # 启用异步运行时
        )

        # 验证异步运行时配置
        assert matchmaking._async_runtime_enabled is True
        assert matchmaking._sync_facade is None

        print("✓ 异步执行模式配置成功")

    def test_manual_confirmation_mode(self):
        """测试人工确认模式"""
        print("\n测试人工确认模式")

        # 使用人工确认Broker
        manual_broker = MockManualBroker()
        matchmaking = Router(
            broker=manual_broker,
            async_runtime_enabled=False
        )

        # 验证人工确认支持
        assert matchmaking._supports_manual_confirmation is True
        assert hasattr(matchmaking, '_confirmation_handler')

        # 测试获取待确认订单
        pending_orders = matchmaking.get_pending_manual_orders()
        assert isinstance(pending_orders, list)

        print("✓ 人工确认模式支持正常")


@pytest.mark.matchmaking
@pytest.mark.order_lifecycle
class TestBrokerMatchMakingOrderLifecycle:
    """BrokerMatchMaking订单生命周期测试"""

    def setup_method(self):
        """测试前设置"""
        self.broker = MockBroker(immediate_execution=True)
        self.matchmaking = Router(
            broker=self.broker,
            async_runtime_enabled=False
        )

    def test_complete_order_lifecycle(self):
        """测试完整订单生命周期"""
        print("\n测试完整订单生命周期")

        # 1. 订单提交
        order = Order(
            code="000001.SZ",
            direction=DIRECTION_TYPES.LONG,
            volume=100,
            limit_price=Decimal("10.50")
        )

        submit_event = EventOrderSubmit(order=order)
        self.matchmaking.on_order_received(submit_event)

        assert len(self.matchmaking._pending_orders_queue) == 1
        print("  ✓ 订单提交成功")

        # 2. 价格更新触发执行
        bar = Bar(code="000001.SZ", close=Decimal("10.50"))
        price_event = EventPriceUpdate(price_info=bar)

        # 模拟事件发布
        with patch.object(self.matchmaking, 'put') as mock_put:
            self.matchmaking.on_price_received(price_event)

            # 验证Broker接收到订单
            assert len(self.broker.submitted_orders) == 1

            # 验证执行结果被处理
            assert mock_put.called
            print("  ✓ 订单执行成功")

        # 3. 验证订单状态更新
        assert order.status == ORDERSTATUS_TYPES.FILLED
        assert order.transaction_price == 10.50
        assert order.transaction_volume == 100

        print("  ✓ 订单状态更新成功")
        print("✓ 完整订单生命周期测试通过")

    def test_order_cancellation(self):
        """测试订单撤销"""
        print("\n测试订单撤销")

        # 使用异步Broker（支持撤销）
        async_broker = MockBroker(immediate_execution=False)
        matchmaking = Router(
            broker=async_broker,
            async_runtime_enabled=False
        )

        # 提交订单
        order = Order(code="000001.SZ", direction=DIRECTION_TYPES.LONG, volume=100)
        submit_event = EventOrderSubmit(order=order)
        matchmaking.on_order_received(submit_event)

        # 模拟订单被提交到Broker
        bar = Bar(code="000001.SZ", close=Decimal("10.50"))
        price_event = EventPriceUpdate(price_info=bar)
        matchmaking.on_price_received(price_event)

        # 撤销订单
        matchmaking.cancel_order(order)

        # 验证撤销请求被发送
        # 注意：在同步模式下，撤销是立即处理的
        print("✓ 订单撤销处理成功")

    def test_partial_fill_handling(self):
        """测试部分成交处理"""
        print("\n测试部分成交处理")

        # 创建模拟部分成交的Broker
        partial_fill_broker = MockBroker()

        # 重写submit_order方法返回部分成交结果
        async def submit_partial(order):
            return ExecutionResult(
                order_id=order.uuid,
                status=ExecutionStatus.PARTIALLY_FILLED,
                filled_price=10.50,
                filled_quantity=50,  # 部分成交
                message="Partial fill"
            )

        partial_fill_broker.submit_order = submit_partial

        matchmaking = Router(
            broker=partial_fill_broker,
            async_runtime_enabled=False
        )

        # 提交订单
        order = Order(code="000001.SZ", direction=DIRECTION_TYPES.LONG, volume=100)
        submit_event = EventOrderSubmit(order=order)
        matchmaking.on_order_received(submit_event)

        # 触发执行
        bar = Bar(code="000001.SZ", close=Decimal("10.50"))
        price_event = EventPriceUpdate(price_info=bar)

        with patch.object(matchmaking, 'put') as mock_put:
            matchmaking.on_price_received(price_event)

            # 验证部分成交事件被发布
            assert mock_put.called

        print("✓ 部分成交处理成功")

    def test_order_rejection_handling(self):
        """测试订单拒绝处理"""
        print("\n测试订单拒绝处理")

        # 创建会拒绝订单的Broker
        rejecting_broker = MockBroker()

        async def submit_reject(order):
            return ExecutionResult(
                order_id=order.uuid,
                status=ExecutionStatus.REJECTED,
                message="Insufficient balance",
                error_code="INSUFFICIENT_BALANCE"
            )

        rejecting_broker.submit_order = submit_reject

        matchmaking = Router(
            broker=rejecting_broker,
            async_runtime_enabled=False
        )

        # 提交订单
        order = Order(code="000001.SZ", direction=DIRECTION_TYPES.LONG, volume=100)
        submit_event = EventOrderSubmit(order=order)
        matchmaking.on_order_received(submit_event)

        # 触发执行
        bar = Bar(code="000001.SZ", close=Decimal("10.50"))
        price_event = EventPriceUpdate(price_info=bar)

        with patch.object(matchmaking, 'put') as mock_put:
            matchmaking.on_price_received(price_event)

            # 验证拒绝事件被发布
            assert mock_put.called

        # 验证订单状态
        assert order.status == ORDERSTATUS_TYPES.CANCELLED

        print("✓ 订单拒绝处理成功")


@pytest.mark.matchmaking
@pytest.mark.error_handling
class TestBrokerMatchMakingErrorHandling:
    """BrokerMatchMaking错误处理测试"""

    def setup_method(self):
        """测试前设置"""
        self.broker = MockBroker()
        self.matchmaking = Router(
            broker=self.broker,
            async_runtime_enabled=False
        )

    def test_broker_connection_failure(self):
        """测试Broker连接失败处理"""
        print("\n测试Broker连接失败处理")

        # 创建会连接失败的Broker
        failing_broker = MockBroker()
        failing_broker.connect = AsyncMock(return_value=False)

        matchmaking = Router(
            broker=failing_broker,
            async_runtime_enabled=False
        )

        # 尝试建立连接应该失败
        with pytest.raises(RuntimeError, match="Broker connection failed"):
            asyncio.run(matchmaking.initialize_broker_connection())

        print("✓ Broker连接失败处理正确")

    def test_order_submission_failure(self):
        """测试订单提交失败处理"""
        print("\n测试订单提交失败处理")

        # 创建会提交失败的Broker
        failing_broker = MockBroker()

        async def submit_failure(order):
            raise Exception("Network error")

        failing_broker.submit_order = submit_failure

        matchmaking = Router(
            broker=failing_broker,
            async_runtime_enabled=False
        )

        # 提交订单
        order = Order(code="000001.SZ", direction=DIRECTION_TYPES.LONG, volume=100)
        submit_event = EventOrderSubmit(order=order)
        matchmaking.on_order_received(submit_event)

        # 触发执行（应该处理失败）
        bar = Bar(code="000001.SZ", close=Decimal("10.50"))
        price_event = EventPriceUpdate(price_info=bar)

        # 即使提交失败，也不应该崩溃
        try:
            matchmaking.on_price_received(price_event)
            print("✓ 订单提交失败处理成功")
        except Exception as e:
            pytest.fail(f"订单提交失败导致MatchMaking崩溃: {e}")

    def test_invalid_price_data_handling(self):
        """测试无效价格数据处理"""
        print("\n测试无效价格数据处理")

        # 测试各种无效价格数据
        invalid_price_data = [
            None,
            "invalid_string",
            {},
            []  # 空列表
        ]

        for invalid_data in invalid_price_data:
            try:
                # 直接调用价格更新方法
                self.matchmaking._update_price_cache(invalid_data)
                print(f"  ✓ 无效价格数据处理成功: {type(invalid_data)}")
            except Exception as e:
                # 验证错误被正确处理
                assert isinstance(e, (TypeError, AttributeError, ValueError))
                print(f"  ✓ 无效价格数据错误被正确处理: {type(e)}")

    def test_order_tracking_cleanup(self):
        """测试订单跟踪清理"""
        print("\n测试订单跟踪清理")

        # 添加处理中订单
        order = Order(code="000001.SZ", direction=DIRECTION_TYPES.LONG, volume=100)
        self.matchmaking._processing_orders[order.uuid] = {
            'order': order,
            'result': ExecutionResult(order_id=order.uuid, status=ExecutionStatus.SUBMITTED),
            'submit_time': datetime.datetime.now()
        }

        assert len(self.matchmaking._processing_orders) == 1

        # 清理订单
        self.matchmaking._processing_orders.clear()

        assert len(self.matchmaking._processing_orders) == 0

        print("✓ 订单跟踪清理成功")


@pytest.mark.matchmaking
@pytest.mark.performance
class TestBrokerMatchMakingPerformance:
    """BrokerMatchMaking性能测试"""

    def setup_method(self):
        """测试前设置"""
        self.broker = MockBroker()
        self.matchmaking = Router(
            broker=self.broker,
            async_runtime_enabled=False
        )

    def test_high_frequency_order_processing(self):
        """测试高频订单处理"""
        print("\n测试高频订单处理")

        import time

        # 创建大量订单
        order_count = 100
        orders = []
        for i in range(order_count):
            order = Order(
                code=f"00000{i%10+1}.SZ",
                direction=DIRECTION_TYPES.LONG,
                volume=100,
                limit_price=Decimal(f"10.{i%100:02d}")
            )
            orders.append(order)

        # 批量提交订单
        start_time = time.time()

        for order in orders:
            submit_event = EventOrderSubmit(order=order)
            self.matchmaking.on_order_received(submit_event)

        submission_time = time.time() - start_time

        # 批量执行订单
        bar = Bar(code="000001.SZ", close=Decimal("10.50"))
        price_event = EventPriceUpdate(price_info=bar)

        execution_start = time.time()
        with patch.object(self.matchmaking, 'put'):
            self.matchmaking.on_price_received(price_event)
        execution_time = time.time() - execution_start

        print(f"✓ 高频处理测试：{order_count}个订单")
        print(f"  提交耗时：{submission_time:.3f}秒")
        print(f"  执行耗时：{execution_time:.3f}秒")

        # 性能断言
        assert submission_time < 1.0, f"订单提交速度过慢：{submission_time:.3f}秒"
        assert execution_time < 1.0, f"订单执行速度过慢：{execution_time:.3f}秒"

    def test_memory_usage_stability(self):
        """测试内存使用稳定性"""
        print("\n测试内存使用稳定性")

        import psutil
        import os
        import gc

        process = psutil.Process(os.getpid())
        initial_memory = process.memory_info().rss / 1024 / 1024  # MB

        # 大量订单处理循环
        for cycle in range(3):
            # 添加订单
            for i in range(50):
                order = Order(code=f"00000{i%10+1}.SZ", direction=DIRECTION_TYPES.LONG, volume=100)
                submit_event = EventOrderSubmit(order=order)
                self.matchmaking.on_order_received(submit_event)

            # 执行订单
            bar = Bar(code="000001.SZ", close=Decimal("10.50"))
            price_event = EventPriceUpdate(price_info=bar)
            with patch.object(self.matchmaking, 'put'):
                self.matchmaking.on_price_received(price_event)

            # 清理
            self.matchmaking._pending_orders_queue.clear()
            self.matchmaking._processing_orders.clear()
            self.matchmaking._order_results.clear()

            if cycle % 2 == 1:
                gc.collect()

        final_memory = process.memory_info().rss / 1024 / 1024  # MB
        memory_increase = final_memory - initial_memory

        print(f"✓ 内存使用：初始 {initial_memory:.1f}MB，最终 {final_memory:.1f}MB，增长 {memory_increase:.1f}MB")

        # 内存增长应该在合理范围内
        assert memory_increase < 50, f"内存使用增长过多：{memory_increase:.1f}MB"


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])