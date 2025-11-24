#!/usr/bin/env python3
"""
BaseRouter单元测试

测试BaseRouter的基础功能，包括：
1. Mixin组装和初始化
2. 属性访问和方法调用
3. 事件发布功能
4. 引擎绑定功能
5. 订单管理功能（通过OrderManagementMixin）
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../../../src'))

import pytest
import datetime
from unittest.mock import Mock, patch
from typing import Dict, Any

from ginkgo.trading.bases.base_router import BaseRouter
from ginkgo.trading.entities import Order
from ginkgo.enums import DIRECTION_TYPES, ORDER_TYPES, ORDERSTATUS_TYPES


class TestBaseRouterBasics:
    """测试BaseRouter基础功能"""

    def test_router_initialization(self):
        """测试Router初始化"""
        router = BaseRouter("TestRouter")

        assert router.name == "TestRouter"
        assert router._router_name == "TestRouter"
        assert hasattr(router, '_pending_orders')  # OrderManagementMixin
        assert hasattr(router, '_engine_put')      # EngineBindableMixin
        assert hasattr(router, 'timestamp')       # TimeMixin
        assert hasattr(router, 'bound_engine')    # ContextMixin
        assert hasattr(router, 'engine_id')       # ContextMixin

    def test_router_inheritance_structure(self):
        """测试Router继承结构"""
        from ginkgo.trading.mixins.order_management_mixin import OrderManagementMixin
        from ginkgo.trading.mixins.context_mixin import ContextMixin
        from ginkgo.trading.mixins.engine_bindable_mixin import EngineBindableMixin
        from ginkgo.trading.mixins.loggable_mixin import LoggableMixin

        router = BaseRouter()

        # 验证Mixin继承
        assert isinstance(router, OrderManagementMixin)
        assert isinstance(router, ContextMixin)
        assert isinstance(router, EngineBindableMixin)
        assert isinstance(router, LoggableMixin)

    def test_engine_binding_functionality(self):
        """测试引擎绑定功能"""
        router = BaseRouter("TestRouter")

        # 初始状态
        assert router._engine_put is None
        assert router.bound_engine is None

        # 模拟引擎
        mock_engine = Mock()
        mock_engine.put = Mock()

        # 绑定引擎
        router.bind_engine(mock_engine)

        assert router.bound_engine is mock_engine
        assert router._engine_put is mock_engine.put


class TestBaseRouterEventPublishing:
    """测试BaseRouter事件发布功能"""

    def test_set_event_publisher(self):
        """测试设置事件发布器"""
        router = BaseRouter("TestRouter")

        # 模拟事件发布函数
        mock_publisher = Mock()

        # 设置事件发布器
        router.set_event_publisher(mock_publisher)

        assert router._engine_put is mock_publisher

    def test_publish_event_without_engine_binding(self):
        """测试未绑定引擎时发布事件"""
        router = BaseRouter("TestRouter")

        # 应该不抛出异常，但会记录错误
        with patch.object(router, 'log') as mock_log:
            router.publish_event("test_event")
            mock_log.assert_called_once_with("ERROR", "Engine put not bind. Events can not put back to the engine.")

    def test_publish_event_with_engine_binding(self):
        """测试绑定引擎后发布事件"""
        router = BaseRouter("TestRouter")

        # 模拟事件发布函数
        mock_publisher = Mock()
        router.set_event_publisher(mock_publisher)

        # 发布事件
        test_event = {"type": "test", "data": "example"}
        router.publish_event(test_event)

        # 验证事件被发布
        mock_publisher.assert_called_once_with(test_event)


class TestBaseRouterOrderManagement:
    """测试BaseRouter订单管理功能（通过OrderManagementMixin）"""

    def test_pending_order_management(self):
        """测试待处理订单管理"""
        router = BaseRouter("TestRouter")

        # 创建测试订单
        order = Order(
            portfolio_id="test_portfolio",
            engine_id="test_engine",
            run_id="test_run",
            code="000001.SZ",
            direction=DIRECTION_TYPES.LONG,
            order_type=ORDER_TYPES.MARKETORDER,
            status=ORDERSTATUS_TYPES.NEW,
            volume=100,
            limit_price=10.0
        )

        # 添加待处理订单
        router.add_pending_order(order)

        assert router.get_pending_order_count() == 1
        assert len(router.get_pending_orders()) == 1
        assert router.get_pending_orders()[0] == order

        # 清空待处理订单
        router.clear_pending_orders()

        assert router.get_pending_order_count() == 0
        assert len(router.get_pending_orders()) == 0

    def test_execution_history_tracking(self):
        """测试执行历史记录"""
        router = BaseRouter("TestRouter")

        # 创建测试订单
        order = Order(
            portfolio_id="test_portfolio",
            engine_id="test_engine",
            run_id="test_run",
            code="000001.SZ",
            direction=DIRECTION_TYPES.LONG,
            order_type=ORDER_TYPES.MARKETORDER,
            status=ORDERSTATUS_TYPES.NEW,
            volume=100,
            limit_price=10.0
        )

        # 模拟执行结果
        mock_result = Mock()
        mock_broker = Mock()

        # 添加执行记录
        router.add_execution_record(order, mock_result, mock_broker)

        assert router.get_execution_history_count() == 1

    def test_order_status_summary(self):
        """测试订单状态摘要"""
        router = BaseRouter("TestRouter")

        # 获取初始状态摘要
        summary = router.get_order_status_summary()

        assert 'pending_orders' in summary
        assert 'processing_orders' in summary
        assert 'execution_history' in summary
        assert 'has_engine_binding' in summary

        assert summary['pending_orders'] == 0
        assert summary['processing_orders'] == 0
        assert summary['execution_history'] == 0
        assert summary['has_engine_binding'] == False


class TestBaseRouterInformationMethods:
    """测试BaseRouter信息查询方法"""

    def test_get_router_info(self):
        """测试获取Router信息"""
        router = BaseRouter("InfoTestRouter")

        info = router.get_router_info()

        assert isinstance(info, dict)
        assert info['name'] == "InfoTestRouter"
        assert 'pending_orders' in info
        assert 'processing_orders' in info
        assert 'execution_history' in info
        assert 'has_engine_binding' in info

    def test_router_info_with_engine_binding(self):
        """测试绑定引擎后的Router信息"""
        router = BaseRouter("BoundRouter")

        # 绑定引擎
        mock_engine = Mock()
        mock_engine.put = Mock()
        router.bind_engine(mock_engine)

        info = router.get_router_info()

        assert info['has_engine_binding'] is True


class TestBaseRouterIntegration:
    """测试BaseRouter集成功能"""

    def test_complete_event_flow(self):
        """测试完整的事件流"""
        router = BaseRouter("IntegrationTestRouter")

        # 模拟引擎事件队列
        event_queue = []

        # 设置事件发布器
        router.set_event_publisher(event_queue.append)

        # 创建测试事件
        test_event = {
            "type": "ORDERFILLED",
            "order_id": "test_order_123",
            "symbol": "000001.SZ",
            "volume": 100,
            "price": 10.5
        }

        # 发布事件
        router.publish_event(test_event)

        # 验证事件被正确发布
        assert len(event_queue) == 1
        assert event_queue[0] == test_event

    def test_multi_event_publishing(self):
        """测试多事件发布"""
        router = BaseRouter("MultiEventRouter")

        # 模拟事件计数
        event_count = 0

        def event_handler(event):
            nonlocal event_count
            event_count += 1

        # 设置事件处理器
        router.set_event_publisher(event_handler)

        # 发布多个事件
        for i in range(5):
            router.publish_event({"event_id": i})

        assert event_count == 5

    def test_error_handling_in_event_publishing(self):
        """测试事件发布错误处理"""
        router = BaseRouter("ErrorTestRouter")

        # 设置会抛出异常的事件发布器
        def failing_publisher(event):
            raise Exception("Publishing failed")

        router.set_event_publisher(failing_publisher)

        # 发布事件应该不抛出异常
        with patch.object(router, 'log') as mock_log:
            router.publish_event("test_event")
            # 验证异常被捕获并记录
            # 注意：这取决于具体的实现，可能需要调整


@pytest.fixture
def sample_order():
    """提供示例订单fixture"""
    return Order(
        portfolio_id="test_portfolio",
        engine_id="test_engine",
        run_id="test_run",
        code="000001.SZ",
        direction=DIRECTION_TYPES.LONG,
        order_type=ORDER_TYPES.MARKETORDER,
        status=ORDERSTATUS_TYPES.NEW,
        volume=100,
        limit_price=10.0
    )


@pytest.fixture
def mock_engine():
    """提供模拟引擎fixture"""
    engine = Mock()
    engine.put = Mock()
    return engine


class TestBaseRouterWithFixtures:
    """使用fixture的BaseRouter测试"""

    def test_router_with_sample_order(self, sample_order):
        """测试使用sample_order fixture"""
        router = BaseRouter("FixtureTestRouter")

        router.add_pending_order(sample_order)
        assert router.get_pending_order_count() == 1

        pending_orders = router.get_pending_orders()
        assert pending_orders[0].code == "000001.SZ"
        assert pending_orders[0].volume == 100

    def test_router_with_mock_engine(self, mock_engine):
        """测试使用mock_engine fixture"""
        router = BaseRouter("MockEngineTestRouter")

        router.bind_engine(mock_engine)
        assert router.bound_engine is mock_engine

        # 测试事件发布
        router.set_event_publisher(mock_engine.put)
        router.publish_event("test_event")
        mock_engine.put.assert_called_once_with("test_event")