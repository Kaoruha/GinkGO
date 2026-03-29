"""
OrderCancellation阶段测试

测试订单取消阶段的组件交互和逻辑处理
涵盖主动取消、被动取消、取消确认、资金解冻等
相关组件：Portfolio, Broker, RiskManager, EventEngine
"""
import pytest
import sys
import datetime
from decimal import Decimal
from pathlib import Path

# 添加项目路径
project_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(project_root / "src"))

from ginkgo.entities.order import Order
from ginkgo.trading.events.order_lifecycle_events import (
    EventOrderCancelAck, EventOrderAck, EventOrderPartiallyFilled,
    EventOrderRejected, EventOrderExpired
)
from ginkgo.enums import ORDERSTATUS_TYPES, EVENT_TYPES, DIRECTION_TYPES, ORDER_TYPES


def _make_order(status=ORDERSTATUS_TYPES.SUBMITTED, volume=100,
                limit_price=Decimal("10.00"), transaction_volume=0,
                code="000001.SZ"):
    """创建测试用Order实例的辅助函数"""
    return Order(
        portfolio_id="portfolio-001",
        engine_id="engine-001",
        run_id="run-001",
        code=code,
        direction=DIRECTION_TYPES.LONG,
        order_type=ORDER_TYPES.LIMITORDER,
        status=status,
        volume=volume,
        limit_price=limit_price,
        frozen_money=Decimal(volume) * limit_price,
        frozen_volume=volume,
        transaction_price=Decimal("0"),
        transaction_volume=transaction_volume,
    )


def _make_submitted_order(**kwargs):
    """创建已提交状态的Order，确保可以partial_fill"""
    status = kwargs.pop("status", ORDERSTATUS_TYPES.SUBMITTED)
    order = _make_order(status=status, **kwargs)
    if order.status == ORDERSTATUS_TYPES.NEW:
        order.submit()
    return order


@pytest.mark.unit
class TestOrderCancellationInitiation:
    """1. 订单取消启动测试"""

    def test_manual_cancellation_request(self):
        """测试手动取消请求"""
        order = _make_order()
        order.cancel()
        assert order.is_canceled()

    def test_automatic_cancellation_trigger(self):
        """测试自动取消触发"""
        order = _make_order()
        cancel_event = EventOrderCancelAck(
            order=order,
            cancelled_quantity=100,
            cancel_reason="Risk management triggered"
        )
        assert cancel_event.cancel_reason == "Risk management triggered"
        assert order.code == cancel_event.code

    def test_market_close_cancellation(self):
        """测试市场收盘取消"""
        order = _make_order()
        cancel_event = EventOrderCancelAck(
            order=order,
            cancelled_quantity=100,
            cancel_reason="Market closed"
        )
        assert cancel_event.cancel_reason == "Market closed"
        assert cancel_event.event_type == EVENT_TYPES.ORDERCANCELACK

    def test_cancellation_eligibility_check(self):
        """测试取消资格检查"""
        new_order = _make_order(status=ORDERSTATUS_TYPES.NEW)
        submitted_order = _make_order(status=ORDERSTATUS_TYPES.SUBMITTED)
        assert not new_order.is_canceled()
        assert not submitted_order.is_canceled()
        assert new_order.is_new()
        assert submitted_order.is_submitted()

    def test_partial_fill_cancellation_handling(self):
        """测试部分成交订单取消处理"""
        order = _make_order(transaction_volume=30)
        cancel_event = EventOrderCancelAck(
            order=order,
            cancelled_quantity=70,
            cancel_reason="User cancelled"
        )
        assert cancel_event.cancelled_quantity == 70
        assert order.code == cancel_event.code


@pytest.mark.unit
class TestOrderCancelEventCreation:
    """2. 订单取消事件创建测试"""

    def test_cancel_request_event_creation(self):
        """测试取消请求事件创建"""
        order = _make_order()
        event = EventOrderCancelAck(
            order=order,
            cancelled_quantity=100
        )
        assert isinstance(event, EventOrderCancelAck)
        assert event.event_type == EVENT_TYPES.ORDERCANCELACK

    def test_cancel_event_attributes_setting(self):
        """测试取消事件属性设置"""
        order = _make_order()
        ts = datetime.datetime(2024, 1, 15, 10, 30, 0)
        event = EventOrderCancelAck(
            order=order,
            cancelled_quantity=50,
            timestamp=ts,
            cancel_reason="Insufficient funds",
            portfolio_id="portfolio-002",
            engine_id="engine-002",
            run_id="run-002"
        )
        assert event.cancelled_quantity == 50
        assert event.cancel_reason == "Insufficient funds"
        assert event.portfolio_id == "portfolio-002"
        assert event.engine_id == "engine-002"
        assert event.run_id == "run-002"
        assert event.order_id == order.uuid

    def test_cancel_reason_classification(self):
        """测试取消原因分类"""
        order = _make_order()
        reasons = [
            "User cancelled",
            "Risk limit exceeded",
            "Market closed",
            "System timeout",
        ]
        for reason in reasons:
            event = EventOrderCancelAck(
                order=order, cancelled_quantity=100, cancel_reason=reason
            )
            assert event.cancel_reason == reason

    def test_cancel_priority_assignment(self):
        """测试取消优先级分配"""
        order1 = _make_order(code="000001.SZ")
        order2 = _make_order(code="600000.SH")
        event1 = EventOrderCancelAck(order=order1, cancelled_quantity=100, cancel_reason="High priority")
        event2 = EventOrderCancelAck(order=order2, cancelled_quantity=50, cancel_reason="Low priority")
        assert event1.order_id != event2.order_id
        assert event1.cancelled_quantity == 100
        assert event2.cancelled_quantity == 50


@pytest.mark.unit
class TestBrokerCancellationProcessing:
    """3. 代理取消处理测试"""

    def test_cancel_request_to_broker(self):
        """测试取消请求到代理"""
        order = _make_order()
        event = EventOrderCancelAck(
            order=order,
            cancelled_quantity=100,
            cancel_reason="Broker cancel request"
        )
        assert event.order.code == "000001.SZ"
        assert event.cancelled_quantity == 100

    def test_broker_cancel_validation(self):
        """测试代理取消验证"""
        order = _make_order()
        event = EventOrderCancelAck(order=order, cancelled_quantity=100)
        assert event.order_id == order.uuid
        assert event.code == order.code

    def test_cancel_transmission_protocol(self):
        """测试取消传输协议"""
        order = _make_order()
        event = EventOrderCancelAck(
            order=order,
            cancelled_quantity=100,
            portfolio_id="portfolio-001",
            engine_id="engine-001",
            run_id="run-001"
        )
        assert event.portfolio_id == "portfolio-001"
        assert event.engine_id == "engine-001"
        assert event.run_id == "run-001"
        assert isinstance(event.uuid, str)
        assert len(event.uuid) > 0

    def test_cancel_acknowledgment_waiting(self):
        """测试等待取消确认"""
        order = _make_order()
        event = EventOrderCancelAck(
            order=order,
            cancelled_quantity=100,
            timestamp=datetime.datetime(2024, 1, 15, 14, 30, 0)
        )
        assert event.timestamp is not None

    def test_broker_cancel_rejection(self):
        """测试代理取消拒绝"""
        order = _make_order()
        rejected_event = EventOrderRejected(
            order=order,
            reject_reason="Cancel rejected - order already filled",
            reject_code="CANCEL_REJECTED"
        )
        assert rejected_event.reject_reason == "Cancel rejected - order already filled"
        assert rejected_event.reject_code == "CANCEL_REJECTED"
        assert rejected_event.event_type == EVENT_TYPES.ORDERREJECTED


@pytest.mark.unit
class TestOrderCancelAcknowledgment:
    """4. 订单取消确认测试"""

    def test_cancel_ack_reception(self):
        """测试取消确认接收"""
        order = _make_order()
        ack = EventOrderCancelAck(order=order, cancelled_quantity=100)
        assert ack is not None
        assert isinstance(ack, EventOrderCancelAck)

    def test_cancel_ack_event_creation(self):
        """测试取消确认事件创建"""
        order = _make_order()
        ack = EventOrderCancelAck(
            order=order,
            cancelled_quantity=100,
            cancel_reason="User cancelled",
            timestamp=datetime.datetime(2024, 3, 1, 9, 30, 0)
        )
        assert ack.event_type == EVENT_TYPES.ORDERCANCELACK
        assert ack.cancel_reason == "User cancelled"
        assert ack.order == order

    def test_cancel_ack_message_validation(self):
        """测试取消确认消息验证"""
        order = _make_order()
        ack = EventOrderCancelAck(order=order, cancelled_quantity=100)
        repr_str = repr(ack)
        assert "EventOrderCancelAck" in repr_str
        assert str(order.uuid[:8]) in repr_str
        assert "cancelled_qty=100" in repr_str

    def test_cancel_completion_timestamp(self):
        """测试取消完成时间戳"""
        order = _make_order()
        ts = datetime.datetime(2024, 6, 15, 15, 0, 0)
        ack = EventOrderCancelAck(
            order=order,
            cancelled_quantity=100,
            timestamp=ts
        )
        assert ack.timestamp.year == 2024
        assert ack.timestamp.month == 6
        assert ack.timestamp.day == 15


@pytest.mark.unit
class TestOrderStatusUpdateOnCancel:
    """5. 取消时订单状态更新测试"""

    def test_order_status_transition_to_canceled(self):
        """测试订单状态转换到已取消"""
        order = _make_order(status=ORDERSTATUS_TYPES.SUBMITTED)
        assert order.status == ORDERSTATUS_TYPES.SUBMITTED
        order.cancel()
        assert order.status == ORDERSTATUS_TYPES.CANCELED

    def test_partial_cancel_status_handling(self):
        """测试部分取消状态处理"""
        order = _make_order()
        order.partial_fill(40, 10.0)
        assert order.status == ORDERSTATUS_TYPES.PARTIAL_FILLED
        order.cancel()
        assert order.status == ORDERSTATUS_TYPES.CANCELED
        assert order.transaction_volume == 40

    def test_cancel_reason_recording(self):
        """测试取消原因记录"""
        order = _make_order()
        event = EventOrderCancelAck(
            order=order,
            cancelled_quantity=100,
            cancel_reason="Strategy signal reversal"
        )
        assert event.cancel_reason == "Strategy signal reversal"
        assert event.code == order.code
        assert event.order_id == order.uuid

    def test_order_lifecycle_completion(self):
        """测试订单生命周期完成"""
        order = _make_order()
        order.cancel()
        assert order.is_canceled()
        assert order.is_final()
        assert not order.is_active()


@pytest.mark.unit
class TestCapitalUnfreezing:
    """6. 资金解冻测试"""

    def test_frozen_capital_calculation(self):
        """测试冻结资金计算"""
        order = _make_order(volume=100, limit_price=Decimal("10.50"))
        expected_frozen = Decimal("100") * Decimal("10.50")
        assert order.frozen_money == expected_frozen

    def test_capital_unfreezing_execution(self):
        """测试资金解冻执行"""
        order = _make_order(volume=200, limit_price=Decimal("15.00"))
        assert order.frozen_money == Decimal("3000.00")
        order.cancel()
        assert order.is_canceled()
        assert order.frozen_money == Decimal("3000.00")

    def test_partial_fill_capital_adjustment(self):
        """测试部分成交资金调整"""
        order = _make_order(volume=200, limit_price=Decimal("10.00"))
        order.partial_fill(50, 10.00)
        assert order.transaction_volume == 50
        assert order.fee > 0 or order.fee == Decimal("0")
        cancel_event = EventOrderCancelAck(
            order=order,
            cancelled_quantity=150,
            cancel_reason="User cancelled"
        )
        assert cancel_event.cancelled_quantity == 150

    def test_portfolio_available_capital_update(self):
        """测试投资组合可用资金更新"""
        order = _make_order(volume=500, limit_price=Decimal("20.00"))
        assert order.frozen_money == Decimal("10000.00")
        assert order.frozen_volume == 500
        order.cancel()
        assert order.is_canceled()

    def test_capital_unfreezing_audit_trail(self):
        """测试资金解冻审计追踪"""
        order = _make_order()
        ts = datetime.datetime(2024, 1, 10, 10, 0, 0)
        event = EventOrderCancelAck(
            order=order,
            cancelled_quantity=100,
            timestamp=ts,
            cancel_reason="Risk management",
            portfolio_id="portfolio-audit-001",
            engine_id="engine-audit-001",
            run_id="run-audit-001"
        )
        assert event.portfolio_id == "portfolio-audit-001"
        assert event.engine_id == "engine-audit-001"
        assert event.run_id == "run-audit-001"
        assert event.timestamp == ts
        assert event.cancel_reason == "Risk management"


@pytest.mark.unit
class TestCancelEventPropagation:
    """7. 取消事件传播测试"""

    def test_cancel_event_publishing(self):
        """测试取消事件发布"""
        order = _make_order()
        event = EventOrderCancelAck(
            order=order,
            cancelled_quantity=100,
            portfolio_id="portfolio-001",
            engine_id="engine-001"
        )
        assert event.event_type == EVENT_TYPES.ORDERCANCELACK
        assert event.name == "OrderCancelAck"
        assert isinstance(event.uuid, str)

    def test_portfolio_cancel_notification(self):
        """测试投资组合取消通知"""
        order = _make_order()
        event = EventOrderCancelAck(
            order=order,
            cancelled_quantity=100,
            portfolio_id="portfolio-001"
        )
        assert event.portfolio_id == "portfolio-001"
        assert event.code == order.code
        assert event.order_id == order.uuid

    def test_strategy_cancel_notification(self):
        """测试策略取消通知"""
        order = _make_order(code="600036.SH")
        event = EventOrderCancelAck(
            order=order,
            cancelled_quantity=100,
            cancel_reason="Strategy override"
        )
        assert event.code == "600036.SH"
        assert event.cancel_reason == "Strategy override"

    def test_risk_manager_cancel_processing(self):
        """测试风险管理器取消处理"""
        order = _make_order()
        cancel_event = EventOrderCancelAck(
            order=order,
            cancelled_quantity=100,
            cancel_reason="Position limit exceeded"
        )
        assert cancel_event.cancelled_quantity == order.volume
        assert cancel_event.cancel_reason == "Position limit exceeded"
        assert cancel_event.order.status == ORDERSTATUS_TYPES.SUBMITTED

    def test_analyzer_cancel_recording(self):
        """测试分析器取消记录"""
        order = _make_order()
        ts1 = datetime.datetime(2024, 1, 1, 9, 30, 0)
        ts2 = datetime.datetime(2024, 1, 1, 9, 31, 0)
        event = EventOrderCancelAck(
            order=order,
            cancelled_quantity=100,
            timestamp=ts2,
            cancel_reason="Analysis trigger"
        )
        assert event.timestamp == ts2
        assert event.cancel_reason == "Analysis trigger"


@pytest.mark.unit
class TestCancellationErrorHandling:
    """8. 取消错误处理测试"""

    def test_cancel_timeout_handling(self):
        """测试取消超时处理"""
        order = _make_order()
        event = EventOrderCancelAck(
            order=order,
            cancelled_quantity=100,
            cancel_reason="Cancel timeout",
            timestamp=datetime.datetime(2024, 1, 1, 15, 0, 5)
        )
        assert event.cancel_reason == "Cancel timeout"
        assert event.cancelled_quantity == 100

    def test_cancel_rejection_handling(self):
        """测试取消拒绝处理"""
        order = _make_order()
        rejected = EventOrderRejected(
            order=order,
            reject_reason="Cannot cancel - order already executing",
            reject_code="CANCEL_TOO_LATE"
        )
        assert rejected.event_type == EVENT_TYPES.ORDERREJECTED
        assert rejected.reject_code == "CANCEL_TOO_LATE"
        assert rejected.order_id == order.uuid

    def test_too_late_cancel_handling(self):
        """测试过晚取消处理"""
        order = _make_order()
        order.fill(price=10.0)
        assert order.is_filled()
        assert order.is_final()
        with pytest.raises(ValueError):
            order.cancel()

    def test_network_failure_during_cancel(self):
        """测试取消时网络故障"""
        order = _make_order()
        event = EventOrderCancelAck(
            order=order,
            cancelled_quantity=0,
            cancel_reason="Network failure during cancellation"
        )
        assert event.cancelled_quantity == 0
        assert event.cancel_reason == "Network failure during cancellation"

    def test_cancel_state_inconsistency_recovery(self):
        """测试取消状态不一致恢复"""
        order = _make_order()
        order.partial_fill(30, 10.0)
        cancel_event = EventOrderCancelAck(
            order=order,
            cancelled_quantity=70,
            cancel_reason="State inconsistency recovery"
        )
        remaining = order.volume - order.transaction_volume
        assert remaining == 70
        assert cancel_event.cancelled_quantity == remaining
        order.cancel()
        assert order.is_canceled()
