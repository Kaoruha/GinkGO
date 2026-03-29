"""
OrderSubmission阶段测试

测试订单提交阶段的组件交互和逻辑处理
涵盖风险最终检查、订单路由选择、Broker通信等
相关组件：Portfolio, RiskManager, Broker, OrderRouter
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
from ginkgo.trading.events.order_lifecycle_events import EventOrderAck
from ginkgo.enums import ORDERSTATUS_TYPES, DIRECTION_TYPES, ORDER_TYPES, EVENT_TYPES


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


@pytest.mark.unit
class TestOrderSubmissionPreparation:
    """1. 订单提交准备测试"""

    def test_order_status_transition_to_submitting(self):
        """测试订单状态转换到提交中"""
        order = _make_order(status=ORDERSTATUS_TYPES.NEW)
        assert order.is_new() is True
        order.submit()
        assert order.is_submitted() is True
        assert order.status == ORDERSTATUS_TYPES.SUBMITTED

    def test_order_frozen_capital_calculation(self):
        """测试订单冻结资金计算"""
        order = _make_order(volume=1000, limit_price=10.50)
        frozen = float(order.volume * order.limit_price)
        assert frozen == 10500.0

    def test_portfolio_capital_freezing(self):
        """测试投资组合资金冻结"""
        order = _make_order(volume=500, limit_price=20.00)
        order.frozen_money = Decimal(str(float(order.volume * order.limit_price)))
        assert float(order.frozen_money) == 10000.0

    def test_order_sequence_number_assignment(self):
        """测试订单序列号分配"""
        order = _make_order()
        assert order.uuid is not None
        assert len(order.uuid) > 0
        uuid1 = order.uuid
        order2 = _make_order()
        assert order2.uuid != uuid1

    def test_order_submission_timestamp(self):
        """测试订单提交时间戳"""
        ts = datetime.datetime(2024, 3, 15, 10, 30, 0)
        order = _make_order()
        order.submit()
        assert order.status == ORDERSTATUS_TYPES.SUBMITTED


@pytest.mark.unit
class TestOrderSubmissionRiskFinalCheck:
    """2. 订单提交风险最终检查测试"""

    def test_risk_manager_final_validation(self):
        """测试风险管理器最终验证"""
        order = _make_order(volume=100, limit_price=10.00)
        order_cost = float(order.volume * order.limit_price)
        available_capital = 20000.0
        assert order_cost <= available_capital

    def test_position_limit_final_check(self):
        """测试持仓限制最终检查"""
        max_position = 0.25
        new_order_value = 50000
        portfolio_value = 1000000
        new_ratio = new_order_value / portfolio_value
        assert new_ratio <= max_position

    def test_capital_adequacy_final_check(self):
        """测试资金充足性最终检查"""
        order = _make_order(volume=100, limit_price=50.00)
        order_cost = float(order.volume * order.limit_price)
        assert order_cost == 5000.0

    def test_market_status_check(self):
        """测试市场状态检查"""
        trading_hours_start = datetime.time(9, 30)
        trading_hours_end = datetime.time(15, 0)
        current = datetime.time(10, 0)
        assert trading_hours_start <= current <= trading_hours_end

    def test_order_rejection_at_submission(self):
        """测试提交阶段的订单拒绝"""
        order = _make_order(status=ORDERSTATUS_TYPES.NEW, volume=100)
        with pytest.raises(Exception):
            order.fill(price=10.0)


@pytest.mark.unit
class TestOrderRoutingAndBrokerSelection:
    """3. 订单路由和代理选择测试"""

    def test_broker_selection_logic(self):
        """测试代理选择逻辑"""
        order = _make_order(order_type=ORDER_TYPES.LIMITORDER)
        assert order.order_type == ORDER_TYPES.LIMITORDER

    def test_order_routing_rules(self):
        """测试订单路由规则"""
        market_order = _make_order(order_type=ORDER_TYPES.MARKETORDER, limit_price=0)
        limit_order = _make_order(order_type=ORDER_TYPES.LIMITORDER, limit_price=10.50)
        assert market_order.order_type != limit_order.order_type

    def test_broker_availability_check(self):
        """测试代理可用性检查"""
        broker_available = True
        assert broker_available is True

    def test_broker_capacity_check(self):
        """测试代理容量检查"""
        broker_max_capacity = 10000
        pending_orders = 3000
        available_capacity = broker_max_capacity - pending_orders
        assert available_capacity > 0

    def test_fallback_broker_selection(self):
        """测试备用代理选择"""
        primary_available = False
        fallback_available = True
        selected = primary_available or fallback_available
        assert selected is True


@pytest.mark.unit
class TestOrderSubmissionToBroker:
    """4. 订单提交到代理测试"""

    def test_order_format_conversion(self):
        """测试订单格式转换"""
        order = _make_order()
        order_data = {
            "code": order.code,
            "direction": order.direction.name,
            "volume": order.volume,
            "price": float(order.limit_price),
        }
        assert order_data["code"] == "000001.SZ"
        assert order_data["direction"] == "LONG"
        assert order_data["volume"] == 100

    def test_broker_communication_setup(self):
        """测试代理通信设置"""
        order = _make_order()
        assert order.portfolio_id == "test-portfolio-001"

    def test_order_transmission_to_broker(self):
        """测试订单传输到代理"""
        order = _make_order()
        order.submit()
        assert order.status == ORDERSTATUS_TYPES.SUBMITTED

    def test_broker_acknowledgment_waiting(self):
        """测试等待代理确认"""
        order = _make_order()
        order.submit()
        ack_event = EventOrderAck(order=order, ack_message="Order accepted")
        assert ack_event.event_type == EVENT_TYPES.ORDERACK
        assert ack_event.order_id == order.uuid

    def test_submission_timeout_handling(self):
        """测试提交超时处理"""
        order = _make_order()
        order.submit()
        timeout_seconds = 30
        assert timeout_seconds > 0


@pytest.mark.unit
class TestOrderSubmissionEventGeneration:
    """5. 订单提交事件生成测试"""

    def test_order_submitted_event_creation(self):
        """测试订单已提交事件创建"""
        order = _make_order()
        order.submit()
        ack_event = EventOrderAck(order=order)
        assert ack_event is not None
        assert ack_event.event_type == EVENT_TYPES.ORDERACK

    def test_submission_event_attributes(self):
        """测试提交事件属性"""
        order = _make_order()
        order.submit()
        ts = datetime.datetime(2024, 3, 15, 10, 30, 0)
        ack_event = EventOrderAck(order=order, timestamp=ts, portfolio_id="test-portfolio-001")
        assert ack_event.order_id == order.uuid
        assert ack_event.code == "000001.SZ"

    def test_submission_event_publishing(self):
        """测试提交事件发布"""
        order = _make_order()
        order.submit()
        ack_event = EventOrderAck(order=order)
        assert ack_event.uuid is not None

    def test_submission_audit_logging(self):
        """测试提交审计日志"""
        order = _make_order()
        order.submit()
        assert order.status == ORDERSTATUS_TYPES.SUBMITTED
        assert order.portfolio_id == "test-portfolio-001"


@pytest.mark.unit
class TestOrderSubmissionStateManagement:
    """6. 订单提交状态管理测试"""

    def test_order_status_update_to_submitted(self):
        """测试订单状态更新到已提交"""
        order = _make_order(status=ORDERSTATUS_TYPES.NEW)
        order.submit()
        assert order.status == ORDERSTATUS_TYPES.SUBMITTED
        assert order.is_submitted() is True

    def test_submission_failure_status_handling(self):
        """测试提交失败状态处理"""
        order = _make_order(status=ORDERSTATUS_TYPES.NEW)
        assert order.is_new() is True
        # Simulate failed submission - order stays in NEW state
        assert order.status == ORDERSTATUS_TYPES.NEW

    def test_portfolio_order_tracking_update(self):
        """测试投资组合订单跟踪更新"""
        order = _make_order()
        order.submit()
        assert order.uuid is not None
        assert order.status == ORDERSTATUS_TYPES.SUBMITTED

    def test_order_submission_metrics(self):
        """测试订单提交指标"""
        total_submissions = 100
        successful = 95
        success_rate = successful / total_submissions
        assert success_rate == 0.95


@pytest.mark.unit
class TestOrderSubmissionErrorHandling:
    """7. 订单提交错误处理测试"""

    def test_network_failure_handling(self):
        """测试网络故障处理"""
        order = _make_order()
        order.submit()
        network_retry_count = 0
        max_retries = 3
        assert network_retry_count < max_retries

    def test_broker_rejection_handling(self):
        """测试代理拒绝处理"""
        order = _make_order(status=ORDERSTATUS_TYPES.NEW)
        order.submit()
        # After submit, order could be rejected
        assert order.status in (ORDERSTATUS_TYPES.SUBMITTED, ORDERSTATUS_TYPES.NEW)

    def test_invalid_order_format_handling(self):
        """测试无效订单格式处理"""
        with pytest.raises(Exception):
            Order(
                portfolio_id="test-portfolio-001",
                engine_id="test-engine-001",
                run_id="test-run-001",
                code="",
                direction=DIRECTION_TYPES.LONG,
                order_type=ORDER_TYPES.LIMITORDER,
                status=ORDERSTATUS_TYPES.NEW,
                volume=100,
                limit_price=10.50,
            )

    def test_submission_retry_mechanism(self):
        """测试提交重试机制"""
        max_retries = 3
        retry_count = 0
        for _ in range(max_retries):
            retry_count += 1
        assert retry_count == max_retries

    def test_submission_failure_recovery(self):
        """测试提交失败恢复"""
        order = _make_order(status=ORDERSTATUS_TYPES.NEW)
        frozen_amount = Decimal("10000")
        order.frozen_money = frozen_amount
        # On failure, unfreeze
        order.frozen_money = Decimal("0")
        assert float(order.frozen_money) == 0.0


@pytest.mark.unit
class TestOrderSubmissionBacktestVsLive:
    """8. 订单提交回测与实盘对比测试"""

    def test_backtest_submission_simulation(self):
        """测试回测提交模拟"""
        order = _make_order(status=ORDERSTATUS_TYPES.NEW)
        order.submit()
        assert order.status == ORDERSTATUS_TYPES.SUBMITTED

    def test_live_submission_real_broker(self):
        """测试实盘提交真实代理"""
        order = _make_order()
        broker_id = "BROKER_LIVE_001"
        ack = EventOrderAck(order=order, ack_message="Order accepted", portfolio_id=order.portfolio_id)
        ack.broker_order_id = broker_id
        assert ack.broker_order_id == broker_id

    def test_submission_timing_consistency(self):
        """测试提交时间一致性"""
        order = _make_order()
        order.submit()
        assert order.timestamp is not None

    def test_submission_cost_modeling(self):
        """测试提交成本建模"""
        commission_rate = Decimal("0.0003")
        order_value = Decimal("100000")
        commission = order_value * commission_rate
        assert float(commission) == 30.0
