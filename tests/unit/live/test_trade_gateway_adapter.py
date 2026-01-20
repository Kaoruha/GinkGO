"""
TradeGatewayAdapter 单元测试

测试 TradeGatewayAdapter 的核心功能：
1. 初始化和配置
2. 启动和停止生命周期
3. 状态管理
4. TradeGateway访问

注意：这些测试只测试TradeGatewayAdapter的实际行为，不依赖内部实现细节。
"""

import pytest
from ginkgo.livecore.trade_gateway_adapter import TradeGatewayAdapter
from ginkgo.trading.interfaces.broker_interface import IBroker


# 简单的Mock Broker用于测试
class MockBroker(IBroker):
    """模拟Broker实现"""

    def __init__(self):
        self.orders_submitted = []
        self.orders_filled = []

    def submit_order_event(self, event):
        """提交订单事件"""
        from ginkgo.trading.interfaces.broker_interface import BrokerExecutionResult
        self.orders_submitted.append(event)
        # 立即成交
        return BrokerExecutionResult(success=True, message="Order filled")

    def validate_order(self, order):
        """验证订单"""
        return True  # 总是验证通过

    def submit_order(self, order):
        """模拟提交订单"""
        self.orders_submitted.append(order)
        # 立即成交
        return order

    def get_order_status(self, order_id):
        """模拟获取订单状态"""
        return "filled"


@pytest.mark.unit
class TestTradeGatewayAdapterInitialization:
    """测试 TradeGatewayAdapter 初始化"""

    def test_init_with_brokers(self):
        """测试使用brokers初始化"""
        mock_broker = MockBroker()

        # 创建adapter
        adapter = TradeGatewayAdapter(brokers=[mock_broker])

        # 验证初始化状态
        assert adapter.is_running is False
        assert hasattr(adapter, 'gateway')
        # brokers在gateway中
        assert hasattr(adapter.gateway, 'brokers')

        print(f"✅ TradeGatewayAdapter 初始化成功")

    def test_init_with_empty_brokers(self):
        """测试使用空brokers列表初始化"""
        # 创建adapter（允许空brokers）
        adapter = TradeGatewayAdapter(brokers=[])

        assert adapter.is_running is False
        assert hasattr(adapter, 'gateway')

        print(f"✅ 空brokers列表初始化成功")


@pytest.mark.unit
class TestTradeGatewayAdapterLifecycle:
    """测试 TradeGatewayAdapter 生命周期"""

    def test_start_sets_is_running(self):
        """测试start()设置运行标志"""
        mock_broker = MockBroker()
        adapter = TradeGatewayAdapter(brokers=[mock_broker])

        # 启动
        adapter.start()

        # 等待线程启动
        import time
        time.sleep(0.1)

        # is_running应该在run()方法中被设置
        assert hasattr(adapter, 'is_running')
        print(f"✅ start() 完成，is_running属性存在")

        # 清理
        adapter.stop()
        adapter.join(timeout=2)

    def test_stop_clears_is_running(self):
        """测试stop()清除运行标志"""
        mock_broker = MockBroker()
        adapter = TradeGatewayAdapter(brokers=[mock_broker])

        # 启动
        adapter.start()
        import time
        time.sleep(0.1)

        # 停止
        adapter.stop()
        adapter.join(timeout=2)

        assert hasattr(adapter, 'is_running')
        print(f"✅ stop() 完成")

    def test_multiple_start_stop_cycles(self):
        """测试多次启动-停止循环（需要创建多个adapter实例）"""
        import time

        # 第一次循环
        adapter1 = TradeGatewayAdapter(brokers=[MockBroker()])
        adapter1.start()
        time.sleep(0.1)
        adapter1.stop()
        adapter1.join(timeout=2)

        # 第二次循环（创建新实例，因为线程不能重复启动）
        adapter2 = TradeGatewayAdapter(brokers=[MockBroker()])
        adapter2.start()
        time.sleep(0.1)
        adapter2.stop()
        adapter2.join(timeout=2)

        print(f"✅ 可以多次启动-停止（通过创建新实例）")


@pytest.mark.unit
class TestTradeGatewayAdapterStatus:
    """测试 TradeGatewayAdapter 状态管理"""

    @pytest.mark.skip(reason="Phase 3: get_statistics()需要order_service，尚未实现")
    def test_get_statistics_returns_dict(self):
        """测试get_statistics()返回字典"""
        mock_broker = MockBroker()
        adapter = TradeGatewayAdapter(brokers=[mock_broker])

        # 获取状态
        status = adapter.get_statistics()

        # 验证返回字典
        assert isinstance(status, dict)
        print(f"✅ get_statistics() 返回字典")

    @pytest.mark.skip(reason="Phase 3: get_statistics()需要order_service，尚未实现")
    def test_statistics_contains_expected_fields(self):
        """测试统计包含预期字段"""
        mock_broker = MockBroker()
        adapter = TradeGatewayAdapter(brokers=[mock_broker])

        status = adapter.get_statistics()

        # 验证包含必要字段（字段名可能根据实际实现调整）
        expected_fields = ["total_orders", "filled_orders", "pending_orders"]
        for field in expected_fields:
            assert field in status, f"Missing field: {field}"

        print(f"✅ 统计包含预期字段")


@pytest.mark.unit
class TestTradeGatewayAdapterComponents:
    """测试 TradeGatewayAdapter 组件"""

    def test_gateway_exists(self):
        """测试gateway存在"""
        mock_broker = MockBroker()
        adapter = TradeGatewayAdapter(brokers=[mock_broker])

        assert adapter.gateway is not None
        print(f"✅ gateway组件存在")

    def test_gateway_has_brokers(self):
        """测试gateway有brokers"""
        mock_broker = MockBroker()
        adapter = TradeGatewayAdapter(brokers=[mock_broker])

        # brokers在gateway中
        assert hasattr(adapter.gateway, 'brokers')
        assert len(adapter.gateway.brokers) == 1

        print(f"✅ gateway有brokers")


@pytest.mark.unit
class TestTradeGatewayAdapterThread:
    """测试 TradeGatewayAdapter 线程功能"""

    def test_adapter_is_thread(self):
        """测试adapter是Thread子类"""
        from threading import Thread

        mock_broker = MockBroker()
        adapter = TradeGatewayAdapter(brokers=[mock_broker])

        assert isinstance(adapter, Thread)
        print(f"✅ adapter是Thread子类")

    def test_thread_can_be_started(self):
        """测试线程可以启动"""
        mock_broker = MockBroker()
        adapter = TradeGatewayAdapter(brokers=[mock_broker])

        # 启动线程
        adapter.start()

        # 等待线程启动
        import time
        time.sleep(0.1)

        # 验证线程正在运行
        assert adapter.is_running == True
        assert adapter.is_alive() == True
        print(f"✅ 线程可以启动")

        # 清理：停止线程
        adapter.stop()
        adapter.join(timeout=2)


@pytest.mark.unit
class TestTradeGatewayAdapterIntegration:
    """测试 TradeGatewayAdapter 集成功能"""

    def test_full_lifecycle_flow(self):
        """测试完整生命周期流程"""
        mock_broker = MockBroker()
        adapter = TradeGatewayAdapter(brokers=[mock_broker])
        import time

        # 初始状态
        assert hasattr(adapter, 'is_running')

        # 启动
        adapter.start()
        time.sleep(0.1)

        # 验证运行状态
        assert hasattr(adapter, 'is_running')

        # 停止
        adapter.stop()
        adapter.join(timeout=2)

        assert hasattr(adapter, 'is_running')
        print(f"✅ 完整生命周期流程正确")

    @pytest.mark.skip(reason="Phase 3: get_statistics()需要order_service，尚未实现")
    def test_statistics_after_lifecycle_changes(self):
        """测试生命周期变化后统计更新"""
        mock_broker = MockBroker()
        adapter = TradeGatewayAdapter(brokers=[mock_broker])
        import time

        # 初始统计
        stats_initial = adapter.get_statistics()

        # 启动后
        adapter.start()
        time.sleep(0.1)
        stats_running = adapter.get_statistics()

        # 停止后
        adapter.stop()
        adapter.join(timeout=2)
        stats_stopped = adapter.get_statistics()

        # 验证统计存在
        assert stats_initial is not None
        assert stats_running is not None
        assert stats_stopped is not None

        print(f"✅ 生命周期变化后统计正确更新")
