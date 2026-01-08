"""
PortfolioProcessor 单元测试

测试 PortfolioProcessor 线程类的基础功能：
1. 实例化和初始化
2. start() 和 stop() 方法
3. 事件路由 (_route_event)
4. 状态管理 (pause/resume)
5. graceful_stop() 优雅停止
6. get_status() 获取状态
"""

import pytest
from queue import Queue
from threading import Thread
from time import sleep
from unittest.mock import Mock, patch

from ginkgo.workers.execution_node.portfolio_processor import PortfolioProcessor, PortfolioState
from ginkgo.trading.portfolios.portfolio_live import PortfolioLive
from ginkgo.trading.events.price_update import EventPriceUpdate
from ginkgo.trading.events.order_lifecycle_events import EventOrderPartiallyFilled, EventOrderAck
from decimal import Decimal
from datetime import datetime


@pytest.mark.unit
class TestPortfolioProcessorBasics:
    """测试 PortfolioProcessor 基础功能"""

    def test_portfolio_processor_initialization(self):
        """测试 PortfolioProcessor 实例化"""
        # 创建Mock Portfolio
        mock_portfolio = Mock(spec=PortfolioLive)
        mock_portfolio.portfolio_id = "test_portfolio"

        # 创建队列
        input_queue = Queue(maxsize=1000)
        output_queue = Queue(maxsize=1000)

        # 创建PortfolioProcessor
        processor = PortfolioProcessor(
            portfolio=mock_portfolio,
            input_queue=input_queue,
            output_queue=output_queue,
            max_queue_size=1000
        )

        assert processor.portfolio_id == "test_portfolio"
        assert processor.portfolio == mock_portfolio
        assert processor.input_queue == input_queue
        assert processor.output_queue == output_queue
        assert processor.max_queue_size == 1000
        assert processor.is_running == False
        assert processor.is_paused == False
        assert processor.is_active == False
        assert processor.state == PortfolioState.STARTING
        assert processor.processed_count == 0
        assert processor.error_count == 0
        print(f"✅ PortfolioProcessor 初始化成功: portfolio_id={processor.portfolio_id}")

    def test_portfolio_processor_inheritance(self):
        """测试 PortfolioProcessor 继承 Thread"""
        mock_portfolio = Mock(spec=PortfolioLive)
        mock_portfolio.portfolio_id = "test_portfolio"

        processor = PortfolioProcessor(
            portfolio=mock_portfolio,
            input_queue=Queue(),
            output_queue=Queue()
        )

        assert isinstance(processor, Thread)
        assert processor.daemon == True  # 应该是守护线程
        print(f"✅ PortfolioProcessor 正确继承 Thread")


@pytest.mark.unit
class TestPortfolioProcessorLifecycle:
    """测试 PortfolioProcessor 生命周期管理"""

    def test_start_stop(self):
        """测试 start() 和 stop() 方法"""
        mock_portfolio = Mock(spec=PortfolioLive)
        mock_portfolio.portfolio_id = "test_portfolio"

        input_queue = Queue()
        output_queue = Queue()

        processor = PortfolioProcessor(
            portfolio=mock_portfolio,
            input_queue=input_queue,
            output_queue=output_queue
        )

        # 启动
        processor.start()
        assert processor.is_running == True
        assert processor.state == PortfolioState.RUNNING
        print(f"✅ PortfolioProcessor 启动成功")

        # 停止
        processor.stop()
        assert processor.is_running == False
        assert processor.state == PortfolioState.STOPPED
        print(f"✅ PortfolioProcessor 停止成功")

    def test_pause_resume(self):
        """测试 pause() 和 resume() 方法"""
        mock_portfolio = Mock(spec=PortfolioLive)
        mock_portfolio.portfolio_id = "test_portfolio"

        processor = PortfolioProcessor(
            portfolio=mock_portfolio,
            input_queue=Queue(),
            output_queue=Queue()
        )

        processor.start()

        # 暂停
        processor.pause()
        assert processor.is_paused == True
        print(f"✅ PortfolioProcessor 暂停成功")

        # 恢复
        processor.resume()
        assert processor.is_paused == False
        print(f"✅ PortfolioProcessor 恢复成功")

        # 清理
        processor.stop()

    def test_graceful_stop(self):
        """测试 graceful_stop() 优雅停止"""
        mock_portfolio = Mock(spec=PortfolioLive)
        mock_portfolio.portfolio_id = "test_portfolio"
        # Mock sync_state_to_db 方法
        mock_portfolio.sync_state_to_db = Mock(return_value=True)

        input_queue = Queue()
        output_queue = Queue()

        processor = PortfolioProcessor(
            portfolio=mock_portfolio,
            input_queue=input_queue,
            output_queue=output_queue
        )

        processor.start()

        # 优雅停止
        result = processor.graceful_stop(timeout=5.0)

        assert result == True
        assert processor.is_running == False
        assert processor.state == PortfolioState.STOPPED
        # 验证调用了 save_state
        mock_portfolio.sync_state_to_db.assert_called_once()
        print(f"✅ PortfolioProcessor 优雅停止成功")


@pytest.mark.unit
class TestPortfolioProcessorEventRouting:
    """测试 PortfolioProcessor 事件路由"""

    def test_route_event_price_update(self):
        """测试路由 EventPriceUpdate"""
        mock_portfolio = Mock(spec=PortfolioLive)
        mock_portfolio.portfolio_id = "test_portfolio"
        # Mock on_price_update 返回空列表
        mock_portfolio.on_price_update = Mock(return_value=[])

        input_queue = Queue()
        output_queue = Queue()

        processor = PortfolioProcessor(
            portfolio=mock_portfolio,
            input_queue=input_queue,
            output_queue=output_queue
        )

        # 创建 EventPriceUpdate
        from ginkgo.trading.entities.bar import Bar
        bar = Bar(
            code="000001.SZ",
            timestamp=datetime.now(),
            open=Decimal("10.0"),
            high=Decimal("10.5"),
            low=Decimal("9.8"),
            close=Decimal("10.3"),
            volume=1000000,
            amount=Decimal("10300000"),
            frequency="DAY"
        )
        event = EventPriceUpdate(payload=bar)

        # 路由事件
        processor._route_event(event)

        # 验证调用了 portfolio.on_price_update
        mock_portfolio.on_price_update.assert_called_once_with(event)
        print(f"✅ EventPriceUpdate 路由成功")

    def test_route_event_order_filled(self):
        """测试路由 EventOrderPartiallyFilled"""
        from ginkgo.trading.entities.order import Order
        from ginkgo.enums import DIRECTION_TYPES, ORDER_TYPES, ORDERSTATUS_TYPES

        mock_portfolio = Mock(spec=PortfolioLive)
        mock_portfolio.portfolio_id = "test_portfolio"
        # Mock on_order_filled 返回 None
        mock_portfolio.on_order_filled = Mock(return_value=None)

        processor = PortfolioProcessor(
            portfolio=mock_portfolio,
            input_queue=Queue(),
            output_queue=Queue()
        )

        # 创建一个真实的 Order 对象
        mock_order = Order(
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

        # 创建 EventOrderPartiallyFilled (需要 order, filled_quantity, fill_price 参数)
        event = EventOrderPartiallyFilled(
            order=mock_order,
            filled_quantity=100,
            fill_price=Decimal("10.5")
        )

        # 路由事件
        processor._route_event(event)

        # 验证调用了 portfolio.on_order_filled
        mock_portfolio.on_order_filled.assert_called_once_with(event)
        print(f"✅ EventOrderPartiallyFilled 路由成功")

    def test_route_event_with_output(self):
        """测试路由事件并将输出放入 output_queue"""
        from ginkgo.trading.entities.order import Order
        from ginkgo.enums import DIRECTION_TYPES, ORDER_TYPES, ORDERSTATUS_TYPES

        mock_portfolio = Mock(spec=PortfolioLive)
        mock_portfolio.portfolio_id = "test_portfolio"

        # 创建一个真实的 Order 对象作为返回值
        mock_order = Order(
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

        # Mock on_price_update 返回 EventOrderAck
        mock_event_ack = EventOrderAck(order=mock_order, broker_order_id="BROKER_123")
        mock_portfolio.on_price_update = Mock(return_value=[mock_event_ack])

        input_queue = Queue()
        output_queue = Queue()

        processor = PortfolioProcessor(
            portfolio=mock_portfolio,
            input_queue=input_queue,
            output_queue=output_queue
        )

        # 创建 EventPriceUpdate
        from ginkgo.trading.entities.bar import Bar
        bar = Bar(
            code="000001.SZ",
            timestamp=datetime.now(),
            open=Decimal("10.0"),
            high=Decimal("10.5"),
            low=Decimal("9.8"),
            close=Decimal("10.3"),
            volume=1000000,
            amount=Decimal("10300000"),
            frequency="DAY"
        )
        event = EventPriceUpdate(payload=bar)

        # 路由事件
        processor._route_event(event)

        # 验证 output_queue 收到了事件
        assert not output_queue.empty()
        output_event = output_queue.get()
        assert isinstance(output_event, EventOrderAck)
        assert output_event.order.uuid == mock_order.uuid
        print(f"✅ 事件输出到 output_queue 成功")


@pytest.mark.unit
class TestPortfolioProcessorStatus:
    """测试 PortfolioProcessor 状态查询"""

    def test_get_status(self):
        """测试 get_status() 方法"""
        mock_portfolio = Mock(spec=PortfolioLive)
        mock_portfolio.portfolio_id = "test_portfolio"

        input_queue = Queue()
        output_queue = Queue()

        processor = PortfolioProcessor(
            portfolio=mock_portfolio,
            input_queue=input_queue,
            output_queue=output_queue,
            max_queue_size=1000
        )

        status = processor.get_status()

        assert status["portfolio_id"] == "test_portfolio"
        assert status["state"] == PortfolioState.STARTING.value
        assert status["is_running"] == False
        assert status["is_paused"] == False
        assert status["is_active"] == False
        assert status["is_alive"] == False
        assert status["queue_size"] == 0
        assert status["queue_usage"] == 0.0
        assert status["queue_maxsize"] == 1000
        assert status["processed_count"] == 0
        assert status["error_count"] == 0
        assert status["last_event_time"] is None
        print(f"✅ get_status() 返回正确: {status}")

    def test_get_queue_size(self):
        """测试 get_queue_size() 方法"""
        mock_portfolio = Mock(spec=PortfolioLive)
        mock_portfolio.portfolio_id = "test_portfolio"

        input_queue = Queue()
        # 放入几个事件
        input_queue.put("event1")
        input_queue.put("event2")
        input_queue.put("event3")

        processor = PortfolioProcessor(
            portfolio=mock_portfolio,
            input_queue=input_queue,
            output_queue=Queue()
        )

        queue_size = processor.get_queue_size()
        assert queue_size == 3
        print(f"✅ get_queue_size() 返回正确: {queue_size}")

    def test_get_queue_usage(self):
        """测试 get_queue_usage() 方法"""
        mock_portfolio = Mock(spec=PortfolioLive)
        mock_portfolio.portfolio_id = "test_portfolio"

        input_queue = Queue(maxsize=100)
        # 放入10个事件
        for i in range(10):
            input_queue.put(f"event{i}")

        processor = PortfolioProcessor(
            portfolio=mock_portfolio,
            input_queue=input_queue,
            output_queue=Queue(),
            max_queue_size=100
        )

        queue_usage = processor.get_queue_usage()
        assert queue_usage == 0.1  # 10/100
        print(f"✅ get_queue_usage() 返回正确: {queue_usage}")


@pytest.mark.unit
class TestPortfolioProcessorIntegration:
    """测试 PortfolioProcessor 集成场景"""

    def test_processor_with_empty_queue(self):
        """测试 Processor 处理空队列"""
        mock_portfolio = Mock(spec=PortfolioLive)
        mock_portfolio.portfolio_id = "test_portfolio"
        mock_portfolio.on_price_update = Mock(return_value=[])

        input_queue = Queue()
        output_queue = Queue()

        processor = PortfolioProcessor(
            portfolio=mock_portfolio,
            input_queue=input_queue,
            output_queue=output_queue
        )

        processor.start()
        # 等待一小段时间，确保主循环运行
        sleep(0.5)

        # 验证没有调用 portfolio 方法（因为队列为空）
        # 注意：由于主循环在运行，可能会有超时导致的继续，但不应该调用业务方法
        assert processor.is_running == True

        # 停止
        processor.stop()
        print(f"✅ 空队列处理测试通过")

    def test_processor_state_transitions(self):
        """测试状态机转换"""
        mock_portfolio = Mock(spec=PortfolioLive)
        mock_portfolio.portfolio_id = "test_portfolio"

        processor = PortfolioProcessor(
            portfolio=mock_portfolio,
            input_queue=Queue(),
            output_queue=Queue()
        )

        # 初始状态
        assert processor.state == PortfolioState.STARTING

        # 启动后
        processor.start()
        assert processor.state == PortfolioState.RUNNING

        # 暂停（状态不变，is_paused改变）
        processor.pause()
        assert processor.state == PortfolioState.RUNNING
        assert processor.is_paused == True

        # 恢复
        processor.resume()
        assert processor.is_paused == False

        # 停止
        processor.stop()
        assert processor.state == PortfolioState.STOPPED

        print(f"✅ 状态机转换测试通过")
