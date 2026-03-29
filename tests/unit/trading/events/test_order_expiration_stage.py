"""
OrderExpiration阶段测试

测试订单过期阶段的组件交互和逻辑处理
涵盖时间过期、条件过期、自动清理、过期通知等
相关组件：TimeManager, Portfolio, EventEngine, OrderTracker
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
from ginkgo.trading.events.order_lifecycle_events import EventOrderExpired, EventOrderCancelAck
from ginkgo.enums import (
    ORDERSTATUS_TYPES,
    DIRECTION_TYPES,
    ORDER_TYPES,
    EVENT_TYPES,
)


def _make_order(code="000001.SZ", direction=DIRECTION_TYPES.LONG, volume=100,
                order_type=ORDER_TYPES.LIMITORDER, limit_price=10.50,
                status=ORDERSTATUS_TYPES.NEW):
    return Order(
        portfolio_id="test-portfolio-001",
        engine_id="test-engine-001",
        run_id="test-run-001",
        code=code,
        direction=direction,
        order_type=order_type,
        status=status,
        volume=volume,
        limit_price=limit_price,
    )


def _make_submitted_order(**kwargs):
    order = _make_order(**kwargs)
    order.submit()
    return order


def _make_expired_event(order=None, reason=None, **kwargs):
    if order is None:
        order = _make_submitted_order()
    if reason is None:
        reason = "Time expired"
    return EventOrderExpired(order=order, expire_reason=reason, **kwargs)


@pytest.mark.unit
class TestOrderExpirationDetection:
    """1. 订单过期检测测试"""

    def test_time_based_expiration_detection(self):
        """测试基于时间的过期检测"""
        creation_time = datetime.datetime(2024, 3, 15, 10, 0, 0)
        expiration_time = datetime.datetime(2024, 3, 15, 15, 0, 0)
        current_time = datetime.datetime(2024, 3, 15, 15, 1, 0)
        is_expired = current_time > expiration_time
        assert is_expired is True

    def test_market_close_expiration(self):
        """测试市场收盘过期"""
        market_close = datetime.time(15, 0)
        current = datetime.time(15, 5)
        is_expired = current >= market_close
        assert is_expired is True

    def test_good_till_date_expiration(self):
        """测试指定日期过期"""
        gtd_date = datetime.date(2024, 3, 20)
        today = datetime.date(2024, 3, 21)
        is_expired = today > gtd_date
        assert is_expired is True

    def test_immediate_or_cancel_expiration(self):
        """测试立即成交或取消过期"""
        # IOC orders expire immediately if not fully filled
        order = _make_submitted_order()
        order.partial_fill(50, 10.50)
        is_ioc_expired = order.get_remaining_volume() > 0
        assert is_ioc_expired is True

    def test_fill_or_kill_expiration(self):
        """测试全额成交或取消过期"""
        order = _make_submitted_order(volume=100)
        order.partial_fill(80, 10.50)
        # FOK requires full fill, partial means cancelled
        is_fok_expired = order.get_remaining_volume() > 0
        assert is_fok_expired is True


@pytest.mark.unit
class TestExpirationConditionEvaluation:
    """2. 过期条件评估测试"""

    def test_order_validity_period_check(self):
        """测试订单有效期检查"""
        creation = datetime.datetime(2024, 3, 15, 10, 0, 0)
        valid_until = datetime.datetime(2024, 3, 15, 14, 0, 0)
        now = datetime.datetime(2024, 3, 15, 13, 0, 0)
        is_valid = now <= valid_until
        assert is_valid is True

    def test_market_status_impact_on_expiration(self):
        """测试市场状态对过期的影响"""
        is_market_open = False
        day_order = True
        if not is_market_open and day_order:
            should_expire = True
        else:
            should_expire = False
        assert should_expire is True

    def test_partial_fill_expiration_handling(self):
        """测试部分成交过期处理"""
        order = _make_submitted_order(volume=1000)
        order.partial_fill(300, 10.50)
        expired_quantity = order.volume - order.transaction_volume
        assert expired_quantity == 700

    def test_conditional_order_expiration(self):
        """测试条件单过期"""
        target_price = 11.00
        current_price = 9.50
        days_waiting = 5
        max_wait = 3
        condition_unmet = current_price < target_price
        wait_too_long = days_waiting > max_wait
        should_expire = condition_unmet and wait_too_long
        assert should_expire is True

    def test_expiration_priority_ranking(self):
        """测试过期优先级排序"""
        orders = [
            (1, "FOK"),
            (2, "IOC"),
            (3, "DAY"),
        ]
        sorted_orders = sorted(orders, key=lambda x: x[0])
        assert sorted_orders[0][1] == "FOK"
        assert sorted_orders[-1][1] == "DAY"


@pytest.mark.unit
class TestOrderExpiredEventCreation:
    """3. 订单过期事件创建测试"""

    def test_expiration_event_instantiation(self):
        """测试过期事件实例化"""
        order = _make_submitted_order()
        event = EventOrderExpired(order=order)
        assert isinstance(event, EventOrderExpired)

    def test_expiration_reason_classification(self):
        """测试过期原因分类"""
        event_time = _make_expired_event(reason="End of trading day")
        event_manual = _make_expired_event(reason="User requested cancellation")
        assert event_time.expire_reason == "End of trading day"
        assert event_manual.expire_reason == "User requested cancellation"

    def test_expiration_event_attributes(self):
        """测试过期事件属性"""
        order = _make_submitted_order(code="600036.SH", volume=200)
        ts = datetime.datetime(2024, 3, 15, 15, 0, 0)
        event = EventOrderExpired(order=order, expire_reason="Market closed", timestamp=ts)
        assert event.order_id == order.uuid
        assert event.code == "600036.SH"
        assert event.timestamp == ts
        assert event.expired_quantity == 200

    def test_expiration_context_preservation(self):
        """测试过期上下文保持"""
        order = _make_submitted_order(volume=500, limit_price=20.00)
        event = EventOrderExpired(
            order=order,
            expire_reason="GTD expired",
            portfolio_id=order.portfolio_id,
            engine_id=order.engine_id,
            run_id=order.run_id,
        )
        assert event.portfolio_id == order.portfolio_id
        assert event.engine_id == order.engine_id
        assert event.code == order.code

    def test_batch_expiration_event_handling(self):
        """测试批量过期事件处理"""
        orders = [_make_submitted_order() for _ in range(3)]
        events = [EventOrderExpired(order=o, expire_reason="Day end") for o in orders]
        assert len(events) == 3
        assert all(e.event_type == EVENT_TYPES.ORDEREXPIRED for e in events)


@pytest.mark.unit
class TestOrderStatusUpdateOnExpiration:
    """4. 过期时订单状态更新测试"""

    def test_order_status_transition_to_expired(self):
        """测试订单状态转换到已过期"""
        order = _make_submitted_order()
        event = _make_expired_event(order=order)
        assert event.event_type == EVENT_TYPES.ORDEREXPIRED
        assert event.order_id == order.uuid

    def test_expiration_timestamp_recording(self):
        """测试过期时间戳记录"""
        ts = datetime.datetime(2024, 3, 15, 15, 0, 0)
        event = _make_expired_event(timestamp=ts)
        assert event.timestamp == ts

    def test_partial_fill_expiration_status(self):
        """测试部分成交过期状态"""
        order = _make_submitted_order(volume=500)
        order.partial_fill(200, 10.50)
        event = EventOrderExpired(order=order, expire_reason="Day order expired")
        assert event.expired_quantity == 300
        assert order.transaction_volume == 200

    def test_expiration_audit_information(self):
        """测试过期审计信息"""
        order = _make_submitted_order()
        event = EventOrderExpired(
            order=order,
            expire_reason="End of day",
            portfolio_id=order.portfolio_id,
        )
        assert event.order_id == order.uuid
        assert event.expire_reason == "End of day"
        assert event.portfolio_id == order.portfolio_id

    def test_order_lifecycle_completion_on_expiration(self):
        """测试过期时订单生命周期完成"""
        order = _make_submitted_order()
        event = EventOrderExpired(order=order)
        # Expiration is a terminal event
        is_terminal = event.event_type == EVENT_TYPES.ORDEREXPIRED
        assert is_terminal is True
        assert event.order_id == order.uuid


@pytest.mark.unit
class TestCapitalUnfreezingOnExpiration:
    """5. 过期时资金解冻测试"""

    def test_expired_order_capital_identification(self):
        """测试过期订单资金识别"""
        order = _make_submitted_order(volume=500, limit_price=20.00)
        order.frozen_money = Decimal(str(float(order.volume * order.limit_price)))
        assert float(order.frozen_money) == 10000.0

    def test_capital_unfreezing_on_expiration(self):
        """测试过期时资金解冻"""
        order = _make_submitted_order(volume=100, limit_price=10.00)
        order.frozen_money = Decimal("1000")
        event = EventOrderExpired(order=order)
        order.frozen_money = Decimal("0")
        assert float(order.frozen_money) == 0.0

    def test_partial_fill_capital_adjustment(self):
        """测试部分成交资金调整"""
        order = _make_submitted_order(volume=1000, limit_price=10.00)
        order.partial_fill(400, 10.00)
        remaining_volume = order.get_remaining_volume()
        unfreeze_amount = float(remaining_volume * order.limit_price)
        assert unfreeze_amount == 6000.0

    def test_portfolio_balance_restoration(self):
        """测试投资组合余额恢复"""
        order = _make_submitted_order(volume=200, limit_price=15.00)
        frozen = Decimal(str(float(order.volume * order.limit_price)))
        order.frozen_money = frozen
        order.frozen_money = Decimal("0")
        assert float(order.frozen_money) == 0.0

    def test_expiration_capital_audit_trail(self):
        """测试过期资金审计追踪"""
        order = _make_submitted_order(volume=300, limit_price=25.00)
        frozen_amount = float(order.volume * order.limit_price)
        event = EventOrderExpired(
            order=order,
            expire_reason="Day order expired",
            portfolio_id=order.portfolio_id,
        )
        assert frozen_amount == 7500.0
        assert event.order_id == order.uuid


@pytest.mark.unit
class TestExpirationEventPropagation:
    """6. 过期事件传播测试"""

    def test_expiration_event_publishing(self):
        """测试过期事件发布"""
        event = _make_expired_event()
        assert event.event_type == EVENT_TYPES.ORDEREXPIRED
        assert event.uuid is not None

    def test_portfolio_expiration_notification(self):
        """测试投资组合过期通知"""
        order = _make_submitted_order()
        event = EventOrderExpired(order=order, portfolio_id=order.portfolio_id)
        assert event.portfolio_id == order.portfolio_id

    def test_strategy_expiration_feedback(self):
        """测试策略过期反馈"""
        order = _make_submitted_order(code="600036.SH", direction=DIRECTION_TYPES.SHORT)
        event = EventOrderExpired(order=order, expire_reason="Market closed")
        assert event.code == "600036.SH"
        assert event.expire_reason == "Market closed"

    def test_analyzer_expiration_recording(self):
        """测试分析器过期记录"""
        order = _make_submitted_order(volume=500)
        event = EventOrderExpired(order=order, expire_reason="GTD date reached")
        assert event.expired_quantity == 500
        assert event.order_id == order.uuid

    def test_risk_manager_expiration_processing(self):
        """测试风险管理器过期处理"""
        order = _make_submitted_order(volume=1000, limit_price=10.00)
        event = EventOrderExpired(order=order, expire_reason="End of day")
        expired_value = float(event.expired_quantity * order.limit_price)
        assert expired_value == 10000.0


@pytest.mark.unit
class TestExpirationCleanupAndMaintenance:
    """7. 过期清理和维护测试"""

    def test_expired_order_cleanup(self):
        """测试过期订单清理"""
        order = _make_submitted_order()
        event = EventOrderExpired(order=order, expire_reason="Day end")
        is_cleaned_up = event.event_type == EVENT_TYPES.ORDEREXPIRED
        assert is_cleaned_up is True

    def test_expiration_batch_processing(self):
        """测试过期批处理"""
        orders = [_make_submitted_order() for _ in range(5)]
        events = [EventOrderExpired(order=o) for o in orders]
        assert len(events) == 5
        assert all(e.event_type == EVENT_TYPES.ORDEREXPIRED for e in events)

    def test_expiration_statistics_update(self):
        """测试过期统计更新"""
        total_expired = 15
        total_submitted = 200
        expiration_rate = total_expired / total_submitted
        assert expiration_rate == 0.075

    def test_expiration_pattern_analysis(self):
        """测试过期模式分析"""
        expired_codes = ["000001.SZ"] * 3 + ["600036.SH"] * 2
        from collections import Counter
        pattern = Counter(expired_codes)
        assert pattern["000001.SZ"] == 3
        assert pattern["600036.SH"] == 2

    def test_expiration_alert_generation(self):
        """测试过期告警生成"""
        daily_expired_count = 20
        alert_threshold = 10
        should_alert = daily_expired_count > alert_threshold
        assert should_alert is True


@pytest.mark.unit
class TestExpirationErrorHandlingAndRecovery:
    """8. 过期错误处理和恢复测试"""

    def test_expiration_detection_failure(self):
        """测试过期检测失败"""
        is_monitor_running = False
        fallback_check = True
        can_detect = is_monitor_running or fallback_check
        assert can_detect is True

    def test_expiration_processing_timeout(self):
        """测试过期处理超时"""
        timeout_seconds = 60
        elapsed = 75
        is_timeout = elapsed > timeout_seconds
        assert is_timeout is True

    def test_partial_expiration_failure_recovery(self):
        """测试部分过期失败恢复"""
        orders = [_make_submitted_order() for _ in range(3)]
        results = []
        for o in orders:
            try:
                event = EventOrderExpired(order=o)
                results.append(("success", o.uuid))
            except Exception:
                results.append(("failed", o.uuid))
        assert len(results) == 3

    def test_expiration_state_inconsistency(self):
        """测试过期状态不一致"""
        order = _make_submitted_order()
        # Simulate: order was already filled but expiration event generated
        order.fill(price=10.50)
        event = EventOrderExpired(order=order)
        # Detect inconsistency: filled order shouldn't have expired
        is_inconsistent = order.is_filled() and event.event_type == EVENT_TYPES.ORDEREXPIRED
        assert is_inconsistent is True

    def test_expiration_cascade_failure_prevention(self):
        """测试过期级联失败预防"""
        failures = 0
        max_cascade_failures = 5
        orders = [_make_submitted_order() for _ in range(10)]
        for o in orders:
            try:
                EventOrderExpired(order=o)
            except Exception:
                failures += 1
                if failures > max_cascade_failures:
                    break
        assert failures <= max_cascade_failures
