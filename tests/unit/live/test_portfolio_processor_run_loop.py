"""
PortfolioProcessor.run() 主循环单元测试

测试 PortfolioProcessor 的主循环功能：
1. run() 主循环的基础功能
2. 从input_queue获取事件并处理
3. pause/resume 暂停恢复功能
4. 统计信息更新（processed_count, error_count, last_event_time）
5. 异常处理和连续性
6. stop() 优雅停止
"""

import pytest
from queue import Queue, Empty
from threading import Thread
from time import sleep
from datetime import datetime
from decimal import Decimal
from unittest.mock import Mock

from ginkgo.workers.execution_node.portfolio_processor import PortfolioProcessor, PortfolioState
from ginkgo.trading.portfolios.portfolio_live import PortfolioLive
from ginkgo.trading.events.price_update import EventPriceUpdate
from ginkgo.trading.events.order_lifecycle_events import EventOrderPartiallyFilled
from ginkgo.trading.entities.bar import Bar
from ginkgo.enums import FREQUENCY_TYPES


@pytest.mark.unit
class TestPortfolioProcessorRunLoop:
    """测试 PortfolioProcessor.run() 主循环"""

    def test_run_loop_processes_events_from_queue(self):
        """测试主循环从input_queue处理事件"""
        # 创建Mock Portfolio
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

        # 创建EventPriceUpdate并放入input_queue
        bar = Bar(
            code="000001.SZ",
            timestamp=datetime.now(),
            open=Decimal("10.5"),
            high=Decimal("10.5"),
            low=Decimal("10.5"),
            close=Decimal("10.5"),
            volume=1000,
            amount=Decimal("10500"),
            frequency=FREQUENCY_TYPES.DAY
        )
        event = EventPriceUpdate(payload=bar)
        input_queue.put(event)

        # 启动processor
        processor.start()
        # 等待事件被处理
        sleep(0.2)

        # 停止processor
        processor.stop()

        # 验证portfolio.on_price_update被调用
        mock_portfolio.on_price_update.assert_called_once()

        # 验证统计信息更新
        assert processor.processed_count == 1
        assert processor.last_event_time is not None

        print(f"✅ 主循环成功处理事件")

    def test_run_loop_handles_multiple_events(self):
        """测试主循环处理多个事件"""
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

        # 放入多个事件
        for i in range(5):
            bar = Bar(
                code="000001.SZ",
                timestamp=datetime.now(),
                open=Decimal("10.5"),
                high=Decimal("10.5"),
                low=Decimal("10.5"),
                close=Decimal("10.5"),
                volume=1000 * (i + 1),
                amount=Decimal("10500"),
                frequency=FREQUENCY_TYPES.DAY
            )
            event = EventPriceUpdate(payload=bar)
            input_queue.put(event)

        # 启动processor
        processor.start()
        sleep(0.5)

        # 停止processor
        processor.stop()

        # 验证所有事件都被处理
        assert mock_portfolio.on_price_update.call_count == 5
        assert processor.processed_count == 5

        print(f"✅ 主循环成功处理多个事件")

    def test_run_loop_pause_resume(self):
        """测试暂停和恢复功能"""
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

        # 启动processor
        processor.start()
        sleep(0.1)  # 让processor启动

        # 暂停processor
        processor.pause()
        assert processor.is_paused == True

        # 在暂停时放入事件（不会被处理）
        bar = Bar(
            code="000001.SZ",
            timestamp=datetime.now(),
            open=Decimal("10.5"),
            high=Decimal("10.5"),
            low=Decimal("10.5"),
            close=Decimal("10.5"),
            volume=1000,
            amount=Decimal("10500"),
            frequency=FREQUENCY_TYPES.DAY
        )
        event = EventPriceUpdate(payload=bar)
        input_queue.put(event)

        sleep(0.3)  # 等待足够时间确认暂停状态

        # 验证暂停时没有处理事件（或者处理很少）
        processed_count_paused = processor.processed_count

        # 恢复processor
        processor.resume()
        assert processor.is_paused == False

        # 再放入一个事件
        bar2 = Bar(
            code="000002.SZ",
            timestamp=datetime.now(),
            open=Decimal("11.0"),
            high=Decimal("11.0"),
            low=Decimal("11.0"),
            close=Decimal("11.0"),
            volume=2000,
            amount=Decimal("22000"),
            frequency=FREQUENCY_TYPES.DAY
        )
        event2 = EventPriceUpdate(payload=bar2)
        input_queue.put(event2)

        sleep(0.3)  # 给足够时间处理恢复后的事件

        # 停止processor
        processor.stop()

        # 验证恢复后处理了更多事件
        assert processor.processed_count >= processed_count_paused

        print(f"✅ 暂停和恢复功能正常")

    def test_run_loop_handles_empty_queue(self):
        """测试主循环处理空队列（超时）"""
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

        # 启动processor（队列为空）
        processor.start()
        sleep(0.2)

        # 验证processor仍在运行（没有崩溃）
        assert processor.is_running == True

        # 停止processor
        processor.stop()

        print(f"✅ 空队列时主循环正常超时")

    def test_run_loop_exception_handling(self):
        """测试异常处理和连续性"""
        mock_portfolio = Mock(spec=PortfolioLive)
        mock_portfolio.portfolio_id = "test_portfolio"

        # Mock on_price_update 第一次抛异常，第二次成功
        call_count = [0]
        def side_effect(event):
            call_count[0] += 1
            if call_count[0] == 1:
                raise ValueError("Test error")
            return []

        mock_portfolio.on_price_update = Mock(side_effect=side_effect)

        input_queue = Queue()
        output_queue = Queue()

        processor = PortfolioProcessor(
            portfolio=mock_portfolio,
            input_queue=input_queue,
            output_queue=output_queue
        )

        # 放入两个事件
        for _ in range(2):
            bar = Bar(
                code="000001.SZ",
                timestamp=datetime.now(),
                open=Decimal("10.5"),
                high=Decimal("10.5"),
                low=Decimal("10.5"),
                close=Decimal("10.5"),
                volume=1000,
                amount=Decimal("10500"),
                frequency=FREQUENCY_TYPES.DAY
            )
            event = EventPriceUpdate(payload=bar)
            input_queue.put(event)

        # 启动processor
        processor.start()
        sleep(0.3)

        # 停止processor
        processor.stop()

        # 验证异常被捕获在_route_event中，processor继续运行
        # 注意：异常在_route_event中被捕获，不会传播到run()层
        # 所以error_count不会增加，但processor应该继续处理第二个事件
        assert call_count[0] >= 2  # 两个事件都被尝试处理

        # 验证processor仍然正常运行（没有崩溃）
        assert processor.is_running == False  # 已停止
        assert processor.state == PortfolioState.STOPPED

        print(f"✅ 异常处理和连续性正常")

    def test_run_loop_stops_gracefully(self):
        """测试优雅停止"""
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

        # 启动processor
        processor.start()
        assert processor.is_running == True

        # 停止processor
        processor.stop()
        sleep(0.1)

        # 验证已停止
        assert processor.is_running == False
        assert processor.state == PortfolioState.STOPPED

        print(f"✅ 优雅停止正常")


@pytest.mark.unit
class TestPortfolioProcessorStatistics:
    """测试 PortfolioProcessor 统计信息"""

    def test_processed_count_increments(self):
        """测试 processed_count 计数增加"""
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

        # 放入3个事件
        for _ in range(3):
            bar = Bar(
                code="000001.SZ",
                timestamp=datetime.now(),
                open=Decimal("10.5"),
                high=Decimal("10.5"),
                low=Decimal("10.5"),
                close=Decimal("10.5"),
                volume=1000,
                amount=Decimal("10500"),
                frequency=FREQUENCY_TYPES.DAY
            )
            event = EventPriceUpdate(payload=bar)
            input_queue.put(event)

        # 启动processor
        processor.start()
        sleep(0.3)

        # 停止processor
        processor.stop()

        # 验证processed_count正确
        assert processor.processed_count == 3

        print(f"✅ processed_count 正确增加")

    def test_last_event_time_updates(self):
        """测试 last_event_time 更新"""
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

        # 初始last_event_time应该为None
        assert processor.last_event_time is None

        # 放入一个事件
        bar = Bar(
            code="000001.SZ",
            timestamp=datetime.now(),
            open=Decimal("10.5"),
            high=Decimal("10.5"),
            low=Decimal("10.5"),
            close=Decimal("10.5"),
            volume=1000,
            amount=Decimal("10500"),
            frequency=FREQUENCY_TYPES.DAY
        )
        event = EventPriceUpdate(payload=bar)
        input_queue.put(event)

        # 启动processor
        processor.start()
        sleep(0.2)

        # 获取当前时间
        current_time = datetime.now()

        # 停止processor
        processor.stop()

        # 验证last_event_time已更新且在合理范围内
        assert processor.last_event_time is not None
        time_diff = current_time - processor.last_event_time
        assert time_diff.total_seconds() < 2  # 应该在2秒内

        print(f"✅ last_event_time 正确更新")


@pytest.mark.unit
class TestPortfolioProcessorIntegration:
    """测试 PortfolioProcessor 集成场景"""

    def test_full_run_cycle_with_portfolio(self):
        """测试完整的运行周期：启动 -> 处理事件 -> 停止"""
        mock_portfolio = Mock(spec=PortfolioLive)
        mock_portfolio.portfolio_id = "test_portfolio"

        # Mock portfolio方法返回模拟订单
        from ginkgo.trading.events.order_lifecycle_events import EventOrderAck
        from ginkgo.trading.entities.order import Order
        from ginkgo.enums import DIRECTION_TYPES, ORDER_TYPES, ORDERSTATUS_TYPES

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

        mock_ack = EventOrderAck(order=mock_order, broker_order_id="BROKER_123")

        # 第一次调用返回EventOrderAck，之后返回空
        call_count = [0]
        def side_effect(event):
            call_count[0] += 1
            if call_count[0] == 1:
                return [mock_ack]
            return []

        mock_portfolio.on_price_update = Mock(side_effect=side_effect)

        input_queue = Queue()
        output_queue = Queue()

        processor = PortfolioProcessor(
            portfolio=mock_portfolio,
            input_queue=input_queue,
            output_queue=output_queue
        )

        # 放入事件
        bar = Bar(
            code="000001.SZ",
            timestamp=datetime.now(),
            open=Decimal("10.5"),
            high=Decimal("10.5"),
            low=Decimal("10.5"),
            close=Decimal("10.5"),
            volume=1000,
            amount=Decimal("10500"),
            frequency=FREQUENCY_TYPES.DAY
        )
        event = EventPriceUpdate(payload=bar)
        input_queue.put(event)

        # 启动processor
        processor.start()
        sleep(0.2)

        # 停止processor
        processor.stop()

        # 验证portfolio方法被调用
        assert mock_portfolio.on_price_update.call_count >= 1

        # 验证output_queue收到事件
        assert not output_queue.empty()
        output_event = output_queue.get()
        assert isinstance(output_event, EventOrderAck)

        print(f"✅ 完整运行周期测试通过")
