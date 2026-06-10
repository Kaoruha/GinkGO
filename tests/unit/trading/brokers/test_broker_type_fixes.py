# #5534 #5533 #5536 #5535 #5484
# Broker 类型错误批量修复测试
"""
TDD 测试：验证 5 个 broker 类型错误的修复。
按依赖顺序逐个通过 RED→GREEN 循环。
"""
import pytest
from decimal import Decimal


class TestBrokerInstantiationSyncContext:
    """#5534: BaseBroker 在同步上下文中实例化不应崩溃（Python 3.10 兼容）"""

    def test_base_broker_instantiates_without_event_loop(self):
        """在同步上下文（无事件循环）中实例化 BaseBroker 不应 raise RuntimeError"""
        from ginkgo.trading.brokers.base_broker import BaseBroker
        from ginkgo.trading.brokers.interfaces import BrokerType

        # 不应在 __init__ 中 raise RuntimeError
        broker = BaseBroker(BrokerType.SIM)
        assert broker is not None

    def test_sim_broker_instantiates_without_event_loop(self):
        """SimBroker 在同步上下文中实例化不应崩溃"""
        from ginkgo.trading.brokers.sim_broker import SimBroker

        broker = SimBroker(name="TestBroker")
        assert broker is not None


class TestExecutionStatusCancelledSpelling:
    """#5533: ExecutionStatus/OrderStatus 枚举拼写一致性"""

    def test_execution_status_is_final_covers_cancelled(self):
        """ExecutionStatus.CANCELLED 应被 is_final_status 正确识别"""
        from ginkgo.trading.brokers.base_broker import ExecutionStatus

        cancelled_result = type('obj', (object,), {'status': ExecutionStatus.CANCELLED})()
        # is_final_status 是 ExecutionResult 的 property
        from ginkgo.trading.brokers.base_broker import ExecutionResult
        result = ExecutionResult(order_id="test", status=ExecutionStatus.CANCELLED)
        assert result.is_final_status is True

    def test_order_status_cancelled_attribute_exists(self):
        """OrderStatus.CANCELLED 属性应存在"""
        from ginkgo.trading.brokers.interfaces import OrderStatus
        assert hasattr(OrderStatus, 'CANCELLED')
        assert OrderStatus.CANCELLED == 5

    def test_execution_status_cancelled_attribute_exists(self):
        """ExecutionStatus.CANCELLED 属性应存在"""
        from ginkgo.trading.brokers.base_broker import ExecutionStatus
        assert hasattr(ExecutionStatus, 'CANCELLED')
        assert ExecutionStatus.CANCELLED.value == "cancelled"


class TestLiveBrokerBaseInitType:
    """#5536: LiveBrokerBase 实例化验证（bases.BaseBroker 接受 name: str）"""

    def test_ashare_broker_instantiates_successfully(self):
        """AShareBroker 应能正常实例化"""
        from ginkgo.trading.brokers.ashare_broker import AShareBroker

        broker = AShareBroker(name="test_ashare")
        assert broker is not None
        assert broker.name == "test_ashare"

    def test_sim_broker_has_current_market_data(self):
        """#5535: SimBroker 应继承 _current_market_data（由 bases.BaseBroker 初始化）"""
        from ginkgo.trading.brokers.sim_broker import SimBroker

        broker = SimBroker()
        assert hasattr(broker, '_current_market_data')
        assert isinstance(broker._current_market_data, dict)


class TestAShareBrokerRejectedStatus:
    """#5484: AShareBroker 被拒绝的订单应使用 REJECTED 而非 NEW 状态"""

    def test_rejected_uses_correct_status(self):
        """验证 AShareBroker 中所有 # REJECTED 注释处使用 ORDERSTATUS_TYPES.REJECTED"""
        import inspect
        from ginkgo.trading.brokers.ashare_broker import AShareBroker
        from ginkgo.enums import ORDERSTATUS_TYPES

        source = inspect.getsource(AShareBroker)
        # 不应存在 NEW + REJECTED 注释的组合
        assert 'ORDERSTATUS_TYPES.NEW,  # REJECTED' not in source, \
            "Found ORDERSTATUS_TYPES.NEW with # REJECTED comment - should use ORDERSTATUS_TYPES.REJECTED"


class TestTradeGatewayRejectedStatus:
    """#5533: trade_gateway 中不应有 NEW 伪装为 REJECTED 的任何变体"""

    def test_no_new_with_rejected_comment(self):
        """trade_gateway.py 中不应存在任何形式的 NEW + # REJECTED 组合"""
        import inspect
        from ginkgo.trading.gateway.trade_gateway import TradeGateway

        source = inspect.getsource(TradeGateway)
        # 覆盖逗号和冒号两种语法
        assert 'NEW,  # REJECTED' not in source, \
            "Found ORDERSTATUS_TYPES.NEW, with # REJECTED comment"
        assert 'NEW:  # REJECTED' not in source, \
            "Found ORDERSTATUS_TYPES.NEW: with # REJECTED comment"

    def test_handle_execution_result_removes_rejected_tracking(self):
        """_handle_execution_result 应对 REJECTED 状态移除订单跟踪"""
        import inspect
        from ginkgo.trading.gateway.trade_gateway import TradeGateway

        source = inspect.getsource(TradeGateway._handle_execution_result)
        # 终态列表应包含 REJECTED 而非 NEW
        assert 'ORDERSTATUS_TYPES.REJECTED' in source, \
            "_handle_execution_result should include REJECTED in terminal status list"
        # 终态列表不应包含 NEW（NEW 不是终态）
        # 排除注释和字符串中的 NEW
        for line in source.split('\n'):
            stripped = line.strip()
            if 'result.status in [' in stripped and 'ORDERSTATUS_TYPES' in stripped:
                assert 'ORDERSTATUS_TYPES.NEW' not in stripped, \
                    f"Terminal status list should not contain NEW: {stripped}"
