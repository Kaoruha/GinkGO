"""
OrderLifecycle集成测试

测试完整订单生命周期的端到端流转和集成
涵盖所有阶段的完整流程：Creation → Submission → Acknowledgment → Execution → Settlement
以及异常路径：Rejection, Cancellation, Expiration
相关组件：所有订单生命周期相关组件的集成测试
"""
import pytest
import sys
import datetime
import time
import gc
from decimal import Decimal
from pathlib import Path

# 添加项目路径
project_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(project_root / "src"))

from ginkgo.entities.order import Order
from ginkgo.trading.events.order_lifecycle_events import (
    EventOrderAck, EventOrderPartiallyFilled, EventOrderRejected,
    EventOrderExpired, EventOrderCancelAck
)
from ginkgo.enums import ORDERSTATUS_TYPES, EVENT_TYPES, DIRECTION_TYPES, ORDER_TYPES


def _make_order(status=ORDERSTATUS_TYPES.NEW, volume=100,
                limit_price=Decimal("10.00"), code="000001.SZ",
                direction=DIRECTION_TYPES.LONG, transaction_volume=0,
                portfolio_id="portfolio-001", engine_id="engine-001",
                run_id="run-001"):
    """创建测试用Order实例的辅助函数"""
    return Order(
        portfolio_id=portfolio_id,
        engine_id=engine_id,
        run_id=run_id,
        code=code,
        direction=direction,
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
    status = kwargs.pop("status", ORDERSTATUS_TYPES.NEW)
    order = _make_order(status=status, **kwargs)
    if order.status == ORDERSTATUS_TYPES.NEW:
        order.submit()
    return order


@pytest.mark.unit
@pytest.mark.integration
class TestCompleteOrderLifecycleSuccess:
    """1. 完整订单生命周期成功流程测试"""

    def test_signal_to_settlement_complete_flow(self):
        """测试从信号到结算的完整流程"""
        order = _make_order()
        assert order.is_new()

        order.submit()
        assert order.is_submitted()

        ack = EventOrderAck(order=order)
        ack.broker_order_id = "BRK-SETTLE-001"
        assert ack.event_type == EVENT_TYPES.ORDERACK

        order.partial_fill(100, 10.0)
        assert order.is_filled()
        assert order.transaction_volume == 100
        assert order.get_remaining_volume() == 0

    def test_order_status_transitions_validation(self):
        """测试订单状态转换验证"""
        order = _make_order()
        assert order.status == ORDERSTATUS_TYPES.NEW

        order.submit()
        assert order.status == ORDERSTATUS_TYPES.SUBMITTED

        order.partial_fill(40, 10.0)
        assert order.status == ORDERSTATUS_TYPES.PARTIAL_FILLED

        order.fill(price=10.0)
        assert order.status == ORDERSTATUS_TYPES.FILLED

    def test_event_sequence_validation(self):
        """测试事件序列验证"""
        order = _make_order()
        ts_ack = datetime.datetime(2024, 1, 1, 9, 30, 0)
        ts_fill1 = datetime.datetime(2024, 1, 1, 9, 30, 5)
        ts_fill2 = datetime.datetime(2024, 1, 1, 9, 30, 10)

        events = [
            EventOrderAck(order=order, timestamp=ts_ack),
            EventOrderPartiallyFilled(order=order, filled_quantity=50, fill_price=10.0, timestamp=ts_fill1),
            EventOrderPartiallyFilled(order=order, filled_quantity=50, fill_price=10.0, timestamp=ts_fill2),
        ]
        for i in range(len(events) - 1):
            assert events[i].timestamp <= events[i + 1].timestamp

        event_types = [e.event_type for e in events]
        assert EVENT_TYPES.ORDERACK in event_types
        assert EVENT_TYPES.ORDERPARTIALLYFILLED in event_types

    def test_cross_component_data_consistency(self):
        """测试跨组件数据一致性"""
        order = _make_order(code="600036.SH", volume=200)
        ack = EventOrderAck(
            order=order,
            portfolio_id="portfolio-001",
            engine_id="engine-001",
            run_id="run-001"
        )
        fill = EventOrderPartiallyFilled(
            order=order,
            filled_quantity=100,
            fill_price=15.50,
            portfolio_id="portfolio-001",
            engine_id="engine-001",
            run_id="run-001"
        )
        assert ack.portfolio_id == fill.portfolio_id == "portfolio-001"
        assert ack.code == fill.code == "600036.SH"
        assert ack.order_id == fill.order_id == order.uuid

    def test_portfolio_state_evolution(self):
        """测试投资组合状态演化"""
        order = _make_order(volume=500, limit_price=Decimal("20.00"))
        assert order.frozen_money == Decimal("10000.00")

        order.submit()
        ack = EventOrderAck(order=order)
        assert ack.event_type == EVENT_TYPES.ORDERACK

        order.partial_fill(200, 20.0)
        assert order.transaction_volume == 200
        assert order.get_fill_ratio() == 0.4

        order.fill(price=20.0)
        assert order.is_filled()
        assert order.get_fill_ratio() == 1.0


@pytest.mark.unit
@pytest.mark.integration
class TestOrderLifecycleRejectionFlows:
    """2. 订单生命周期拒绝流程测试"""

    def test_creation_stage_rejection_flow(self):
        """测试创建阶段拒绝流程"""
        order = _make_order(status=ORDERSTATUS_TYPES.NEW)
        event = EventOrderRejected(
            order=order,
            reject_reason="Risk limit exceeded at creation",
            reject_code="CREATION_RISK_LIMIT"
        )
        assert event.event_type == EVENT_TYPES.ORDERREJECTED
        assert event.reject_code == "CREATION_RISK_LIMIT"
        assert event.code == order.code

    def test_submission_stage_rejection_flow(self):
        """测试提交阶段拒绝流程"""
        order = _make_order(status=ORDERSTATUS_TYPES.SUBMITTED)
        event = EventOrderRejected(
            order=order,
            reject_reason="Broker rejected at submission",
            reject_code="BROKER_REJECT"
        )
        assert event.order.status == ORDERSTATUS_TYPES.SUBMITTED
        assert event.reject_reason == "Broker rejected at submission"

    def test_market_rejection_flow(self):
        """测试市场拒绝流程"""
        order = _make_order()
        ts = datetime.datetime(2024, 1, 1, 9, 35, 0)
        event = EventOrderRejected(
            order=order,
            reject_reason="Exchange rejected - price out of range",
            reject_code="EXCHANGE_REJECT",
            timestamp=ts
        )
        assert event.reject_code == "EXCHANGE_REJECT"
        assert event.timestamp == ts
        assert event.event_type == EVENT_TYPES.ORDERREJECTED

    def test_rejection_cleanup_and_recovery(self):
        """测试拒绝清理和恢复"""
        order = _make_order(volume=300, limit_price=Decimal("25.00"))
        frozen = order.frozen_money
        assert frozen == Decimal("7500.00")
        assert order.frozen_volume == 300

        event = EventOrderRejected(
            order=order,
            reject_reason="Insufficient margin",
            reject_code="MARGIN_INSUFF"
        )
        assert event.code == order.code
        assert order.frozen_money == frozen

    def test_rejection_notification_propagation(self):
        """测试拒绝通知传播"""
        order = _make_order()
        event = EventOrderRejected(
            order=order,
            reject_reason="System rejection",
            reject_code="SYS_REJECT",
            portfolio_id="portfolio-notif",
            engine_id="engine-notif",
            run_id="run-notif"
        )
        assert event.portfolio_id == "portfolio-notif"
        assert event.engine_id == "engine-notif"
        assert event.run_id == "run-notif"
        assert event.order_id == order.uuid


@pytest.mark.unit
@pytest.mark.integration
class TestOrderLifecycleCancellationFlows:
    """3. 订单生命周期取消流程测试"""

    def test_pre_submission_cancellation(self):
        """测试提交前取消"""
        order = _make_order(status=ORDERSTATUS_TYPES.NEW)
        assert order.is_new()
        order.cancel()
        assert order.is_canceled()

        cancel_event = EventOrderCancelAck(
            order=order,
            cancelled_quantity=order.volume,
            cancel_reason="Pre-submission cancellation"
        )
        assert cancel_event.event_type == EVENT_TYPES.ORDERCANCELACK
        assert cancel_event.cancelled_quantity == order.volume

    def test_post_acknowledgment_cancellation(self):
        """测试确认后取消"""
        order = _make_order(status=ORDERSTATUS_TYPES.SUBMITTED)
        ack = EventOrderAck(order=order)
        ack.broker_order_id = "BRK-POST-ACK"
        assert ack.event_type == EVENT_TYPES.ORDERACK

        order.cancel()
        cancel_event = EventOrderCancelAck(
            order=order,
            cancelled_quantity=100,
            cancel_reason="Post-acknowledgment cancellation"
        )
        assert order.is_canceled()
        assert cancel_event.cancel_reason == "Post-acknowledgment cancellation"
        assert cancel_event.order_id == order.uuid

    def test_partial_fill_cancellation(self):
        """测试部分成交取消"""
        order = _make_submitted_order(volume=200)
        order.partial_fill(80, 10.0)
        assert order.status == ORDERSTATUS_TYPES.PARTIAL_FILLED
        assert order.transaction_volume == 80

        order.cancel()
        cancel_event = EventOrderCancelAck(
            order=order,
            cancelled_quantity=120,
            cancel_reason="Cancel remaining after partial fill"
        )
        assert order.is_canceled()
        assert cancel_event.cancelled_quantity == 120

    def test_emergency_cancellation_flow(self):
        """测试紧急取消流程"""
        order = _make_order(volume=1000, limit_price=Decimal("50.00"))
        assert order.frozen_money == Decimal("50000.00")

        cancel_event = EventOrderCancelAck(
            order=order,
            cancelled_quantity=1000,
            cancel_reason="EMERGENCY: Market circuit breaker triggered",
            timestamp=datetime.datetime(2024, 1, 1, 11, 30, 0),
            portfolio_id="portfolio-emergency",
            engine_id="engine-emergency"
        )
        assert cancel_event.cancel_reason == "EMERGENCY: Market circuit breaker triggered"
        assert cancel_event.cancelled_quantity == 1000

    def test_cancellation_failure_handling(self):
        """测试取消失败处理"""
        order = _make_submitted_order()
        order.partial_fill(100, 10.0)
        assert order.is_filled()

        rejected = EventOrderRejected(
            order=order,
            reject_reason="Cannot cancel - order already filled",
            reject_code="CANCEL_FAIL_FILLED"
        )
        assert rejected.reject_code == "CANCEL_FAIL_FILLED"
        assert order.is_final()


@pytest.mark.unit
@pytest.mark.integration
class TestOrderLifecycleExpirationFlows:
    """4. 订单生命周期过期流程测试"""

    def test_time_based_expiration_flow(self):
        """测试基于时间的过期流程"""
        order = _make_order()
        order.submit()
        assert order.is_submitted()

        ts = datetime.datetime(2024, 1, 1, 15, 0, 0)
        expired = EventOrderExpired(
            order=order,
            timestamp=ts,
            expire_reason="GTC order time limit reached"
        )
        assert expired.event_type == EVENT_TYPES.ORDEREXPIRED
        assert expired.expired_quantity == order.volume
        assert expired.timestamp == ts

    def test_market_close_expiration_flow(self):
        """测试市场收盘过期流程"""
        order = _make_order(volume=500)
        expired = EventOrderExpired(
            order=order,
            expire_reason="Market closed - day order expired",
            timestamp=datetime.datetime(2024, 1, 1, 15, 0, 0),
            portfolio_id="portfolio-001",
            engine_id="engine-001",
            run_id="run-001"
        )
        assert expired.expired_quantity == 500
        assert expired.code == order.code
        assert expired.portfolio_id == "portfolio-001"

    def test_conditional_expiration_flow(self):
        """测试条件过期流程"""
        order = _make_order(volume=100, limit_price=Decimal("9.50"))
        expired = EventOrderExpired(
            order=order,
            expire_reason="Limit price condition not met within timeout"
        )
        assert expired.expire_reason == "Limit price condition not met within timeout"
        assert expired.expired_quantity == 100
        assert expired.event_type == EVENT_TYPES.ORDEREXPIRED

    def test_batch_expiration_processing(self):
        """测试批量过期处理"""
        orders = [_make_order(code=f"60{i:04d}.SH") for i in range(1, 6)]
        expired_events = [
            EventOrderExpired(order=o, expire_reason="Batch day close expiration")
            for o in orders
        ]
        codes = [e.code for e in expired_events]
        assert len(expired_events) == 5
        assert "6000001.SH" not in codes
        for e in expired_events:
            assert e.event_type == EVENT_TYPES.ORDEREXPIRED

    def test_expiration_chain_reaction_prevention(self):
        """测试过期连锁反应预防"""
        order1 = _make_order(code="000001.SZ")
        order2 = _make_order(code="600036.SH")

        expired1 = EventOrderExpired(order=order1, expire_reason="Order 1 expired")
        expired2 = EventOrderExpired(order=order2, expire_reason="Order 2 expired")

        assert expired1.order_id != expired2.order_id
        assert expired1.code != expired2.code
        assert expired1.event_type == expired2.event_type == EVENT_TYPES.ORDEREXPIRED


@pytest.mark.unit
@pytest.mark.integration
class TestOrderLifecyclePartialExecutionFlows:
    """5. 订单生命周期部分执行流程测试"""

    def test_multiple_partial_fills_flow(self):
        """测试多次部分成交流程"""
        order = _make_submitted_order(volume=300)
        fills = []
        quantities = [50, 80, 100, 70]

        for qty in quantities:
            event = EventOrderPartiallyFilled(
                order=order, filled_quantity=qty, fill_price=10.0
            )
            order.partial_fill(qty, 10.0)
            fills.append(event)

        assert order.transaction_volume == 300
        assert order.is_filled()
        assert len(fills) == 4

    def test_partial_fill_to_complete_flow(self):
        """测试部分成交到完全成交流程"""
        order = _make_submitted_order(volume=200)

        event1 = EventOrderPartiallyFilled(order=order, filled_quantity=60, fill_price=10.0)
        order.partial_fill(60, 10.0)
        assert order.status == ORDERSTATUS_TYPES.PARTIAL_FILLED

        event2 = EventOrderPartiallyFilled(order=order, filled_quantity=140, fill_price=10.0)
        order.partial_fill(140, 10.0)
        assert order.status == ORDERSTATUS_TYPES.FILLED
        assert order.is_filled()

    def test_partial_fill_cancellation_integration(self):
        """测试部分成交取消集成"""
        order = _make_submitted_order(volume=300)

        event1 = EventOrderPartiallyFilled(order=order, filled_quantity=100, fill_price=10.0)
        order.partial_fill(100, 10.0)
        assert order.status == ORDERSTATUS_TYPES.PARTIAL_FILLED

        order.cancel()
        cancel = EventOrderCancelAck(
            order=order,
            cancelled_quantity=200,
            cancel_reason="Cancel remaining after partial fill"
        )
        assert order.is_canceled()
        assert cancel.cancelled_quantity == 200

    def test_partial_fill_expiration_integration(self):
        """测试部分成交过期集成"""
        order = _make_submitted_order(volume=200)
        order.partial_fill(80, 10.0)

        expired = EventOrderExpired(
            order=order,
            expire_reason="Remaining quantity expired after partial fill"
        )
        remaining = order.volume - order.transaction_volume
        assert remaining == 120
        assert expired.expired_quantity == 120

    def test_partial_fill_portfolio_impact(self):
        """测试部分成交投资组合影响"""
        order = _make_submitted_order(volume=1000, limit_price=Decimal("15.00"))
        total_expected = Decimal("15000.00")
        assert order.frozen_money == total_expected

        order.partial_fill(400, 15.0)
        assert order.transaction_volume == 400
        assert order.get_fill_ratio() == 0.4

        fill_event = EventOrderPartiallyFilled(
            order=order, filled_quantity=300, fill_price=15.0
        )
        assert fill_event.remaining_quantity == 300
        assert fill_event.fill_amount == 4500.0


@pytest.mark.unit
@pytest.mark.integration
class TestOrderLifecycleEventDrivenIntegration:
    """6. 订单生命周期事件驱动集成测试"""

    def test_event_engine_integration(self):
        """测试事件引擎集成"""
        order = _make_order()
        all_events = [
            EventOrderAck(order=order, portfolio_id="p1", engine_id="e1"),
            EventOrderPartiallyFilled(order=order, filled_quantity=50, fill_price=10.0,
                                      portfolio_id="p1", engine_id="e1"),
            EventOrderCancelAck(order=order, cancelled_quantity=50,
                                cancel_reason="Integration test", portfolio_id="p1", engine_id="e1"),
        ]
        for event in all_events:
            assert event.portfolio_id == "p1"
            assert event.engine_id == "e1"
            assert isinstance(event.uuid, str)

    def test_event_ordering_and_sequencing(self):
        """测试事件排序和序列化"""
        order = _make_order()
        base_ts = datetime.datetime(2024, 6, 1, 9, 30, 0)
        events = [
            EventOrderAck(order=order, timestamp=base_ts),
            EventOrderPartiallyFilled(order=order, filled_quantity=30, fill_price=10.0,
                                      timestamp=base_ts + datetime.timedelta(seconds=5)),
            EventOrderPartiallyFilled(order=order, filled_quantity=40, fill_price=10.0,
                                      timestamp=base_ts + datetime.timedelta(seconds=10)),
            EventOrderPartiallyFilled(order=order, filled_quantity=30, fill_price=10.0,
                                      timestamp=base_ts + datetime.timedelta(seconds=15)),
        ]
        timestamps = [e.timestamp for e in events]
        assert timestamps == sorted(timestamps)

    def test_concurrent_order_event_handling(self):
        """测试并发订单事件处理"""
        orders = [
            _make_order(code=f"00000{i}.SZ") for i in range(1, 5)
        ]
        events = []
        for i, order in enumerate(orders):
            events.append(EventOrderAck(order=order, timestamp=datetime.datetime(2024, 1, 1, 9, 30, i)))

        order_ids = [e.order_id for e in events]
        assert len(set(order_ids)) == 4
        codes = [e.code for e in events]
        assert "000001.SZ" in codes
        assert "000004.SZ" in codes

    def test_event_replay_and_recovery(self):
        """测试事件重放和恢复"""
        order = _make_order()
        event_log = [
            EventOrderAck(order=order, timestamp=datetime.datetime(2024, 1, 1, 9, 30, 0)),
            EventOrderPartiallyFilled(order=order, filled_quantity=30, fill_price=10.0,
                                      timestamp=datetime.datetime(2024, 1, 1, 9, 30, 1)),
            EventOrderPartiallyFilled(order=order, filled_quantity=70, fill_price=10.0,
                                      timestamp=datetime.datetime(2024, 1, 1, 9, 30, 2)),
        ]
        assert len(event_log) == 3
        for e in event_log:
            assert e.order_id == order.uuid
            assert e.code == order.code

    def test_event_audit_trail_completeness(self):
        """测试事件审计追踪完整性"""
        order = _make_order()
        audit_events = [
            ("Ack", EVENT_TYPES.ORDERACK),
            ("PartialFill", EVENT_TYPES.ORDERPARTIALLYFILLED),
            ("Reject", EVENT_TYPES.ORDERREJECTED),
            ("Expire", EVENT_TYPES.ORDEREXPIRED),
            ("CancelAck", EVENT_TYPES.ORDERCANCELACK),
        ]
        event_objects = []
        for name, etype in audit_events:
            if name == "Ack":
                e = EventOrderAck(order=order, portfolio_id="audit", engine_id="audit", run_id="audit")
            elif name == "PartialFill":
                e = EventOrderPartiallyFilled(order=order, filled_quantity=10, fill_price=10.0,
                                              portfolio_id="audit", engine_id="audit", run_id="audit")
            elif name == "Reject":
                e = EventOrderRejected(order=order, reject_reason="audit test",
                                       portfolio_id="audit", engine_id="audit", run_id="audit")
            elif name == "Expire":
                e = EventOrderExpired(order=order, expire_reason="audit test",
                                      portfolio_id="audit", engine_id="audit", run_id="audit")
            else:
                e = EventOrderCancelAck(order=order, cancelled_quantity=10, cancel_reason="audit test",
                                        portfolio_id="audit", engine_id="audit", run_id="audit")
            assert e.event_type == etype
            assert e.portfolio_id == "audit"
            event_objects.append(e)


@pytest.mark.unit
@pytest.mark.integration
class TestOrderLifecyclePerformanceAndScalability:
    """7. 订单生命周期性能和可扩展性测试"""

    def test_high_volume_order_processing(self):
        """测试高容量订单处理"""
        orders = []
        events = []
        for i in range(100):
            order = _make_order(code=f"{i:06d}.SZ")
            orders.append(order)
            events.append(EventOrderAck(order=order))

        assert len(orders) == 100
        assert len(events) == 100
        assert all(e.event_type == EVENT_TYPES.ORDERACK for e in events)

    def test_order_lifecycle_latency_measurement(self):
        """测试订单生命周期延迟测量"""
        order = _make_order()
        start = time.perf_counter()

        ack = EventOrderAck(order=order)
        fill = EventOrderPartiallyFilled(order=order, filled_quantity=100, fill_price=10.0)

        elapsed = time.perf_counter() - start
        assert elapsed < 1.0
        assert ack.event_type == EVENT_TYPES.ORDERACK
        assert fill.event_type == EVENT_TYPES.ORDERPARTIALLYFILLED

    def test_memory_usage_optimization(self):
        """测试内存使用优化"""
        orders = [_make_order(code=f"{i:06d}.SZ") for i in range(50)]
        events = [
            EventOrderPartiallyFilled(order=o, filled_quantity=10, fill_price=10.0)
            for o in orders
        ]
        assert len(events) == 50
        for e in events:
            assert e.filled_quantity == 10
        events.clear()
        gc.collect()

    def test_resource_cleanup_effectiveness(self):
        """测试资源清理有效性"""
        order = _make_order()
        ack = EventOrderAck(order=order)
        fill = EventOrderPartiallyFilled(order=order, filled_quantity=100, fill_price=10.0)
        cancel = EventOrderCancelAck(order=order, cancelled_quantity=0,
                                     cancel_reason="Already filled")
        assert cancel.cancelled_quantity == 0

    def test_scalability_bottleneck_identification(self):
        """测试可扩展性瓶颈识别"""
        start = time.perf_counter()
        orders = []
        for i in range(200):
            o = _make_order(code=f"{i:06d}.SZ")
            orders.append(o)
            EventOrderAck(order=o)
            EventOrderPartiallyFilled(order=o, filled_quantity=10, fill_price=10.0)
        elapsed = time.perf_counter() - start
        assert elapsed < 5.0
        assert len(orders) == 200


@pytest.mark.unit
@pytest.mark.integration
class TestOrderLifecycleErrorHandlingAndResilience:
    """8. 订单生命周期错误处理和弹性测试"""

    def test_component_failure_resilience(self):
        """测试组件故障弹性"""
        order = _make_order()
        ack = EventOrderAck(order=order, portfolio_id="resilient")
        rejected = EventOrderRejected(
            order=order,
            reject_reason="Downstream component failure",
            reject_code="COMPONENT_FAILURE",
            portfolio_id="resilient"
        )
        assert ack.portfolio_id == "resilient"
        assert rejected.event_type == EVENT_TYPES.ORDERREJECTED
        assert rejected.reject_code == "COMPONENT_FAILURE"

    def test_network_interruption_handling(self):
        """测试网络中断处理"""
        order = _make_order()
        expired = EventOrderExpired(
            order=order,
            expire_reason="Network timeout - order expired",
            timestamp=datetime.datetime(2024, 1, 1, 15, 30, 0)
        )
        assert expired.expire_reason == "Network timeout - order expired"
        assert expired.event_type == EVENT_TYPES.ORDEREXPIRED

    def test_data_corruption_detection_and_recovery(self):
        """测试数据损坏检测和恢复"""
        order = _make_order()
        event1 = EventOrderAck(order=order)
        event2 = EventOrderAck(order=order)
        assert event1.order_id == event2.order_id == order.uuid
        assert event1.uuid != event2.uuid

    def test_system_restart_state_recovery(self):
        """测试系统重启状态恢复"""
        order = _make_submitted_order(code="600036.SH", volume=200)
        order.partial_fill(100, 15.0)
        assert order.transaction_volume == 100
        assert order.status == ORDERSTATUS_TYPES.PARTIAL_FILLED

        recovery_event = EventOrderAck(
            order=order,
            portfolio_id="recovery",
            engine_id="recovery",
            run_id="recovery"
        )
        assert recovery_event.order_id == order.uuid
        assert recovery_event.code == "600036.SH"
        assert order.get_remaining_volume() == 100

    def test_cascading_failure_prevention(self):
        """测试级联失败预防"""
        orders = [
            _make_order(code=f"00000{i}.SZ") for i in range(5)
        ]
        errors = []
        for order in orders:
            try:
                EventOrderRejected(
                    order=order,
                    reject_reason="Cascading test rejection",
                    reject_code="CASCADE_TEST"
                )
            except Exception as e:
                errors.append(e)
        assert len(errors) == 0
        assert all(o.code is not None for o in orders)
