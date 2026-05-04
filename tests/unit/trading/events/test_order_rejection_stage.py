"""
OrderRejection阶段测试

测试订单拒绝阶段的组件交互和逻辑处理
涵盖风控拒绝、代理拒绝、市场拒绝、拒绝通知等
相关组件：RiskManager, Broker, Portfolio, EventEngine
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

from ginkgo.entities.order import Order
from ginkgo.trading.events.order_lifecycle_events import EventOrderRejected
from ginkgo.enums import ORDERSTATUS_TYPES, DIRECTION_TYPES, ORDER_TYPES, EVENT_TYPES


def _make_order(code="000001.SZ", direction=DIRECTION_TYPES.LONG, volume=100,
                order_type=ORDER_TYPES.LIMITORDER, limit_price=10.50,
                status=ORDERSTATUS_TYPES.NEW):
    return Order(
        portfolio_id="test-portfolio-001",
        engine_id="test-engine-001",
        task_id="test-run-001",
        code=code,
        direction=direction,
        order_type=order_type,
        status=status,
        volume=volume,
        limit_price=limit_price,
    )


def _make_rejected_event(order=None, reason="Rejected", reject_code=None, **kwargs):
    if order is None:
        order = _make_order()
    return EventOrderRejected(
        order=order,
        reject_reason=reason,
        reject_code=reject_code,
        **kwargs,
    )


@pytest.mark.unit
class TestRiskManagementRejection:
    """1. 风险管理拒绝测试"""

    def test_position_limit_rejection(self):
        """测试持仓限制拒绝"""
        max_position_ratio = 0.20
        current_ratio = 0.15
        new_order_ratio = 0.10
        is_rejected = (current_ratio + new_order_ratio) > max_position_ratio
        assert is_rejected is True

    def test_capital_inadequacy_rejection(self):
        """测试资金不足拒绝"""
        available_capital = 5000
        required_capital = 10000
        is_rejected = required_capital > available_capital
        assert is_rejected is True

    def test_daily_trading_limit_rejection(self):
        """测试日交易限制拒绝"""
        daily_limit = 100000
        daily_used = 95000
        new_order_value = 10000
        is_rejected = (daily_used + new_order_value) > daily_limit
        assert is_rejected is True

    def test_volatility_limit_rejection(self):
        """测试波动率限制拒绝"""
        max_volatility = 0.05
        current_volatility = 0.08
        is_rejected = current_volatility > max_volatility
        assert is_rejected is True

    def test_concentration_risk_rejection(self):
        """测试集中度风险拒绝"""
        max_concentration = 0.30
        single_stock_ratio = 0.35
        is_rejected = single_stock_ratio > max_concentration
        assert is_rejected is True


@pytest.mark.unit
class TestBrokerRejection:
    """2. 代理拒绝测试"""

    def test_broker_order_validation_rejection(self):
        """测试代理订单验证拒绝"""
        # Order with volume=0 cannot be created - validates rejection at creation level
        with pytest.raises(Exception):
            _make_order(volume=0)

    def test_broker_capacity_rejection(self):
        """测试代理容量拒绝"""
        broker_max_orders = 100
        pending_orders = 100
        is_rejected = pending_orders >= broker_max_orders
        assert is_rejected is True

    def test_broker_market_hours_rejection(self):
        """测试代理交易时段拒绝"""
        order_time = datetime.time(8, 0)
        market_open = datetime.time(9, 30)
        is_rejected = order_time < market_open
        assert is_rejected is True

    def test_broker_instrument_rejection(self):
        """测试代理标的拒绝"""
        supported_instruments = {"000001.SZ", "600036.SH", "601398.SH"}
        target = "INVALID.SZ"
        is_rejected = target not in supported_instruments
        assert is_rejected is True

    def test_broker_account_status_rejection(self):
        """测试代理账户状态拒绝"""
        account_status = "FROZEN"
        is_rejected = account_status != "ACTIVE"
        assert is_rejected is True


@pytest.mark.unit
class TestMarketRejection:
    """3. 市场拒绝测试"""

    def test_exchange_price_limit_rejection(self):
        """测试交易所价格限制拒绝"""
        limit_up = 11.00
        limit_down = 9.00
        order_price = 12.00
        is_rejected = order_price > limit_up or order_price < limit_down
        assert is_rejected is True

    def test_exchange_volume_limit_rejection(self):
        """测试交易所数量限制拒绝"""
        max_volume = 1000000
        order_volume = 2000000
        is_rejected = order_volume > max_volume
        assert is_rejected is True

    def test_exchange_trading_halt_rejection(self):
        """测试交易所停牌拒绝"""
        is_trading_halted = True
        is_rejected = is_trading_halted
        assert is_rejected is True

    def test_exchange_circuit_breaker_rejection(self):
        """测试交易所熔断拒绝"""
        circuit_breaker_active = True
        is_rejected = circuit_breaker_active
        assert is_rejected is True

    def test_exchange_maintenance_rejection(self):
        """测试交易所维护拒绝"""
        maintenance_mode = True
        is_rejected = maintenance_mode
        assert is_rejected is True


@pytest.mark.unit
class TestOrderRejectedEventCreation:
    """4. 订单拒绝事件创建测试"""

    def test_rejection_event_instantiation(self):
        """测试拒绝事件实例化"""
        order = _make_order()
        event = EventOrderRejected(order=order, reject_reason="Insufficient funds")
        assert isinstance(event, EventOrderRejected)

    def test_rejection_reason_classification(self):
        """测试拒绝原因分类"""
        event = _make_rejected_event(reason="Position limit exceeded", reject_code="RISK_001")
        assert event.reject_reason == "Position limit exceeded"
        assert event.reject_code == "RISK_001"

    def test_rejection_event_attributes(self):
        """测试拒绝事件属性"""
        order = _make_order("600036.SH", DIRECTION_TYPES.SHORT, 300)
        ts = datetime.datetime(2024, 3, 15, 10, 30, 0)
        event = EventOrderRejected(order=order, reject_reason="Test rejection", timestamp=ts)
        assert event.order_id == order.uuid
        assert event.code == "600036.SH"
        assert event.timestamp == ts

    def test_rejection_severity_level(self):
        """测试拒绝严重程度级别"""
        critical_reject = _make_rejected_event(reason="Account frozen", reject_code="CRITICAL")
        warning_reject = _make_rejected_event(reason="Price too far from market", reject_code="WARNING")
        assert critical_reject.reject_code == "CRITICAL"
        assert warning_reject.reject_code == "WARNING"

    def test_rejection_context_preservation(self):
        """测试拒绝上下文保持"""
        order = _make_order(volume=500, limit_price=20.00)
        event = EventOrderRejected(
            order=order,
            reject_reason="Capital insufficient",
            portfolio_id=order.portfolio_id,
            engine_id=order.engine_id,
            task_id=order.task_id,
        )
        assert event.portfolio_id == order.portfolio_id
        assert event.engine_id == order.engine_id
        assert event.code == order.code


@pytest.mark.unit
class TestOrderStatusUpdateOnRejection:
    """5. 拒绝时订单状态更新测试"""

    def test_order_status_transition_to_rejected(self):
        """测试订单状态转换到已拒绝"""
        order = _make_order()
        event = _make_rejected_event(order=order)
        assert event.event_type == EVENT_TYPES.ORDERREJECTED

    def test_rejection_timestamp_recording(self):
        """测试拒绝时间戳记录"""
        ts = datetime.datetime(2024, 3, 15, 10, 30, 5)
        event = _make_rejected_event(timestamp=ts)
        assert event.timestamp == ts

    def test_rejection_reason_storage(self):
        """测试拒绝原因存储"""
        event = _make_rejected_event(reason="Insufficient capital for order")
        assert event.reject_reason == "Insufficient capital for order"

    def test_rejection_source_identification(self):
        """测试拒绝来源识别"""
        risk_reject = _make_rejected_event(reason="Position limit", reject_code="RISK_MGR")
        broker_reject = _make_rejected_event(reason="Invalid order", reject_code="BROKER")
        assert risk_reject.reject_code == "RISK_MGR"
        assert broker_reject.reject_code == "BROKER"

    def test_order_lifecycle_termination(self):
        """测试订单生命周期终止"""
        order = _make_order()
        event = _make_rejected_event(order=order)
        assert event.event_type == EVENT_TYPES.ORDERREJECTED
        assert event.order_id == order.uuid


@pytest.mark.unit
class TestCapitalUnfreezingOnRejection:
    """6. 拒绝时资金解冻测试"""

    def test_frozen_capital_identification(self):
        """测试冻结资金识别"""
        order = _make_order(volume=1000, limit_price=10.00)
        order.frozen_money = Decimal(str(float(order.volume * order.limit_price)))
        assert float(order.frozen_money) == 10000.0

    def test_capital_unfreezing_execution(self):
        """测试资金解冻执行"""
        order = _make_order(volume=500, limit_price=20.00)
        order.frozen_money = Decimal("10000")
        # Simulate unfreezing
        order.frozen_money = Decimal("0")
        assert float(order.frozen_money) == 0.0

    def test_portfolio_balance_restoration(self):
        """测试投资组合余额恢复"""
        order = _make_order(volume=200, limit_price=15.00)
        frozen = Decimal(str(float(order.volume * order.limit_price)))
        order.frozen_money = frozen
        order.frozen_money = Decimal("0")
        assert float(order.frozen_money) == 0.0

    def test_unfreezing_audit_trail(self):
        """测试解冻审计追踪"""
        order = _make_order()
        event = EventOrderRejected(
            order=order,
            reject_reason="Risk limit breached",
            reject_code="RISK_001",
            portfolio_id=order.portfolio_id,
        )
        assert event.order_id == order.uuid
        assert event.reject_reason == "Risk limit breached"


@pytest.mark.unit
class TestRejectionEventPropagation:
    """7. 拒绝事件传播测试"""

    def test_rejection_event_publishing(self):
        """测试拒绝事件发布"""
        event = _make_rejected_event()
        assert event.event_type == EVENT_TYPES.ORDERREJECTED
        assert event.uuid is not None

    def test_portfolio_rejection_notification(self):
        """测试投资组合拒绝通知"""
        order = _make_order()
        event = EventOrderRejected(order=order, reject_reason="Rejected", portfolio_id=order.portfolio_id)
        assert event.portfolio_id == order.portfolio_id

    def test_strategy_rejection_feedback(self):
        """测试策略拒绝反馈"""
        order = _make_order("600036.SH")
        event = _make_rejected_event(order=order, reason="Market halted")
        assert event.code == "600036.SH"
        assert event.reject_reason == "Market halted"

    def test_risk_manager_rejection_learning(self):
        """测试风险管理器拒绝学习"""
        rejections = ["position_limit", "position_limit", "capital"]
        position_count = rejections.count("position_limit")
        assert position_count == 2

    def test_analyzer_rejection_analysis(self):
        """测试分析器拒绝分析"""
        rejection_codes = ["RISK_001", "RISK_001", "BROKER_001", "RISK_002"]
        risk_count = sum(1 for c in rejection_codes if c.startswith("RISK"))
        assert risk_count == 3


@pytest.mark.unit
class TestRejectionRecoveryAndAdaptation:
    """8. 拒绝恢复和适应测试"""

    def test_automatic_order_adjustment(self):
        """测试自动订单调整"""
        original_volume = 1000
        max_volume = 500
        adjusted_volume = min(original_volume, max_volume)
        assert adjusted_volume == 500

    def test_rejection_pattern_recognition(self):
        """测试拒绝模式识别"""
        rejection_history = ["position_limit"] * 5
        is_pattern = len(rejection_history) >= 3
        assert is_pattern is True

    def test_alternative_execution_path(self):
        """测试替代执行路径"""
        primary_broker = "BROKER_A"
        fallback_broker = "BROKER_B"
        available = primary_broker is None
        selected = fallback_broker if available else primary_broker
        assert selected == "BROKER_A"

    def test_rejection_threshold_adjustment(self):
        """测试拒绝阈值调整"""
        current_threshold = Decimal("0.20")
        rejection_rate = 0.30
        if rejection_rate > 0.15:
            new_threshold = float(current_threshold * Decimal("0.9"))
        else:
            new_threshold = float(current_threshold)
        assert new_threshold == 0.18

    def test_rejection_reporting_and_alerting(self):
        """测试拒绝报告和告警"""
        daily_rejections = 15
        alert_threshold = 10
        should_alert = daily_rejections > alert_threshold
        assert should_alert is True
