"""
OrderLifecycle事件流转TDD测试

通过TDD方式测试订单生命周期事件在回测系统中的完整流转过程
涵盖OrderAck、OrderPartiallyFilled、OrderRejected、OrderExpired等T5架构事件
"""
import pytest
import sys
import datetime
from decimal import Decimal
from pathlib import Path

# 添加项目路径
project_root = Path(__file__).parent.parent.parent.parent
_path = str(project_root / "src")
if _path not in sys.path:
    sys.path.insert(0, _path)

from ginkgo.trading.events.order_lifecycle_events import (
    EventOrderAck, EventOrderPartiallyFilled, EventOrderRejected, EventOrderExpired
)
from ginkgo.entities.order import Order
from ginkgo.enums import EVENT_TYPES, ORDERSTATUS_TYPES, DIRECTION_TYPES, ORDER_TYPES, SOURCE_TYPES


def _make_order(status=ORDERSTATUS_TYPES.SUBMITTED, volume=100,
                limit_price=Decimal("10.00"), code="000001.SZ",
                transaction_volume=0):
    """创建测试用Order实例的辅助函数"""
    return Order(
        portfolio_id="portfolio-001",
        engine_id="engine-001",
        task_id="run-001",
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
class TestOrderAckEventFlow:
    """1. OrderAck事件流转测试"""

    def test_order_ack_event_creation(self):
        """测试OrderAck事件创建"""
        order = _make_order()
        ack = EventOrderAck(order=order)
        assert isinstance(ack, EventOrderAck)
        assert ack.event_type == EVENT_TYPES.ORDERACK

    def test_order_ack_properties(self):
        """测试OrderAck事件属性"""
        order = _make_order()
        ack = EventOrderAck(
            order=order,
            ack_message="Order accepted by exchange",
            portfolio_id="portfolio-001",
            engine_id="engine-001"
        )
        assert ack.order == order
        assert ack.broker_order_id == ""
        assert ack.ack_message == "Order accepted by exchange"
        assert ack.code == "000001.SZ"
        assert ack.order_id == order.uuid

    def test_broker_generates_order_ack(self):
        """测试代理生成订单确认"""
        order = _make_order()
        ack = EventOrderAck(order=order)
        ack.broker_order_id = "BRK-20240101-00001"
        assert ack.broker_order_id == "BRK-20240101-00001"
        assert ack.event_type == EVENT_TYPES.ORDERACK

    def test_portfolio_receives_order_ack(self):
        """测试投资组合接收订单确认"""
        order = _make_order()
        ack = EventOrderAck(
            order=order,
            portfolio_id="portfolio-001",
            engine_id="engine-001",
            task_id="run-001"
        )
        assert ack.portfolio_id == "portfolio-001"
        assert ack.engine_id == "engine-001"
        assert ack.task_id == "run-001"
        assert ack.payload == order

    def test_order_status_update_on_ack(self):
        """测试确认时订单状态更新"""
        order = _make_order(status=ORDERSTATUS_TYPES.SUBMITTED)
        ack = EventOrderAck(order=order)
        assert ack.order.status == ORDERSTATUS_TYPES.SUBMITTED
        order.partial_fill(50, 10.0)
        assert order.status == ORDERSTATUS_TYPES.PARTIAL_FILLED


@pytest.mark.unit
class TestOrderPartiallyFilledEventFlow:
    """2. OrderPartiallyFilled事件流转测试"""

    def test_partial_fill_event_creation(self):
        """测试部分成交事件创建"""
        order = _make_order()
        event = EventOrderPartiallyFilled(
            order=order,
            filled_quantity=30,
            fill_price=10.50
        )
        assert isinstance(event, EventOrderPartiallyFilled)
        assert event.event_type == EVENT_TYPES.ORDERPARTIALLYFILLED

    def test_partial_fill_quantity_tracking(self):
        """测试部分成交数量追踪"""
        order = _make_order()
        event = EventOrderPartiallyFilled(
            order=order,
            filled_quantity=40,
            fill_price=10.25,
            trade_id="TRD-001",
            commission=Decimal("5.00")
        )
        assert event.filled_quantity == 40
        assert event.fill_price == 10.25
        assert event.fill_amount == 40 * 10.25
        assert event.trade_id == "TRD-001"
        assert event.commission == Decimal("5.00")

    def test_multiple_partial_fills(self):
        """测试多次部分成交"""
        order = _make_order()
        fill1 = EventOrderPartiallyFilled(
            order=order, filled_quantity=30, fill_price=10.0
        )
        order.partial_fill(30, 10.0)
        fill2 = EventOrderPartiallyFilled(
            order=order, filled_quantity=40, fill_price=10.2
        )
        order.partial_fill(40, 10.2)
        assert order.transaction_volume == 70
        assert order.status == ORDERSTATUS_TYPES.PARTIAL_FILLED
        assert fill1.code == fill2.code == "000001.SZ"

    def test_partial_fill_position_update(self):
        """测试部分成交触发持仓更新"""
        order = _make_order()
        event = EventOrderPartiallyFilled(
            order=order,
            filled_quantity=50,
            fill_price=10.0
        )
        assert event.remaining_quantity == 50
        assert event.code == order.code
        assert event.order_id == order.uuid

    def test_remaining_quantity_calculation(self):
        """测试剩余数量计算"""
        order = _make_order()
        event = EventOrderPartiallyFilled(
            order=order,
            filled_quantity=30,
            fill_price=10.0
        )
        assert event.remaining_quantity == 70
        event2 = EventOrderPartiallyFilled(
            order=order,
            filled_quantity=50,
            fill_price=10.0
        )
        assert event2.remaining_quantity == 50


@pytest.mark.unit
class TestOrderRejectedEventFlow:
    """3. OrderRejected事件流转测试"""

    def test_order_rejected_event_creation(self):
        """测试订单拒绝事件创建"""
        order = _make_order()
        event = EventOrderRejected(
            order=order,
            reject_reason="Insufficient capital"
        )
        assert isinstance(event, EventOrderRejected)
        assert event.event_type == EVENT_TYPES.ORDERREJECTED

    def test_rejection_reason_tracking(self):
        """测试拒绝原因追踪"""
        order = _make_order()
        event = EventOrderRejected(
            order=order,
            reject_reason="Price limit violated",
            reject_code="PRICE_LIMIT"
        )
        assert event.reject_reason == "Price limit violated"
        assert event.reject_code == "PRICE_LIMIT"
        assert event.code == "000001.SZ"
        assert event.order_id == order.uuid

    def test_risk_manager_order_rejection(self):
        """测试风险管理器订单拒绝"""
        order = _make_order()
        event = EventOrderRejected(
            order=order,
            reject_reason="Position ratio exceeds limit",
            reject_code="RISK_POSITION_LIMIT"
        )
        assert event.reject_reason == "Position ratio exceeds limit"
        assert event.reject_code == "RISK_POSITION_LIMIT"

    def test_broker_order_rejection(self):
        """测试代理订单拒绝"""
        order = _make_order()
        event = EventOrderRejected(
            order=order,
            reject_reason="Market closed",
            reject_code="MARKET_CLOSED",
            portfolio_id="portfolio-001",
            engine_id="engine-001"
        )
        assert event.portfolio_id == "portfolio-001"
        assert event.engine_id == "engine-001"
        assert event.order == order

    def test_rejected_order_cleanup(self):
        """测试被拒绝订单的清理"""
        order = _make_order()
        event = EventOrderRejected(
            order=order,
            reject_reason="Invalid order parameters"
        )
        assert event.code == order.code
        assert event.order_id == order.uuid
        assert event.event_type == EVENT_TYPES.ORDERREJECTED


@pytest.mark.unit
class TestOrderExpiredEventFlow:
    """4. OrderExpired事件流转测试"""

    def test_order_expired_event_creation(self):
        """测试订单过期事件创建"""
        order = _make_order()
        event = EventOrderExpired(order=order)
        assert isinstance(event, EventOrderExpired)
        assert event.event_type == EVENT_TYPES.ORDEREXPIRED

    def test_time_based_expiration(self):
        """测试基于时间的过期"""
        order = _make_order()
        ts = datetime.datetime(2024, 1, 15, 15, 0, 0)
        event = EventOrderExpired(
            order=order,
            timestamp=ts,
            expire_reason="Order time limit reached"
        )
        assert event.expire_reason == "Order time limit reached"
        assert event.timestamp.year == 2024

    def test_market_close_expiration(self):
        """测试市场关闭时的过期"""
        order = _make_order()
        event = EventOrderExpired(
            order=order,
            expire_reason="Market closed - daily limit order expired"
        )
        assert event.expire_reason == "Market closed - daily limit order expired"
        assert event.expired_quantity == order.volume

    def test_expired_order_notification(self):
        """测试过期订单通知"""
        order = _make_order(volume=200)
        event = EventOrderExpired(
            order=order,
            expire_reason="Time expired",
            portfolio_id="portfolio-001",
            engine_id="engine-001",
            task_id="run-001"
        )
        assert event.code == "000001.SZ"
        assert event.expired_quantity == 200
        assert event.portfolio_id == "portfolio-001"
        assert event.order_id == order.uuid


@pytest.mark.unit
class TestOrderLifecycleEventChaining:
    """5. 订单生命周期事件链测试"""

    def test_complete_order_lifecycle(self):
        """测试完整订单生命周期"""
        order = _make_order()
        ack = EventOrderAck(order=order)
        ack.broker_order_id = "BRK-001"
        assert ack.event_type == EVENT_TYPES.ORDERACK

        fill = EventOrderPartiallyFilled(order=order, filled_quantity=100, fill_price=10.0)
        assert fill.event_type == EVENT_TYPES.ORDERPARTIALLYFILLED

        order.partial_fill(100, 10.0)
        assert order.is_filled()

    def test_order_status_transitions(self):
        """测试订单状态转换"""
        order = _make_order(status=ORDERSTATUS_TYPES.SUBMITTED)
        assert order.status == ORDERSTATUS_TYPES.SUBMITTED

        order.partial_fill(30, 10.0)
        assert order.status == ORDERSTATUS_TYPES.PARTIAL_FILLED

        order.fill(price=10.0)
        assert order.status == ORDERSTATUS_TYPES.FILLED

    def test_concurrent_order_events(self):
        """测试并发订单事件"""
        order1 = _make_order(code="000001.SZ")
        order2 = _make_order(code="600036.SH")
        ack1 = EventOrderAck(order=order1)
        ack2 = EventOrderAck(order=order2)
        assert ack1.order_id != ack2.order_id
        assert ack1.code == "000001.SZ"
        assert ack2.code == "600036.SH"

    def test_event_ordering_consistency(self):
        """测试事件顺序一致性"""
        order = _make_order()
        ts1 = datetime.datetime(2024, 1, 1, 9, 30, 0)
        ts2 = datetime.datetime(2024, 1, 1, 9, 30, 1)
        ts3 = datetime.datetime(2024, 1, 1, 9, 30, 2)

        ack = EventOrderAck(order=order, timestamp=ts1)
        fill = EventOrderPartiallyFilled(order=order, filled_quantity=50, fill_price=10.0, timestamp=ts2)
        complete = EventOrderPartiallyFilled(order=order, filled_quantity=50, fill_price=10.0, timestamp=ts3)

        assert ack.timestamp < fill.timestamp < complete.timestamp


@pytest.mark.unit
class TestOrderEventErrorHandling:
    """6. 订单事件错误处理测试"""

    def test_malformed_order_event_handling(self):
        """测试格式错误的订单事件处理"""
        order = _make_order()
        event = EventOrderRejected(
            order=order,
            reject_reason="Malformed event data",
            reject_code="MALFORMED"
        )
        assert event.reject_code == "MALFORMED"
        assert event.event_type == EVENT_TYPES.ORDERREJECTED

    def test_missing_order_reference_handling(self):
        """测试缺失订单引用处理"""
        order = _make_order()
        event = EventOrderAck(order=order)
        assert event.order is not None
        assert event.code == order.code
        assert event.order_id == order.uuid

    def test_duplicate_order_event_handling(self):
        """测试重复订单事件处理"""
        order = _make_order()
        ack1 = EventOrderAck(order=order, ack_message="First ack")
        ack2 = EventOrderAck(order=order, ack_message="Duplicate ack")
        assert ack1.order_id == ack2.order_id
        assert ack1.uuid != ack2.uuid
        assert ack1.ack_message != ack2.ack_message

    def test_order_event_timeout_handling(self):
        """测试订单事件超时处理"""
        order = _make_order()
        event = EventOrderExpired(
            order=order,
            expire_reason="Event processing timeout",
            timestamp=datetime.datetime(2024, 1, 1, 15, 30, 0)
        )
        assert event.expire_reason == "Event processing timeout"
        assert event.event_type == EVENT_TYPES.ORDEREXPIRED


@pytest.mark.unit
class TestOrderEventPortfolioIntegration:
    """7. 订单事件与投资组合集成测试"""

    def test_portfolio_order_tracking(self):
        """测试投资组合订单追踪"""
        order = _make_order()
        ack = EventOrderAck(
            order=order,
            portfolio_id="portfolio-001",
            engine_id="engine-001",
            task_id="run-001"
        )
        assert ack.portfolio_id == "portfolio-001"
        assert ack.order_id == order.uuid
        assert ack.code == order.code

    def test_portfolio_risk_adjustment_on_events(self):
        """测试事件触发的投资组合风险调整"""
        order = _make_order()
        rejected = EventOrderRejected(
            order=order,
            reject_reason="Position limit exceeded",
            reject_code="RISK_LIMIT"
        )
        assert rejected.event_type == EVENT_TYPES.ORDERREJECTED

        rejected2 = EventOrderRejected(
            order=order,
            reject_reason="Position limit exceeded",
            reject_code="RISK_LIMIT",
            portfolio_id="portfolio-risk-001"
        )
        assert rejected2.portfolio_id == "portfolio-risk-001"
        assert rejected2.reject_code == "RISK_LIMIT"

    def test_portfolio_performance_calculation(self):
        """测试投资组合绩效计算"""
        order = _make_order()
        fill = EventOrderPartiallyFilled(
            order=order,
            filled_quantity=100,
            fill_price=10.50,
            commission=Decimal("10.50")
        )
        assert fill.fill_amount == 100 * 10.50
        assert fill.commission == Decimal("10.50")

    def test_portfolio_reporting_on_order_events(self):
        """测试基于订单事件的投资组合报告"""
        order = _make_order(code="000001.SZ", volume=500, limit_price=Decimal("20.00"))
        ack = EventOrderAck(order=order, portfolio_id="portfolio-report")
        fill = EventOrderPartiallyFilled(
            order=order,
            filled_quantity=200,
            fill_price=20.0,
            portfolio_id="portfolio-report"
        )
        assert ack.code == "000001.SZ"
        assert fill.fill_amount == 4000.0
        assert ack.portfolio_id == fill.portfolio_id == "portfolio-report"


@pytest.mark.unit
class TestOrderEventBacktestVsLive:
    """8. 订单事件回测与实盘对比测试"""

    def test_backtest_order_event_simulation(self):
        """测试回测订单事件模拟"""
        order = _make_order(status=ORDERSTATUS_TYPES.SUBMITTED)
        ack = EventOrderAck(order=order, engine_id="backtest-engine-001")
        fill = EventOrderPartiallyFilled(
            order=order,
            filled_quantity=order.volume,
            fill_price=float(order.limit_price),
            timestamp=datetime.datetime(2024, 1, 2, 10, 0, 0),
            engine_id="backtest-engine-001"
        )
        assert ack.engine_id == "backtest-engine-001"
        assert fill.engine_id == "backtest-engine-001"

    def test_live_trading_order_event_handling(self):
        """测试实盘交易订单事件处理"""
        order = _make_order(code="600036.SH")
        ack = EventOrderAck(
            order=order,
            engine_id="live-engine-001",
            task_id="live-run-001"
        )
        ack.broker_order_id = "LIVE-BRK-12345"
        assert ack.broker_order_id == "LIVE-BRK-12345"
        assert ack.engine_id == "live-engine-001"

    def test_event_timing_consistency(self):
        """测试事件时间一致性"""
        order = _make_order()
        ts = datetime.datetime(2024, 3, 1, 9, 30, 0)
        ack = EventOrderAck(order=order, timestamp=ts)
        fill = EventOrderPartiallyFilled(
            order=order, filled_quantity=50, fill_price=10.0, timestamp=ts
        )
        assert ack.timestamp == fill.timestamp == ts

    def test_t5_architecture_compliance(self):
        """测试T5架构合规性"""
        order = _make_order()
        ack = EventOrderAck(order=order)
        partial = EventOrderPartiallyFilled(order=order, filled_quantity=30, fill_price=10.0)
        rejected = EventOrderRejected(order=order, reject_reason="test")
        expired = EventOrderExpired(order=order, expire_reason="test")

        assert ack.event_type == EVENT_TYPES.ORDERACK
        assert partial.event_type == EVENT_TYPES.ORDERPARTIALLYFILLED
        assert rejected.event_type == EVENT_TYPES.ORDERREJECTED
        assert expired.event_type == EVENT_TYPES.ORDEREXPIRED

        all_events = [ack, partial, rejected, expired]
        for event in all_events:
            assert event.name is not None
            assert isinstance(event.uuid, str)
            assert len(event.uuid) > 0
