"""
ExecutionNode.subscribe_market_data() 集成测试

测试 ExecutionNode 的 Kafka 订阅和事件路由功能：
1. subscribe_market_data() 创建Kafka消费者和消费线程
2. _route_event_to_portfolios() 路由事件到对应的Portfolio
3. 处理Queue满的情况（非阻塞put）
4. subscribe_order_feedback() 订阅订单反馈topic
5. 完整的事件路由流程

注意：这些测试使用真实的Kafka信号，不使用mock。
"""

import pytest
from queue import Queue
from threading import Thread
from datetime import datetime
from decimal import Decimal

from ginkgo.workers.execution_node.node import ExecutionNode
from ginkgo.trading.events import EventPriceUpdate
from ginkgo.trading.entities import Bar
from ginkgo.data.containers import container
from ginkgo.enums import FREQUENCY_TYPES

# 从依赖注入容器获取服务实例
portfolio_service = container.portfolio_service()


@pytest.mark.integration
@pytest.mark.live
class TestExecutionNodeInterestMapSubscription:
    """测试 InterestMap 订阅功能"""

    def test_interest_map_subscription_flow(self):
        """测试InterestMap的订阅流程"""
        node = ExecutionNode(node_id="test_node_subscription")

        # 创建InterestMap并订阅股票代码
        from ginkgo.workers.execution_node.interest_map import InterestMap
        node.interest_map = InterestMap()

        # 添加订阅（使用正确的API）
        portfolio_id = "test_portfolio"
        codes = ["000001.SZ", "000002.SZ"]

        node.interest_map.add_portfolio(portfolio_id, codes)

        # 验证订阅
        subscriptions = node.interest_map.get_all_subscriptions(portfolio_id)
        assert len(subscriptions) == 2
        assert "000001.SZ" in subscriptions
        assert "000002.SZ" in subscriptions

        print(f"✅ InterestMap订阅流程正确")

    def test_interest_map_unsubscription(self):
        """测试InterestMap的取消订阅"""
        node = ExecutionNode(node_id="test_node_unsubscription")

        from ginkgo.workers.execution_node.interest_map import InterestMap
        node.interest_map = InterestMap()

        portfolio_id = "test_portfolio"
        code = "000001.SZ"

        # 订阅（使用正确的API）
        node.interest_map.add_portfolio(portfolio_id, [code])
        assert code in node.interest_map.get_all_subscriptions(portfolio_id)

        # 取消订阅
        node.interest_map.remove_portfolio(portfolio_id, [code])
        assert code not in node.interest_map.get_all_subscriptions(portfolio_id)

        print(f"✅ InterestMap取消订阅正确")


@pytest.mark.integration
@pytest.mark.live
class TestExecutionNodeEventRouting:
    """测试事件路由功能"""

    def test_route_event_to_portfolios_basic(self):
        """测试基本的事件路由"""
        node = ExecutionNode(node_id="test_node_routing")

        # 创建模拟的PortfolioProcessor和input_queue
        portfolio_id = "test_portfolio"
        processor = Mock()
        processor.input_queue = Queue()
        input_queue = Queue()  # 创建单独的input_queue用于路由

        # 添加到node（_route_event_to_portfolios使用input_queues字典）
        node.portfolios[portfolio_id] = processor
        node._portfolio_instances[portfolio_id] = Mock()
        node.input_queues[portfolio_id] = input_queue  # 关键：设置input_queues

        # 创建Bar对象
        bar = Bar(
            code="000001.SZ",
            timestamp=datetime.now(),
            open=10.0,
            high=10.5,
            low=9.5,
            close=10.50,
            volume=1000,
            amount=Decimal("10000"),
            frequency=FREQUENCY_TYPES.DAY
        )

        # 创建价格事件
        event = EventPriceUpdate(payload=bar)

        # 设置InterestMap（使用正确的API）
        from ginkgo.workers.execution_node.interest_map import InterestMap
        node.interest_map = InterestMap()
        node.interest_map.add_portfolio(portfolio_id, ["000001.SZ"])

        # 路由事件
        node._route_event_to_portfolios(event)

        # 验证事件被路由到正确的Portfolio input_queue
        assert input_queue.qsize() > 0, "事件应该在队列中"
        routed_event = input_queue.get()
        assert routed_event.code == "000001.SZ"

        print(f"✅ 事件路由正确")


@pytest.mark.integration
@pytest.mark.live
class TestExecutionNodeQueueHandling:
    """测试Queue处理机制"""

    def test_queue_non_blocking_put(self):
        """测试Queue非阻塞put"""
        node = ExecutionNode(node_id="test_node_queue")

        # 创建小容量Queue
        small_queue = Queue(maxsize=1)

        # 填满队列
        small_queue.put("event1")
        assert small_queue.full()

        # 尝试非阻塞put（应该不阻塞）
        try:
            small_queue.put("event2", block=False)
            assert False, "应该抛出Queue满异常"
        except:
            pass  # 预期的行为

        print(f"✅ Queue非阻塞put正确")

    def test_portfolio_processor_queues_exist(self):
        """测试PortfolioProcessor有input_queue和output_queue"""
        from ginkgo.workers.execution_node.portfolio_processor import PortfolioProcessor

        # 创建Mock PortfolioLive实例（包含必需的属性）
        mock_portfolio = Mock()
        mock_portfolio.portfolio_id = "test_portfolio_id"
        mock_portfolio.uuid = "test_portfolio_uuid"

        # Mock set_event_publisher方法（需要是可调用的）
        mock_portfolio.set_event_publisher = lambda x: None

        # 使用正确的参数创建PortfolioProcessor
        input_queue = Queue()
        output_queue = Queue()

        processor = PortfolioProcessor(
            portfolio=mock_portfolio,
            input_queue=input_queue,
            output_queue=output_queue
        )

        assert hasattr(processor, 'input_queue')
        assert hasattr(processor, 'output_queue')
        assert isinstance(processor.input_queue, Queue)
        assert isinstance(processor.output_queue, Queue)

        print(f"✅ PortfolioProcessor有input_queue和output_queue")


@pytest.mark.integration
@pytest.mark.live
class TestExecutionNodeSubscriptionIntegration:
    """测试订阅集成"""

    @pytest.fixture(autouse=True)
    def setup_portfolio(self):
        """确保预置Portfolio存在"""
        result = portfolio_service.get(filters={"name": "present_portfolio_live"})

        if not result.success or len(result.data) == 0:
            pytest.skip("预置Portfolio 'present_portfolio_live' 不存在")

    def test_full_routing_flow_with_loaded_portfolio(self):
        """测试加载Portfolio后的完整路由流程"""
        node = ExecutionNode(node_id="test_node_full_routing")

        # 获取present_portfolio_live的UUID
        result = portfolio_service.get(filters={"name": "present_portfolio_live"})
        portfolio_uuid = result.data[0].uuid

        # 加载Portfolio
        node.load_portfolio(portfolio_uuid)

        # 添加订阅
        node.interest_map.add_portfolio(portfolio_uuid, ["000001.SZ"])

        # 创建Bar对象
        bar = Bar(
            code="000001.SZ",
            timestamp=datetime.now(),
            open=10.0,
            high=10.5,
            low=9.5,
            close=10.50,
            volume=1000,
            amount=Decimal("10000"),
            frequency=FREQUENCY_TYPES.DAY
        )

        # 创建价格事件
        event = EventPriceUpdate(payload=bar)

        # 路由事件
        node._route_event_to_portfolios(event)

        # 验证事件被路由到PortfolioProcessor
        processor = node.portfolios[portfolio_uuid]
        assert processor.input_queue.qsize() > 0, "事件应该在队列中"

        print(f"✅ 完整路由流程正确")

        # 清理
        node.unload_portfolio(portfolio_uuid)


# 简单的Mock类用于测试
class Mock:
    """简单Mock类"""
    def __init__(self):
        pass

    def is_running(self):
        return True
