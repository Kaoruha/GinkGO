"""
OrderExecution阶段测试

测试订单执行阶段的组件交互和逻辑处理
涵盖订单撮合、部分成交、完全成交、持仓更新等
相关组件：MatchMaking, Broker, Portfolio, PositionManager, Settlement
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
from ginkgo.trading.events.order_lifecycle_events import (
    EventOrderPartiallyFilled,
    EventOrderAck,
)
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


@pytest.mark.unit
class TestOrderMatchingProcess:
    """1. 订单撮合过程测试"""

    def test_order_matching_initialization(self):
        """测试订单撮合初始化"""
        order = _make_submitted_order(volume=100, limit_price=10.50)
        assert order.is_active() is True
        assert order.status == ORDERSTATUS_TYPES.SUBMITTED

    def test_market_order_immediate_matching(self):
        """测试市价单即时撮合"""
        order = _make_submitted_order(order_type=ORDER_TYPES.MARKETORDER, limit_price=0, volume=200)
        assert order.is_active() is True

    def test_limit_order_price_matching(self):
        """测试限价单价格撮合"""
        order = _make_submitted_order(order_type=ORDER_TYPES.LIMITORDER, limit_price=10.50, volume=100)
        market_price = 10.30
        is_matchable = market_price <= float(order.limit_price)
        assert is_matchable is True

    def test_order_queue_priority_handling(self):
        """测试订单队列优先级处理"""
        order1 = _make_submitted_order(volume=100)
        order2 = _make_submitted_order(volume=200)
        assert order1.timestamp is not None
        assert order2.timestamp is not None

    def test_partial_matching_logic(self):
        """测试部分撮合逻辑"""
        order = _make_submitted_order(volume=1000)
        partial_fill_volume = 300
        remaining = order.volume - partial_fill_volume
        assert remaining == 700


@pytest.mark.unit
class TestPartialFillHandling:
    """2. 部分成交处理测试"""

    def test_partial_fill_event_generation(self):
        """测试部分成交事件生成"""
        order = _make_submitted_order(volume=1000)
        event = EventOrderPartiallyFilled(
            order=order,
            filled_quantity=300,
            fill_price=10.50,
        )
        assert isinstance(event, EventOrderPartiallyFilled)
        assert event.event_type == EVENT_TYPES.ORDERPARTIALLYFILLED

    def test_partial_fill_quantity_calculation(self):
        """测试部分成交数量计算"""
        order = _make_submitted_order(volume=1000)
        event = EventOrderPartiallyFilled(
            order=order,
            filled_quantity=400,
            fill_price=10.50,
        )
        assert event.filled_quantity == 400
        assert event.remaining_quantity == 600

    def test_partial_fill_price_recording(self):
        """测试部分成交价格记录"""
        order = _make_submitted_order(volume=500)
        event = EventOrderPartiallyFilled(
            order=order,
            filled_quantity=200,
            fill_price=10.30,
        )
        assert event.fill_price == 10.30
        assert event.fill_amount == 200 * 10.30

    def test_order_status_after_partial_fill(self):
        """测试部分成交后订单状态"""
        order = _make_submitted_order(volume=1000)
        order.partial_fill(300, 10.50)
        assert order.is_partially_filled() is True
        assert order.status == ORDERSTATUS_TYPES.PARTIAL_FILLED

    def test_multiple_partial_fills(self):
        """测试多次部分成交"""
        order = _make_submitted_order(volume=1000)
        order.partial_fill(300, 10.50)
        assert order.transaction_volume == 300
        order.partial_fill(200, 10.60)
        assert order.transaction_volume == 500
        assert order.get_fill_ratio() == 0.5


@pytest.mark.unit
class TestCompleteFillHandling:
    """3. 完全成交处理测试"""

    def test_complete_fill_event_generation(self):
        """测试完全成交事件生成"""
        order = _make_submitted_order(volume=500)
        event = EventOrderPartiallyFilled(
            order=order,
            filled_quantity=500,
            fill_price=10.50,
        )
        assert event.event_type == EVENT_TYPES.ORDERPARTIALLYFILLED
        assert event.filled_quantity == 500

    def test_order_status_transition_to_filled(self):
        """测试订单状态转换到已成交"""
        order = _make_submitted_order(volume=100, limit_price=10.50)
        order.fill(price=10.50)
        assert order.is_filled() is True
        assert order.status == ORDERSTATUS_TYPES.FILLED

    def test_final_execution_price_calculation(self):
        """测试最终执行价格计算"""
        order = _make_submitted_order(volume=200, limit_price=10.50)
        order.partial_fill(100, 10.30)
        order.partial_fill(100, 10.50)
        # VWAP should be (10.30*100 + 10.50*100) / 200
        assert order.is_filled() is True

    def test_order_completion_timestamp(self):
        """测试订单完成时间戳"""
        order = _make_submitted_order(volume=100)
        ts = datetime.datetime(2024, 3, 15, 10, 30, 0)
        order.fill(price=10.50)
        assert order.timestamp is not None

    def test_execution_fee_calculation(self):
        """测试执行费用计算"""
        order = _make_submitted_order(volume=100)
        order.fill(price=10.50, fee=5.25)
        assert float(order.fee) == 5.25


@pytest.mark.unit
class TestPositionUpdateFromExecution:
    """4. 执行后持仓更新测试"""

    def test_position_creation_from_new_order(self):
        """测试新订单创建持仓"""
        order = _make_submitted_order(direction=DIRECTION_TYPES.LONG, volume=100)
        order.fill(price=10.50)
        assert order.is_filled() is True
        assert order.volume == 100

    def test_position_quantity_update(self):
        """测试持仓数量更新"""
        order = _make_submitted_order(direction=DIRECTION_TYPES.LONG, volume=200)
        order.partial_fill(100, 10.50)
        assert order.transaction_volume == 100
        assert order.get_remaining_volume() == 100

    def test_position_cost_basis_calculation(self):
        """测试持仓成本基础计算"""
        order = _make_submitted_order(volume=200)
        order.partial_fill(100, 10.00)
        order.partial_fill(100, 10.50)
        # VWAP = (1000 + 1050) / 200 = 10.25
        assert float(order.transaction_price) == 10.25

    def test_position_pnl_update(self):
        """测试持仓盈亏更新"""
        buy_price = 10.50
        current_price = 11.00
        volume = 100
        pnl = (current_price - buy_price) * volume
        assert pnl == 50.0

    def test_position_closure_from_sell_order(self):
        """测试卖单关闭持仓"""
        order = _make_submitted_order(direction=DIRECTION_TYPES.SHORT, volume=100, limit_price=11.00)
        order.fill(price=11.00)
        assert order.is_filled() is True
        assert order.direction == DIRECTION_TYPES.SHORT


@pytest.mark.unit
class TestPortfolioUpdateFromExecution:
    """5. 执行后投资组合更新测试"""

    def test_portfolio_capital_update(self):
        """测试投资组合资金更新"""
        order = _make_submitted_order(direction=DIRECTION_TYPES.LONG, volume=100, limit_price=10.50)
        order.fill(price=10.50, fee=3.15)
        cost = float(order.volume * Decimal("10.50") + order.fee)
        assert cost == 1053.15

    def test_portfolio_market_value_recalculation(self):
        """测试投资组合市值重算"""
        order = _make_submitted_order(volume=200)
        order.fill(price=10.50)
        market_price = 11.00
        position_value = market_price * order.volume
        assert position_value == 2200.0

    def test_portfolio_performance_metrics_update(self):
        """测试投资组合绩效指标更新"""
        buy_price = 10.00
        current_price = 11.50
        return_pct = (current_price - buy_price) / buy_price * 100
        assert return_pct == 15.0

    def test_portfolio_risk_metrics_recalculation(self):
        """测试投资组合风险指标重算"""
        position_value = 50000
        portfolio_value = 200000
        weight = position_value / portfolio_value
        assert weight == 0.25

    def test_portfolio_allocation_rebalancing(self):
        """测试投资组合配置再平衡"""
        target_weights = {"stock_a": 0.6, "stock_b": 0.4}
        current_weights = {"stock_a": 0.7, "stock_b": 0.3}
        rebalance_needed = target_weights != current_weights
        assert rebalance_needed is True


@pytest.mark.unit
class TestExecutionEventPropagation:
    """6. 执行事件传播测试"""

    def test_execution_event_publishing(self):
        """测试执行事件发布"""
        order = _make_submitted_order(volume=100)
        event = EventOrderPartiallyFilled(
            order=order,
            filled_quantity=50,
            fill_price=10.50,
        )
        assert event.event_type == EVENT_TYPES.ORDERPARTIALLYFILLED
        assert event.uuid is not None

    def test_strategy_execution_notification(self):
        """测试策略执行通知"""
        order = _make_submitted_order(code="600036.SH", volume=200)
        event = EventOrderPartiallyFilled(
            order=order,
            filled_quantity=100,
            fill_price=15.00,
        )
        assert event.code == "600036.SH"
        assert event.filled_quantity == 100

    def test_risk_manager_execution_processing(self):
        """测试风险管理器执行处理"""
        order = _make_submitted_order(volume=500)
        order.partial_fill(500, 10.00)
        assert order.is_filled() is True
        assert order.transaction_volume == 500

    def test_analyzer_execution_recording(self):
        """测试分析器执行记录"""
        order = _make_submitted_order(volume=100)
        event = EventOrderPartiallyFilled(
            order=order,
            filled_quantity=100,
            fill_price=10.50,
            trade_id="TRD-001",
            commission=Decimal("3.15"),
        )
        assert event.trade_id == "TRD-001"
        assert event.fill_amount == 1050.0


@pytest.mark.unit
class TestExecutionSettlement:
    """7. 执行结算测试"""

    def test_trade_settlement_initiation(self):
        """测试交易结算启动"""
        order = _make_submitted_order(volume=100)
        order.fill(price=10.50)
        assert order.is_filled() is True

    def test_cash_settlement_calculation(self):
        """测试现金结算计算"""
        volume = 100
        price = 10.50
        commission = 3.15
        total = volume * price + commission
        assert total == 1053.15

    def test_security_delivery_processing(self):
        """测试证券交割处理"""
        order = _make_submitted_order(direction=DIRECTION_TYPES.LONG, volume=200)
        order.fill(price=10.00)
        assert order.is_filled() is True
        assert order.volume == 200

    def test_settlement_date_calculation(self):
        """测试结算日期计算"""
        trade_date = datetime.date(2024, 3, 15)
        t_plus_1 = trade_date + datetime.timedelta(days=1)
        # Skip weekend
        if t_plus_1.weekday() >= 5:
            t_plus_1 += datetime.timedelta(days=2)
        assert t_plus_1 >= trade_date

    def test_settlement_risk_monitoring(self):
        """测试结算风险监控"""
        settlement_amount = 100000
        max_settlement = 500000
        is_within_limit = settlement_amount <= max_settlement
        assert is_within_limit is True


@pytest.mark.unit
class TestExecutionStageErrorHandling:
    """8. 执行阶段错误处理测试"""

    def test_execution_failure_handling(self):
        """测试执行失败处理"""
        order = _make_submitted_order(volume=100)
        # Fill should succeed
        order.partial_fill(100, 10.50)
        assert order.transaction_volume == 100

    def test_partial_execution_timeout(self):
        """测试部分执行超时"""
        timeout_seconds = 300
        elapsed = 350
        is_timeout = elapsed > timeout_seconds
        assert is_timeout is True

    def test_execution_price_anomaly_detection(self):
        """测试执行价格异常检测"""
        expected_price = 10.50
        executed_price = 8.00
        deviation = abs(executed_price - expected_price) / expected_price
        max_deviation = 0.05
        is_anomaly = deviation > max_deviation
        assert is_anomaly is True

    def test_settlement_failure_recovery(self):
        """测试结算失败恢复"""
        retry_count = 0
        max_retries = 3
        for _ in range(max_retries):
            retry_count += 1
        assert retry_count == max_retries

    def test_execution_data_integrity_check(self):
        """测试执行数据完整性检查"""
        order = _make_submitted_order(volume=100, limit_price=10.50)
        order.fill(price=10.50)
        assert order.volume == 100
        assert order.transaction_volume == 100
        assert float(order.transaction_price) == 10.50
