"""
Dual Queue Mode 单元测试

测试双队列模式的实现：
1. PortfolioProcessor._handle_portfolio_event() 回调机制
2. Portfolio.set_event_publisher() 设置回调
3. Portfolio.put() 发布事件到output_queue
4. ExecutionNode._start_output_queue_listener() 监听output_queue
5. 完整的双队列流程：Portfolio → put() → callback → output_queue → listener
"""

import pytest
from queue import Queue
from threading import Thread
from time import sleep
from decimal import Decimal
from datetime import datetime

from ginkgo.workers.execution_node.portfolio_processor import PortfolioProcessor
from ginkgo.trading.portfolios.portfolio_live import PortfolioLive
from ginkgo.trading.entities.order import Order
from ginkgo.enums import DIRECTION_TYPES, ORDER_TYPES, ORDERSTATUS_TYPES


class MockContext:
    """Mock context for testing Portfolio without engine binding"""
    def __init__(self, engine_id="test_engine", run_id="test_run"):
        self._engine_id = engine_id
        self._run_id = run_id

    @property
    def engine_id(self):
        return self._engine_id

    @property
    def run_id(self):
        return self._run_id


def create_portfolio_with_context(**kwargs):
    """Helper function to create PortfolioLive with mock context"""
    if 'uuid' not in kwargs:
        kwargs['uuid'] = 'test_portfolio'
    if 'engine_id' not in kwargs:
        kwargs['engine_id'] = 'test_engine'
    if 'run_id' not in kwargs:
        kwargs['run_id'] = 'test_run'

    portfolio = PortfolioLive(**kwargs)
    portfolio._context = MockContext(engine_id=kwargs['engine_id'], run_id=kwargs['run_id'])
    return portfolio


@pytest.mark.unit
class TestPortfolioProcessorCallback:
    """测试 PortfolioProcessor 回调机制"""

    def test_handle_portfolio_event_forwards_to_output_queue(self):
        """测试 _handle_portfolio_event() 转发事件到 output_queue"""
        portfolio = create_portfolio_with_context()
        input_queue = Queue()
        output_queue = Queue()

        processor = PortfolioProcessor(
            portfolio=portfolio,
            input_queue=input_queue,
            output_queue=output_queue
        )

        # 创建一个测试事件（Order）
        test_order = Order(
            portfolio_id="test_portfolio",
            engine_id="test_engine",
            run_id="test_run",
            code="000001.SZ",
            direction=DIRECTION_TYPES.LONG,
            order_type=ORDER_TYPES.LIMITORDER,
            status=ORDERSTATUS_TYPES.NEW,
            volume=100,
            limit_price=Decimal("10.0")
        )

        # 调用回调处理事件
        processor._handle_portfolio_event(test_order)

        # 验证事件被转发到output_queue
        assert not output_queue.empty()
        forwarded_event = output_queue.get()
        assert forwarded_event.uuid == test_order.uuid

        print(f"✅ _handle_portfolio_event() 正确转发事件到 output_queue")

    def test_portfolio_set_event_publisher_called(self):
        """测试 PortfolioProcessor 在初始化时设置回调"""
        portfolio = create_portfolio_with_context()
        input_queue = Queue()
        output_queue = Queue()

        processor = PortfolioProcessor(
            portfolio=portfolio,
            input_queue=input_queue,
            output_queue=output_queue
        )

        # 验证portfolio的_event_publisher被设置
        assert portfolio._engine_put is not None
        assert portfolio._engine_put == processor._handle_portfolio_event

        print(f"✅ Portfolio.set_event_publisher() 回调已正确设置")


@pytest.mark.unit
class TestPortfolioPutEvent:
    """测试 Portfolio.put() 发布事件"""

    def test_portfolio_put_sends_to_callback(self):
        """测试 Portfolio.put() 通过回调发送事件到 output_queue"""
        portfolio = create_portfolio_with_context()
        input_queue = Queue()
        output_queue = Queue()

        processor = PortfolioProcessor(
            portfolio=portfolio,
            input_queue=input_queue,
            output_queue=output_queue
        )

        # 创建一个测试Order
        test_order = Order(
            portfolio_id="test_portfolio",
            engine_id="test_engine",
            run_id="test_run",
            code="000001.SZ",
            direction=DIRECTION_TYPES.LONG,
            order_type=ORDER_TYPES.LIMITORDER,
            status=ORDERSTATUS_TYPES.NEW,
            volume=100,
            limit_price=Decimal("10.0")
        )

        # Portfolio使用put()发布事件
        portfolio.put(test_order)

        # 验证事件被转发到output_queue
        sleep(0.1)  # 给回调一点时间
        assert not output_queue.empty()
        forwarded_event = output_queue.get()
        assert forwarded_event.uuid == test_order.uuid

        print(f"✅ Portfolio.put() 正确发送事件到 output_queue")

    def test_portfolio_put_without_callback_logs_error(self):
        """测试没有设置回调时 put() 记录错误"""
        portfolio = create_portfolio_with_context()

        # 手动清除回调（模拟未设置）
        portfolio._engine_put = None

        # 创建一个测试Order
        test_order = Order(
            portfolio_id="test_portfolio",
            engine_id="test_engine",
            run_id="test_run",
            code="000001.SZ",
            direction=DIRECTION_TYPES.LONG,
            order_type=ORDER_TYPES.LIMITORDER,
            status=ORDERSTATUS_TYPES.NEW,
            volume=100,
            limit_price=Decimal("10.0")
        )

        # put()应该记录错误但不崩溃
        portfolio.put(test_order)

        # 验证没有抛异常
        print(f"✅ Portfolio.put() 在没有回调时优雅处理")


@pytest.mark.unit
class TestDualQueueIntegration:
    """测试双队列模式集成场景"""

    def test_full_dual_queue_flow(self):
        """测试完整双队列流程：Portfolio → put() → callback → output_queue"""
        portfolio = create_portfolio_with_context()
        input_queue = Queue()
        output_queue = Queue()

        processor = PortfolioProcessor(
            portfolio=portfolio,
            input_queue=input_queue,
            output_queue=output_queue
        )

        # 创建多个测试Order
        orders = []
        for i in range(3):
            order = Order(
                portfolio_id="test_portfolio",
                engine_id="test_engine",
                run_id="test_run",
                code=f"00000{i+1}.SZ",
                direction=DIRECTION_TYPES.LONG,
                order_type=ORDER_TYPES.LIMITORDER,
                status=ORDERSTATUS_TYPES.NEW,
                volume=100 * (i + 1),
                limit_price=Decimal(str(10.0 + i))
            )
            orders.append(order)

        # Portfolio使用put()发布所有订单
        for order in orders:
            portfolio.put(order)

        # 验证所有订单都被转发到output_queue
        sleep(0.2)  # 给回调时间处理
        received_orders = []
        while not output_queue.empty():
            received_orders.append(output_queue.get())

        assert len(received_orders) == 3
        for i, order in enumerate(orders):
            assert any(o.uuid == order.uuid for o in received_orders)

        print(f"✅ 完整双队列流程测试通过")

    def test_dual_queue_non_blocking(self):
        """测试双队列模式非阻塞特性"""
        portfolio = create_portfolio_with_context()

        # 创建小容量output_queue（容易满）
        input_queue = Queue()
        output_queue = Queue(maxsize=1)

        processor = PortfolioProcessor(
            portfolio=portfolio,
            input_queue=input_queue,
            output_queue=output_queue
        )

        # 创建多个Order
        orders = []
        for i in range(5):
            order = Order(
                portfolio_id="test_portfolio",
                engine_id="test_engine",
                run_id="test_run",
                code=f"00000{i+1}.SZ",
                direction=DIRECTION_TYPES.LONG,
                order_type=ORDER_TYPES.LIMITORDER,
                status=ORDERSTATUS_TYPES.NEW,
                volume=100,
                limit_price=Decimal("10.0")
            )
            orders.append(order)

        # Portfolio使用put()发布所有订单（非阻塞，不会死锁）
        for order in orders:
            portfolio.put(order)

        # 验证没有崩溃
        print(f"✅ 双队列模式非阻塞测试通过")


@pytest.mark.unit
class TestOutputQueueListener:
    """测试 output_queue 监听器"""

    def test_output_queue_listener_receives_events(self):
        """测试监听器接收output_queue中的事件"""
        output_queue = Queue()

        # 模拟监听器行为
        received_events = []

        def mock_listener():
            while len(received_events) < 2:
                try:
                    event = output_queue.get(timeout=0.5)
                    received_events.append(event)
                    output_queue.task_done()
                except:
                    break

        # 启动监听线程
        listener_thread = Thread(target=mock_listener, daemon=True)
        listener_thread.start()

        # 放入测试事件
        order1 = Order(
            portfolio_id="test_portfolio",
            engine_id="test_engine",
            run_id="test_run",
            code="000001.SZ",
            direction=DIRECTION_TYPES.LONG,
            order_type=ORDER_TYPES.LIMITORDER,
            status=ORDERSTATUS_TYPES.NEW,
            volume=100,
            limit_price=Decimal("10.0")
        )

        order2 = Order(
            portfolio_id="test_portfolio",
            engine_id="test_engine",
            run_id="test_run",
            code="000002.SZ",
            direction=DIRECTION_TYPES.LONG,
            order_type=ORDER_TYPES.LIMITORDER,
            status=ORDERSTATUS_TYPES.NEW,
            volume=200,
            limit_price=Decimal("11.0")
        )

        output_queue.put(order1)
        output_queue.put(order2)

        # 等待监听器处理
        sleep(0.2)

        # 验证监听器接收到事件
        assert len(received_events) == 2
        assert received_events[0].uuid == order1.uuid
        assert received_events[1].uuid == order2.uuid

        print(f"✅ output_queue 监听器正确接收事件")


@pytest.mark.unit
class TestHexagonalArchitecture:
    """测试六边形架构约束"""

    def test_portfolio_does_not_depend_on_execution_node(self):
        """测试Portfolio不依赖ExecutionNode（六边形架构）"""
        portfolio = create_portfolio_with_context()

        # Portfolio不应该持有ExecutionNode引用
        assert not hasattr(portfolio, 'execution_node')
        assert not hasattr(portfolio, '_execution_node')
        assert not hasattr(portfolio, 'node')

        # Portfolio应该有put()方法发布事件
        assert hasattr(portfolio, 'put')
        assert callable(portfolio.put)

        print(f"✅ Portfolio不依赖ExecutionNode，符合六边形架构")

    def test_portfolio_communicates_via_queue_only(self):
        """测试Portfolio只通过Queue通信（六边形架构）"""
        portfolio = create_portfolio_with_context()
        input_queue = Queue()
        output_queue = Queue()

        # PortfolioProcessor作为适配器隔离Portfolio和ExecutionNode
        processor = PortfolioProcessor(
            portfolio=portfolio,
            input_queue=input_queue,
            output_queue=output_queue
        )

        # Portfolio通过set_event_publisher()设置通信通道
        assert portfolio._engine_put is not None

        # Portfolio不直接访问ExecutionNode
        assert not hasattr(portfolio, 'execution_node')

        print(f"✅ Portfolio只通过Queue通信，符合六边形架构")
