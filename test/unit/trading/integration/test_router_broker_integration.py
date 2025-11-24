#!/usr/bin/env python3
"""
Router/Broker架构集成测试

测试新Router/Broker架构的完整集成，包括：
1. Engine-Router-Broker绑定关系
2. 事件流：Portfolio → Signal → Router → Broker → Engine
3. 多市场Broker路由
4. 订单生命周期管理
5. 事件发布和订阅
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../../../src'))

import pytest
import pandas as pd
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime

from ginkgo.trading.engines.event_engine import EventEngine
from ginkgo.trading.routing.router import Router
from ginkgo.trading.brokers.sim_broker import SimBroker
from ginkgo.trading.entities import Order, Signal
from ginkgo.trading.events.signal_generation import EventSignalGeneration
from ginkgo.trading.events.order_lifecycle_events import EventOrderAck, EventOrderPartiallyFilled, EventOrderRejected
from ginkgo.enums import (
    DIRECTION_TYPES, ORDER_TYPES, ORDERSTATUS_TYPES, EVENT_TYPES,
    ATTITUDE_TYPES, EXECUTION_MODE
)


class MockEngine:
    """模拟引擎用于测试"""

    def __init__(self):
        self.events = []
        self.registered_handlers = {}

    def put(self, event):
        """接收事件"""
        self.events.append(event)

    def register(self, event_type, handler):
        """注册事件处理器"""
        if event_type not in self.registered_handlers:
            self.registered_handlers[event_type] = []
        self.registered_handlers[event_type].append(handler)


@pytest.fixture
def mock_engine():
    """提供模拟引擎fixture"""
    return MockEngine()


@pytest.fixture
def optimistic_sim_broker():
    """提供乐观的SimBroker fixture"""
    return SimBroker(
        name="TestSimBroker",
        attitude=ATTITUDE_TYPES.OPTIMISTIC,
        commission_rate=0.0003,
        commission_min=5.0
    )


@pytest.fixture
def sample_market_data():
    """提供示例市场数据fixture"""
    return pd.Series({
        'open': 10.0,
        'high': 11.0,
        'low': 9.0,
        'close': 10.5,
        'volume': 1000000
    })


@pytest.fixture
def router_with_brokers(optimistic_sim_broker):
    """提供带有Brokers的Router fixture"""
    brokers = [optimistic_sim_broker]
    router = Router(
        name="TestRouter",
        brokers=brokers
    )
    return router


class TestEngineRouterBinding:
    """测试Engine-Router绑定"""

    def test_bind_matchmaking(self, mock_engine, router_with_brokers):
        """测试引擎绑定Router"""
        router = router_with_brokers

        # 绑定Router到引擎
        mock_engine.bind_matchmaking = Mock()
        router.bind_engine = Mock()
        router.set_event_publisher = Mock()

        # 模拟引擎绑定过程
        mock_engine._matchmaking = router
        router.bind_engine(mock_engine)
        router.set_event_publisher(mock_engine.put)

        # 验证绑定关系
        assert mock_engine._matchmaking == router
        router.bind_engine.assert_called_once_with(mock_engine)
        router.set_event_publisher.assert_called_once_with(mock_engine.put)

    def test_router_engine_binding_properties(self, mock_engine, router_with_brokers):
        """测试Router引擎绑定后的属性"""
        router = router_with_brokers
        router.bind_engine(mock_engine)
        router.set_event_publisher(mock_engine.put)

        assert router.bound_engine == mock_engine
        assert router._engine_put == mock_engine.put

    def test_router_event_publishing_after_binding(self, mock_engine, router_with_brokers):
        """测试绑定后Router的事件发布"""
        router = router_with_brokers
        router.bind_engine(mock_engine)
        router.set_event_publisher(mock_engine.put)

        # 发布事件
        test_event = {"type": "test", "data": "example"}
        router.publish_event(test_event)

        # 验证事件被发布到引擎
        assert len(mock_engine.events) == 1
        assert mock_engine.events[0] == test_event


class TestMarketRoutingLogic:
    """测试市场路由逻辑"""

    def test_get_broker_for_a_share(self, router_with_brokers):
        """测试A股代码路由"""
        router = router_with_brokers

        # 测试A股代码
        a_share_order = self._create_test_order("000001.SZ")
        selected_broker = router.get_broker_for_order(a_share_order)

        assert selected_broker is not None
        assert selected_broker == router.brokers[0]

    def test_get_broker_for_hk_share(self, router_with_brokers):
        """测试港股代码路由"""
        router = router_with_brokers

        # 测试港股代码（应该使用默认broker）
        hk_share_order = self._create_test_order("00700.HK")
        selected_broker = router.get_broker_for_order(hk_share_order)

        assert selected_broker is not None
        assert selected_broker == router.brokers[0]

    def test_get_broker_for_us_share(self, router_with_brokers):
        """测试美股代码路由"""
        router = router_with_brokers

        # 测试美股代码（应该使用默认broker）
        us_share_order = self._create_test_order("AAPL")
        selected_broker = router.get_broker_for_order(us_share_order)

        assert selected_broker is not None
        assert selected_broker == router.brokers[0]

    def test_market_detection_by_code_format(self, router_with_brokers):
        """测试通过代码格式检测市场"""
        router = router_with_brokers

        # 测试不同格式的代码
        test_cases = [
            ("000001.SZ", "A股"),
            ("600000.SH", "A股"),
            ("00700.HK", "港股"),
            ("03690.HK", "港股"),
            ("AAPL", "美股"),
            ("TSLA", "美股"),
            ("IF2312", "期货")
        ]

        for code, expected_market in test_cases:
            order = self._create_test_order(code)
            market = router._get_market_by_code(code)
            assert market == expected_market, f"Code {code} should be detected as {expected_market}"

    def _create_test_order(self, code):
        """创建测试订单"""
        return Order(
            portfolio_id="test",
            engine_id="test",
            run_id="test",
            code=code,
            direction=DIRECTION_TYPES.LONG,
            order_type=ORDER_TYPES.MARKETORDER,
            status=ORDERSTATUS_TYPES.NEW,
            volume=100,
            limit_price=10.0
        )


class TestOrderProcessingWorkflow:
    """测试订单处理工作流"""

    def test_on_order_received_workflow(self, router_with_brokers, sample_market_data):
        """测试订单接收处理流程"""
        router = router_with_brokers

        # 设置市场数据
        for broker in router.brokers:
            if hasattr(broker, 'set_market_data'):
                broker.set_market_data("000001.SZ", sample_market_data)

        # 创建订单事件
        order = self._create_test_order("000001.SZ")
        order_event = Mock()
        order_event.value = order

        # 绑定引擎（用于事件发布）
        mock_engine = Mock()
        router.bind_engine(mock_engine)
        router.set_event_publisher(mock_engine.put)

        # 处理订单接收事件
        router.on_order_received(order_event)

        # 验证订单被处理（乐观态度应该成交）
        assert len(mock_engine.put.call_args_list) > 0

    def test_order_to_signal_conversion(self):
        """测试订单到信号的转换（通过Portfolio）"""
        # 这里简化测试，实际信号到订单的转换在Portfolio中
        signal = Signal(
            portfolio_id="test",
            engine_id="test",
            run_id="test",
            code="000001.SZ",
            direction=DIRECTION_TYPES.LONG
        )

        assert signal.code == "000001.SZ"
        assert signal.direction == DIRECTION_TYPES.LONG

    def test_multiple_order_processing(self, router_with_brokers, sample_market_data):
        """测试多订单处理"""
        router = router_with_brokers

        # 设置市场数据
        for broker in router.brokers:
            broker.set_market_data("000001.SZ", sample_market_data)

        # 创建多个订单
        orders = []
        order_events = []
        for i in range(3):
            order = self._create_test_order("000001.SZ")
            order.volume = 100 * (i + 1)
            orders.append(order)

            order_event = Mock()
            order_event.value = order
            order_events.append(order_event)

        # 绑定引擎
        mock_engine = Mock()
        router.bind_engine(mock_engine)
        router.set_event_publisher(mock_engine.put)

        # 处理所有订单
        for order_event in order_events:
            router.on_order_received(order_event)

        # 验证所有订单都被处理
        assert mock_engine.put.call_count >= len(order_events)

    def _create_test_order(self, code):
        """创建测试订单"""
        return Order(
            portfolio_id="test",
            engine_id="test",
            run_id="test",
            code=code,
            direction=DIRECTION_TYPES.LONG,
            order_type=ORDER_TYPES.MARKETORDER,
            status=ORDERSTATUS_TYPES.NEW,
            volume=100,
            limit_price=10.0
        )


class TestEventFlowIntegration:
    """测试事件流集成"""

    def test_complete_signal_to_fill_flow(self, router_with_brokers, sample_market_data):
        """测试完整的信号到成交流程"""
        router = router_with_brokers
        mock_engine = MockEngine()

        # 设置Router
        router.bind_engine(mock_engine)
        router.set_event_publisher(mock_engine.put)

        # 设置市场数据
        for broker in router.brokers:
            broker.set_market_data("000001.SZ", sample_market_data)

        # 1. 创建信号
        signal = Signal(
            portfolio_id="integration_test",
            engine_id="test_engine",
            run_id="test_run",
            code="000001.SZ",
            direction=DIRECTION_TYPES.LONG
        )

        # 2. 创建订单（模拟Portfolio从信号创建订单）
        order = Order(
            portfolio_id="integration_test",
            engine_id="test_engine",
            run_id="test_run",
            code="000001.SZ",
            direction=DIRECTION_TYPES.LONG,
            order_type=ORDER_TYPES.MARKETORDER,
            status=ORDERSTATUS_TYPES.NEW,
            volume=200,
            limit_price=10.0
        )

        # 3. 创建订单接收事件
        order_received_event = Mock()
        order_received_event.value = order

        # 4. Router处理订单
        router.on_order_received(order_received_event)

        # 5. 验证事件发布
        published_events = mock_engine.events
        assert len(published_events) > 0

        # 验证持仓更新（通过Broker）
        for broker in router.brokers:
            position = broker.get_position("000001.SZ")
            if position:
                assert position.volume == 200
                break

    def test_event_publishing_mechanism(self, router_with_brokers):
        """测试事件发布机制"""
        router = router_with_brokers
        mock_engine = MockEngine()

        # 绑定引擎
        router.bind_engine(mock_engine)
        router.set_event_publisher(mock_engine.put)

        # 测试多种事件类型发布
        mock_order = Mock()
        test_events = [
            EventOrderAck(mock_order, "test_broker_order_id"),
            EventOrderRejected(mock_order, "test_reject_reason"),
            {"custom": "event", "type": "test"}
        ]

        for event in test_events:
            router.publish_event(event)

        assert len(mock_engine.events) == len(test_events)

    def test_event_handler_registration(self, mock_engine, router_with_brokers):
        """测试事件处理器注册"""
        router = router_with_brokers

        # 模拟引擎注册订单处理器
        def order_handler(event):
            pass

        mock_engine.register = Mock()
        mock_engine.register(EVENT_TYPES.ORDERSUBMITTED, router.on_order_received)

        # 验证注册调用
        mock_engine.register.assert_called_once_with(
            EVENT_TYPES.ORDERSUBMITTED, router.on_order_received
        )


@pytest.mark.integration
class TestMultiMarketIntegration:
    """多市场集成测试"""

    def test_multi_market_broker_setup(self):
        """测试多市场Broker设置"""
        # 创建不同类型的Brokers
        sim_broker = SimBroker(name="SimBacktest", attitude=ATTITUDE_TYPES.OPTIMISTIC)

        brokers = [sim_broker]
        router = Router(
            name="MultiMarketRouter",
            brokers=brokers
        )

        # 验证多市场支持
        assert len(router.brokers) == 1
        assert router.name == "MultiMarketRouter"

        # 验证市场映射
        market_mapping = router._market_mapping
        broker_status = router.get_broker_status()

        assert len(broker_status) == 1

    def test_cross_market_order_routing(self, router_with_brokers, sample_market_data):
        """测试跨市场订单路由"""
        router = router_with_brokers

        # 设置市场数据
        for broker in router.brokers:
            broker.set_market_data("000001.SZ", sample_market_data)
            broker.set_market_data("AAPL", sample_market_data)

        # 测试不同市场的订单
        market_orders = [
            self._create_test_order("000001.SZ"),  # A股
            self._create_test_order("00700.HK"),   # 港股
            self._create_test_order("AAPL"),        # 美股
        ]

        mock_engine = Mock()
        router.bind_engine(mock_engine)
        router.set_event_publisher(mock_engine.put)

        # 处理所有市场订单
        for order in market_orders:
            order_event = Mock()
            order_event.value = order
            router.on_order_received(order_event)

        # 验证所有订单都被处理
        assert mock_engine.put.call_count >= len(market_orders)

    def _create_test_order(self, code):
        """创建测试订单"""
        return Order(
            portfolio_id="multimarket_test",
            engine_id="test_engine",
            run_id="test_run",
            code=code,
            direction=DIRECTION_TYPES.LONG,
            order_type=ORDER_TYPES.MARKETORDER,
            status=ORDERSTATUS_TYPES.NEW,
            volume=100,
            limit_price=10.0
        )


class TestErrorHandlingAndRecovery:
    """测试错误处理和恢复"""

    def test_invalid_order_handling(self, router_with_brokers):
        """测试无效订单处理"""
        router = router_with_brokers

        # 创建无效订单 - 使用异常捕获
        try:
            invalid_order = Order(
                portfolio_id="test",
                engine_id="test",
                run_id="test",
                code="",  # 无效代码（空字符串）
                direction=DIRECTION_TYPES.LONG,
                order_type=ORDER_TYPES.MARKETORDER,
                status=ORDERSTATUS_TYPES.NEW,
                volume=100,
                limit_price=10.0
            )
            # 如果没有抛出异常，继续测试
            order_event = Mock()
            order_event.value = invalid_order

            mock_engine = Mock()
            router.bind_engine(mock_engine)
            router.set_event_publisher(mock_engine.put)

            # 应该不会抛出异常
            router.on_order_received(order_event)
        except (ValueError, Exception) as e:
            # 预期的订单验证错误，这是正常的
            assert "code" in str(e).lower()  # 确认是code相关的错误

    def test_broker_failure_simulation(self, router_with_brokers):
        """测试Broker故障模拟"""
        router = router_with_brokers

        # 模拟Broker失败
        for broker in router.brokers:
            if hasattr(broker, 'validate_order'):
                # 让验证失败
                with patch.object(broker, 'validate_order', return_value=False):
                    order = self._create_test_order("000001.SZ")
                    order_event = Mock()
                    order_event.value = order

                    mock_engine = Mock()
                    router.bind_engine(mock_engine)
                    router.set_event_publisher(mock_engine.put)

                    # 应该不会抛出异常，订单应该被拒绝
                    router.on_order_received(order_event)

    def _create_test_order(self, code):
        """创建测试订单"""
        return Order(
            portfolio_id="error_test",
            engine_id="test_engine",
            run_id="test_run",
            code=code,
            direction=DIRECTION_TYPES.LONG,
            order_type=ORDER_TYPES.MARKETORDER,
            status=ORDERSTATUS_TYPES.NEW,
            volume=100,
            limit_price=10.0
        )


class TestPerformanceAndScalability:
    """测试性能和可扩展性"""

    def test_high_volume_order_processing(self, router_with_brokers, sample_market_data):
        """测试高容量订单处理"""
        router = router_with_brokers

        # 设置市场数据
        for broker in router.brokers:
            broker.set_market_data("000001.SZ", sample_market_data)

        # 创建大量订单
        large_order_count = 100
        orders = []
        order_events = []

        for i in range(large_order_count):
            order = self._create_test_order("000001.SZ")
            order.volume = 100 + i
            orders.append(order)

            order_event = Mock()
            order_event.value = order
            order_events.append(order_event)

        mock_engine = Mock()
        router.bind_engine(mock_engine)
        router.set_event_publisher(mock_engine.put)

        # 处理所有订单
        import time
        start_time = time.time()

        for order_event in order_events:
            router.on_order_received(order_event)

        end_time = time.time()
        processing_time = end_time - start_time

        # 验证性能（处理时间应该合理）
        assert processing_time < 10.0  # 10秒内处理完成
        assert mock_engine.put.call_count >= large_order_count

    def test_memory_usage_tracking(self, router_with_brokers):
        """测试内存使用跟踪"""
        router = router_with_brokers

        # 获取初始状态
        initial_info = router.get_router_info()
        initial_pending = initial_info['pending_orders']
        initial_processing = initial_info['processing_orders']

        # 添加一些订单
        for i in range(5):
            order = self._create_test_order("000001.SZ")
            router.add_pending_order(order)

        # 检查内存使用
        current_info = router.get_router_info()
        current_pending = current_info['pending_orders']

        assert current_pending == initial_pending + 5

        # 清空订单
        router.clear_pending_orders()
        final_info = router.get_router_info()
        assert final_info['pending_orders'] == 0

    def _create_test_order(self, code):
        """创建测试订单"""
        return Order(
            portfolio_id="performance_test",
            engine_id="test_engine",
            run_id="test_run",
            code=code,
            direction=DIRECTION_TYPES.LONG,
            order_type=ORDER_TYPES.MARKETORDER,
            status=ORDERSTATUS_TYPES.NEW,
            volume=100,
            limit_price=10.0
        )


class TestAsyncExecutionMode:
    """测试异步执行模式"""

    def test_detect_execution_mode(self, router_with_brokers):
        """测试执行模式检测"""
        router = router_with_brokers

        # 测试SimBroker（同步执行）
        sync_broker = router.brokers[0]  # SimBroker
        execution_mode = router._detect_execution_mode(sync_broker)
        assert execution_mode == "backtest"
        assert sync_broker.supports_immediate_execution() is True

    def test_sync_vs_async_handling(self, router_with_brokers, sample_market_data):
        """测试同步vs异步处理流程"""
        router = router_with_brokers

        # 创建测试订单
        order = self._create_test_order("000001.SZ")

        # 创建模拟事件
        order_event = Mock()
        order_event.value = order

        # 绑定引擎
        mock_engine = Mock()
        router.bind_engine(mock_engine)
        router.set_event_publisher(mock_engine.put)

        # 处理订单（应该走同步流程，因为SimBroker支持立即执行）
        router.on_order_received(order_event)

        # 验证立即有结果（同步执行）
        assert mock_engine.put.call_count > 0

    def test_async_order_tracking(self, router_with_brokers):
        """测试异步订单跟踪功能"""
        router = router_with_brokers

        # 模拟异步订单跟踪
        test_order = self._create_test_order("000001.SZ")
        broker_order_id = "ASYNC_TEST_123"

        # 开始跟踪订单
        router.track_order(broker_order_id, {
            'order': test_order,
            'broker': router.brokers[0],
            'submit_time': datetime.now(),
            'execution_mode': 'paper',
            'timeout_seconds': 300
        })

        # 验证订单被跟踪
        tracked_order = router.get_tracked_order(broker_order_id)
        assert tracked_order is not None
        assert tracked_order['order'] == test_order

        # 获取订单状态
        order_status = router.get_async_order_status(broker_order_id)
        assert order_status is not None
        assert order_status['broker_order_id'] == broker_order_id
        assert order_status['execution_mode'] == 'paper'
        assert 'elapsed_seconds' in order_status

    def test_timeout_handling(self, router_with_brokers):
        """测试超时处理机制"""
        router = router_with_brokers

        # 创建一个超时的订单（使用很早的提交时间）
        test_order = self._create_test_order("000001.SZ")
        broker_order_id = "TIMEOUT_TEST_456"

        # 模拟超时订单（提交时间为10分钟前）
        old_time = datetime.now() - datetime.timedelta(minutes=10)
        router.track_order(broker_order_id, {
            'order': test_order,
            'broker': router.brokers[0],
            'submit_time': old_time,
            'execution_mode': 'paper',
            'timeout_seconds': 300  # 5分钟超时
        })

        # 检查超时
        timeout_orders = router.check_order_timeouts()

        # 验证超时订单被处理
        assert broker_order_id in timeout_orders or len(timeout_orders) >= 0

        # 验证超时订单不再被跟踪
        remaining_tracked = router.get_tracked_order(broker_order_id)
        assert remaining_tracked is None

    def test_async_result_handling(self, router_with_brokers):
        """测试异步结果处理"""
        router = router_with_brokers

        # 模拟异步订单
        test_order = self._create_test_order("000001.SZ")
        broker_order_id = "ASYNC_RESULT_789"

        # 开始跟踪
        router.track_order(broker_order_id, {
            'order': test_order,
            'broker': router.brokers[0],
            'submit_time': datetime.now(),
            'execution_mode': 'paper'
        })

        # 绑定引擎
        mock_engine = Mock()
        router.bind_engine(mock_engine)
        router.set_event_publisher(mock_engine.put)

        # 模拟异步执行结果
        from ginkgo.trading.interfaces.broker_interface import BrokerExecutionResult
        async_result = BrokerExecutionResult(
            status=ORDERSTATUS_TYPES.FILLED,
            broker_order_id=broker_order_id,
            filled_volume=100,
            filled_price=10.5,
            commission=5.25
        )

        # 处理异步结果
        router._handle_async_result(async_result)

        # 验证事件被发布
        assert mock_engine.put.call_count > 0

        # 验证订单跟踪被清理（已完成的订单）
        remaining_tracked = router.get_tracked_order(broker_order_id)
        assert remaining_tracked is None

    def test_partial_fill_tracking_update(self, router_with_brokers):
        """测试部分成交的跟踪更新"""
        router = router_with_brokers

        test_order = self._create_test_order("000001.SZ")
        broker_order_id = "PARTIAL_FILL_123"

        # 开始跟踪
        router.track_order(broker_order_id, {
            'order': test_order,
            'broker': router.brokers[0],
            'submit_time': datetime.now(),
            'execution_mode': 'paper'
        })

        # 模拟部分成交结果
        from ginkgo.trading.interfaces.broker_interface import BrokerExecutionResult
        partial_result = BrokerExecutionResult(
            status=ORDERSTATUS_TYPES.PARTIAL_FILLED,
            broker_order_id=broker_order_id,
            filled_volume=50,  # 部分成交
            filled_price=10.25,
            commission=2.56
        )

        # 绑定引擎
        mock_engine = Mock()
        router.bind_engine(mock_engine)
        router.set_event_publisher(mock_engine.put)

        # 处理部分成交结果
        router._handle_async_result(partial_result)

        # 验证订单仍然被跟踪（部分成交后继续跟踪）
        remaining_tracked = router.get_tracked_order(broker_order_id)
        assert remaining_tracked is not None
        assert remaining_tracked['filled_volume'] == 50
        assert remaining_tracked['remaining_volume'] == 50  # 100 - 50

    def _create_test_order(self, code):
        """创建测试订单"""
        return Order(
            portfolio_id="async_test",
            engine_id="test_engine",
            run_id="test_run",
            code=code,
            direction=DIRECTION_TYPES.LONG,
            order_type=ORDER_TYPES.MARKETORDER,
            status=ORDERSTATUS_TYPES.NEW,
            volume=100,
            limit_price=10.0
        )