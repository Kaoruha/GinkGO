"""
实盘交易事件链路集成测试

测试完整的事件驱动链路：
PriceUpdate → PortfolioLive → Signal → Order → PortfolioProcessor → output_queue

这个测试验证：
1. PortfolioLive.on_price_update() 处理价格更新
2. Strategy 生成 Signal
3. Sizer 计算 Order
4. PortfolioProcessor 收集返回值并放入 output_queue
5. ExecutionNode 监听 output_queue 并发送到 Kafka
"""

import pytest
from decimal import Decimal
from datetime import datetime
from queue import Queue
from unittest.mock import Mock, patch

from ginkgo.trading.portfolios.portfolio_live import PortfolioLive
from ginkgo.trading.events.price_update import EventPriceUpdate
from ginkgo.trading.events.order_lifecycle_events import EventOrderAck
from ginkgo.trading.entities.signal import Signal
from ginkgo.enums import DIRECTION_TYPES, SOURCE_TYPES, FREQUENCY_TYPES, ORDER_TYPES, ORDERSTATUS_TYPES
from ginkgo.trading.strategies.base_strategy import BaseStrategy
from ginkgo.trading.bases.sizer_base import SizerBase
from ginkgo.trading.bases.risk_base import RiskBase
from ginkgo.trading.bases.selector_base import SelectorBase
from ginkgo.workers.execution_node.portfolio_processor import PortfolioProcessor


@pytest.mark.integration
class TestLiveTradingEventChain:
    """测试实盘交易完整事件链路"""

    def test_price_update_to_order_complete_chain(self):
        """测试完整的 PriceUpdate → Signal → Order 链路"""

        # 1. 创建 PortfolioLive
        portfolio = PortfolioLive(
            portfolio_id="test_portfolio",
            engine_id="test_engine",
            run_id="test_run",
            name="Test Portfolio",
            initial_cash=Decimal("100000")
        )

        # 2. 添加一个简单的策略（价格 > 10 时买入）
        class SimpleStrategy(BaseStrategy):
            def cal(self, portfolio_info, event):
                # 从 event.payload (Bar) 获取价格信息
                if event.payload and event.payload.close > Decimal("10.0"):
                    # 直接使用 portfolio 的属性，而不是从 portfolio_info 获取
                    return [Signal(
                        portfolio_id=self.portfolio_id or portfolio.portfolio_id,
                        engine_id=self.engine_id or "test_engine",
                        run_id=self.run_id or "test_run",
                        code=event.payload.code,
                        direction=DIRECTION_TYPES.LONG
                    )]
                return []

        portfolio.add_strategy(SimpleStrategy())

        # 3. 添加 Selector（选择所有股票）
        class AllStockSelector(SelectorBase):
            def pick(self, time=None, *args, **kwargs):
                # 返回所有股票代码（测试时允许任何代码）
                return ["*"]  # 通配符表示所有股票

        portfolio.bind_selector(AllStockSelector())

        # 4. 添加 Sizer（固定买入100股）
        class FixedSizer(SizerBase):
            def cal(self, portfolio_info, signal):
                from ginkgo.trading.entities.order import Order
                return Order(
                    portfolio_id=signal.portfolio_id,
                    engine_id=signal.engine_id,
                    run_id=signal.run_id,
                    code=signal.code,
                    direction=signal.direction,
                    order_type=ORDER_TYPES.LIMITORDER,  # 限价单
                    status=ORDERSTATUS_TYPES.NEW,  # 新订单
                    volume=100,
                    limit_price=Decimal("10.0")  # 限价
                )

        portfolio.bind_sizer(FixedSizer())

        # 4. 添加空的 risk_manager（放行所有订单）
        portfolio.add_risk_manager(RiskBase())

        # 5. 创建 PortfolioProcessor
        input_queue = Queue(maxsize=100)
        output_queue = Queue(maxsize=100)

        processor = PortfolioProcessor(
            portfolio=portfolio,
            input_queue=input_queue,
            output_queue=output_queue,
            max_queue_size=100
        )

        # 6. 发送价格更新事件（价格 > 10，应该生成信号）
        from ginkgo.trading.entities.bar import Bar
        bar = Bar(
            code="000001.SZ",
            timestamp=datetime.now(),
            open=Decimal("10.5"),
            high=Decimal("10.5"),
            low=Decimal("10.5"),
            close=Decimal("10.5"),  # 价格 > 10，应该触发买入
            volume=1000,
            amount=Decimal("10500"),  # 成交金额 = price * volume
            frequency=FREQUENCY_TYPES.DAY
        )
        event = EventPriceUpdate(payload=bar)

        # 7. Portfolio 处理事件
        result = portfolio.on_price_update(event)

        # 8. 验证返回了订单事件
        assert isinstance(result, list)
        assert len(result) == 1
        assert isinstance(result[0], EventOrderAck)

        # 验证订单内容
        order_event = result[0]
        assert order_event.order.code == "000001.SZ"
        assert order_event.order.direction == DIRECTION_TYPES.LONG
        assert order_event.order.volume == 100

        print(f"✅ PriceUpdate → Signal → Order 链路测试通过！")
        print(f"   生成订单: {order_event.order.code} {order_event.order.direction} {order_event.order.volume}股")

    def test_portfolio_processor_routes_event(self):
        """测试 PortfolioProcessor 事件路由和输出队列"""

        # 1. 创建 PortfolioLive
        portfolio = PortfolioLive(
            portfolio_id="test_portfolio",
            engine_id="test_engine",
            run_id="test_run",
            name="Test Portfolio",
            initial_cash=Decimal("100000")
        )

        # 2. 添加策略和Sizer
        class SimpleStrategy(BaseStrategy):
            def cal(self, portfolio_info, event):
                if event.payload and event.payload.close > Decimal("10.0"):
                    return [Signal(
                        portfolio_id=self.portfolio_id or portfolio.portfolio_id,
                        engine_id=self.engine_id or "test_engine",
                        run_id=self.run_id or "test_run",
                        code=event.payload.code,
                        direction=DIRECTION_TYPES.LONG
                    )]
                return []

        portfolio.add_strategy(SimpleStrategy())

        # 添加 Selector（选择所有股票）
        class AllStockSelector(SelectorBase):
            def pick(self, time=None, *args, **kwargs):
                return ["*"]

        portfolio.bind_selector(AllStockSelector())

        class FixedSizer(SizerBase):
            def cal(self, portfolio_info, signal):
                from ginkgo.trading.entities.order import Order
                return Order(
                    portfolio_id=signal.portfolio_id,
                    engine_id=signal.engine_id,
                    run_id=signal.run_id,
                    code=signal.code,
                    direction=signal.direction,
                    order_type=ORDER_TYPES.LIMITORDER,
                    status=ORDERSTATUS_TYPES.NEW,
                    volume=100,
                    limit_price=Decimal("10.0")
                )

        portfolio.bind_sizer(FixedSizer())
        portfolio.add_risk_manager(RiskBase())

        # 3. 创建队列和PortfolioProcessor
        input_queue = Queue(maxsize=100)
        output_queue = Queue(maxsize=100)

        processor = PortfolioProcessor(
            portfolio=portfolio,
            input_queue=input_queue,
            output_queue=output_queue,
            max_queue_size=100
        )

        # 4. 创建价格更新事件
        from ginkgo.trading.entities.bar import Bar
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

        # 5. 模拟 PortfolioProcessor 路由事件
        # （实际中这是在 processor.run() 主循环中自动进行）
        result = processor._route_event(event)

        # 6. 验证 output_queue 收到了订单事件
        assert not output_queue.empty(), "output_queue 应该包含订单事件"

        order_event = output_queue.get()
        assert isinstance(order_event, EventOrderAck)
        assert order_event.order.code == "000001.SZ"
        assert order_event.order.direction == DIRECTION_TYPES.LONG

        print(f"✅ PortfolioProcessor 事件路由测试通过！")
        print(f"   EventPriceUpdate → Portfolio → output_queue → EventOrderAck")

    def test_no_signal_when_price_low(self):
        """测试价格不满足条件时不生成信号"""

        # 1. 创建 PortfolioLive
        portfolio = PortfolioLive(
            portfolio_id="test_portfolio",
            engine_id="test_engine",
            run_id="test_run",
            name="Test Portfolio",
            initial_cash=Decimal("100000")
        )

        # 2. 添加策略（价格 > 10 时才买入）
        class SimpleStrategy(BaseStrategy):
            def cal(self, portfolio_info, event):
                if event.payload and event.payload.close > Decimal("10.0"):
                    return [Signal(
                        portfolio_id=self.portfolio_id or portfolio.portfolio_id,
                        engine_id=self.engine_id or "test_engine",
                        run_id=self.run_id or "test_run",
                        code=event.payload.code,
                        direction=DIRECTION_TYPES.LONG
                    )]
                return []

        portfolio.add_strategy(SimpleStrategy())

        # 添加 Selector（选择所有股票）
        class AllStockSelector(SelectorBase):
            def pick(self, time=None, *args, **kwargs):
                return ["*"]

        portfolio.bind_selector(AllStockSelector())
        portfolio.bind_sizer(SizerBase())
        portfolio.add_risk_manager(RiskBase())

        # 3. 发送价格更新事件（价格 = 9.5，不满足条件）
        from ginkgo.trading.entities.bar import Bar
        bar = Bar(
            code="000001.SZ",
            timestamp=datetime.now(),
            open=Decimal("9.5"),
            high=Decimal("9.5"),
            low=Decimal("9.5"),
            close=Decimal("9.5"),  # 价格 < 10，不应该触发买入
            volume=1000,
            amount=Decimal("9500"),
            frequency=FREQUENCY_TYPES.DAY
        )
        event = EventPriceUpdate(payload=bar)

        # 4. Portfolio 处理事件
        result = portfolio.on_price_update(event)

        # 5. 验证没有生成订单
        assert isinstance(result, list)
        assert len(result) == 0

        print(f"✅ 价格不满足条件时不生成信号 - 测试通过！")
        print(f"   价格 9.5 < 阈值 10.0，无信号生成")

    def test_risk_manager_blocks_order(self):
        """测试风控管理器拦截订单"""

        # 1. 创建 PortfolioLive
        portfolio = PortfolioLive(
            portfolio_id="test_portfolio",
            engine_id="test_engine",
            run_id="test_run",
            name="Test Portfolio",
            initial_cash=Decimal("100000")
        )

        # 2. 添加策略（总是买入）
        class AlwaysBuyStrategy(BaseStrategy):
            def cal(self, portfolio_info, event):
                if event.payload:
                    return [Signal(
                        portfolio_id=self.portfolio_id or portfolio.portfolio_id,
                        engine_id=self.engine_id or "test_engine",
                        run_id=self.run_id or "test_run",
                        code=event.payload.code,
                        direction=DIRECTION_TYPES.LONG
                    )]
                return []

        portfolio.add_strategy(AlwaysBuyStrategy())

        # 添加 Selector（选择所有股票）
        class AllStockSelector(SelectorBase):
            def pick(self, time=None, *args, **kwargs):
                return ["*"]

        portfolio.bind_selector(AllStockSelector())

        # 3. 添加 Sizer
        class FixedSizer(SizerBase):
            def cal(self, portfolio_info, signal):
                from ginkgo.trading.entities.order import Order
                return Order(
                    portfolio_id=signal.portfolio_id,
                    engine_id=signal.engine_id,
                    run_id=signal.run_id,
                    code=signal.code,
                    direction=signal.direction,
                    order_type=ORDER_TYPES.LIMITORDER,
                    status=ORDERSTATUS_TYPES.NEW,
                    volume=100,
                    limit_price=Decimal("10.0")
                )

        portfolio.bind_sizer(FixedSizer())

        # 4. 添加会拦截的 risk_manager（资金不足）
        class BlockingRisk(RiskBase):
            def cal(self, portfolio_info, order):
                # 模拟资金不足，拦截订单
                return None  # 返回 None 表示拦截

        portfolio.add_risk_manager(BlockingRisk())

        # 5. 发送价格更新事件
        from ginkgo.trading.entities.bar import Bar
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

        # 6. Portfolio 处理事件
        result = portfolio.on_price_update(event)

        # 7. 验证订单被风控拦截
        assert isinstance(result, list)
        assert len(result) == 0  # 风控拦截，没有订单生成

        print(f"✅ 风控管理器拦截订单 - 测试通过！")
        print(f"   Signal 生成 → Sizer 计算 → RiskManager 拦截 → 无订单输出")


@pytest.mark.integration
class TestEventChainEndToEnd:
    """端到端测试：ExecutionNode → Portfolio → Kafka"""

    def test_execution_node_to_portfolio_to_kafka_chain(self):
        """测试完整的 ExecutionNode → Portfolio → Kafka 链路（模拟）"""

        # 1. 创建 Portfolio
        portfolio = PortfolioLive(
            portfolio_id="test_portfolio",
            engine_id="test_engine",
            run_id="test_run",
            name="Test Portfolio",
            initial_cash=Decimal("100000")
        )

        # 2. 添加策略和Sizer
        class SimpleStrategy(BaseStrategy):
            def cal(self, portfolio_info, event):
                if event.payload and event.payload.close > Decimal("10.0"):
                    return [Signal(
                        portfolio_id=self.portfolio_id or portfolio.portfolio_id,
                        engine_id=self.engine_id or "test_engine",
                        run_id=self.run_id or "test_run",
                        code=event.payload.code,
                        direction=DIRECTION_TYPES.LONG
                    )]
                return []

        portfolio.add_strategy(SimpleStrategy())

        # 添加 Selector（选择所有股票）
        class AllStockSelector(SelectorBase):
            def pick(self, time=None, *args, **kwargs):
                return ["*"]

        portfolio.bind_selector(AllStockSelector())

        class FixedSizer(SizerBase):
            def cal(self, portfolio_info, signal):
                from ginkgo.trading.entities.order import Order
                return Order(
                    portfolio_id=signal.portfolio_id,
                    engine_id=signal.engine_id,
                    run_id=signal.run_id,
                    code=signal.code,
                    direction=signal.direction,
                    order_type=ORDER_TYPES.LIMITORDER,
                    status=ORDERSTATUS_TYPES.NEW,
                    volume=100,
                    limit_price=Decimal("10.0")
                )

        portfolio.bind_sizer(FixedSizer())
        portfolio.add_risk_manager(RiskBase())

        # 3. 创建队列（模拟 ExecutionNode 的 input/output queue）
        input_queue = Queue(maxsize=100)
        output_queue = Queue(maxsize=100)

        # 4. 创建 PortfolioProcessor
        processor = PortfolioProcessor(
            portfolio=portfolio,
            input_queue=input_queue,
            output_queue=output_queue,
            max_queue_size=100
        )

        # 5. 模拟 Kafka 消息到达 ExecutionNode
        # ExecutionNode 解析为 EventPriceUpdate 并放入 input_queue
        from ginkgo.trading.entities.bar import Bar
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

        # 6. PortfolioProcessor 路由事件到 Portfolio
        result = processor._route_event(event)

        # 7. 验证 output_queue 收到订单
        assert not output_queue.empty()
        order_event = output_queue.get()
        assert isinstance(order_event, EventOrderAck)

        # 8. 模拟 ExecutionNode 监听 output_queue 并发送到 Kafka
        # （实际中这是在 ExecutionNode._start_output_queue_listener 中进行）
        order_data = {
            "order_id": str(order_event.order.uuid),
            "portfolio_id": order_event.order.portfolio_id,
            "code": order_event.order.code,
            "direction": order_event.order.direction.value,
            "volume": order_event.order.volume,
            "price": str(order_event.order.limit_price) if order_event.order.limit_price else None,
            "timestamp": order_event.order.timestamp.isoformat() if order_event.order.timestamp else None
        }

        # 9. 验证订单数据格式
        assert order_data["code"] == "000001.SZ"
        assert order_data["direction"] == DIRECTION_TYPES.LONG.value
        assert order_data["volume"] == 100

        print(f"✅ 端到端测试通过！")
        print(f"   Kafka消息 → EventPriceUpdate → Portfolio → EventOrderAck → output_queue → 订单数据")
        print(f"   订单ID: {order_data['order_id'][:8]}...")
        print(f"   完整链路验证成功！")
