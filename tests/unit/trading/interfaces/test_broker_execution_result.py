"""
BrokerExecutionResult.to_event() 测试 - 覆盖 FILLED→ORDERFILLED 事件类型映射

测试范围:
1. FILLED 状态生成 ORDERFILLED 类型事件
2. PARTIAL_FILLED 状态生成 ORDERPARTIALLYFILLED 类型事件
3. REJECTED 状态生成 EventOrderRejected
4. SUBMITTED 状态生成 EventOrderAck
5. 无 order 时返回 None
"""
import sys
import os
_path = os.path.join(os.path.dirname(__file__), '..', '..', '..')
if _path not in sys.path:
    sys.path.insert(0, _path)

from decimal import Decimal
import pytest

from ginkgo.trading.interfaces.broker_interface import BrokerExecutionResult
from ginkgo.entities import Order
from ginkgo.enums import ORDERSTATUS_TYPES, EVENT_TYPES, DIRECTION_TYPES, ORDER_TYPES


class TestBrokerExecutionResultToEvent:
    """BrokerExecutionResult.to_event() 事件类型映射测试"""

    def _make_order(self):
        return Order(
            portfolio_id="portfolio-001",
            engine_id="engine-1",
            task_id="run-1",
            code="000001.SZ",
            direction=DIRECTION_TYPES.LONG,
            order_type=ORDER_TYPES.MARKETORDER,
            status=ORDERSTATUS_TYPES.NEW,
            volume=100,
            limit_price=Decimal("10.00"),
        )

    def test_filled_maps_to_orderfilled_event_type(self):
        """FILLED 状态应生成 ORDERFILLED 事件类型"""
        result = BrokerExecutionResult(
            status=ORDERSTATUS_TYPES.FILLED,
            broker_order_id="BROKER-001",
            filled_volume=100,
            filled_price=10.5,
            order=self._make_order()
        )
        event = result.to_event(engine_id="engine-1", task_id="run-1")
        assert event is not None
        assert event.event_type == EVENT_TYPES.ORDERFILLED

    def test_partial_filled_maps_to_orderpartiallyfilled(self):
        """PARTIAL_FILLED 状态应生成 ORDERPARTIALLYFILLED 事件类型"""
        result = BrokerExecutionResult(
            status=ORDERSTATUS_TYPES.PARTIAL_FILLED,
            broker_order_id="BROKER-002",
            filled_volume=50,
            filled_price=10.5,
            order=self._make_order()
        )
        event = result.to_event(engine_id="engine-1", task_id="run-1")
        assert event is not None
        assert event.event_type == EVENT_TYPES.ORDERPARTIALLYFILLED

    def test_rejected_maps_to_orderrejected(self):
        """REJECTED 状态应生成 EventOrderRejected"""
        result = BrokerExecutionResult(
            status=ORDERSTATUS_TYPES.REJECTED,
            error_message="Insufficient funds",
            order=self._make_order()
        )
        event = result.to_event(engine_id="engine-1", task_id="run-1")
        assert event is not None
        assert event.event_type == EVENT_TYPES.ORDERREJECTED

    def test_submitted_maps_to_orderack(self):
        """SUBMITTED 状态应生成 EventOrderAck"""
        result = BrokerExecutionResult(
            status=ORDERSTATUS_TYPES.SUBMITTED,
            broker_order_id="BROKER-003",
            order=self._make_order()
        )
        event = result.to_event(engine_id="engine-1", task_id="run-1")
        assert event is not None
        assert event.event_type == EVENT_TYPES.ORDERACK

    def test_canceled_maps_to_ordercancelack(self):
        """CANCELED 状态应生成 EventOrderCancelAck"""
        result = BrokerExecutionResult(
            status=ORDERSTATUS_TYPES.CANCELED,
            filled_volume=0,
            order=self._make_order()
        )
        event = result.to_event(engine_id="engine-1", task_id="run-1")
        assert event is not None
        assert event.event_type == EVENT_TYPES.ORDERCANCELACK

    def test_no_order_returns_none(self):
        """无 order 时返回 None"""
        result = BrokerExecutionResult(
            status=ORDERSTATUS_TYPES.FILLED,
            filled_volume=100,
        )
        assert result.to_event() is None

    def test_filled_event_has_correct_payload(self):
        """FILLED 事件包含正确的成交信息"""
        order = self._make_order()
        result = BrokerExecutionResult(
            status=ORDERSTATUS_TYPES.FILLED,
            broker_order_id="BROKER-004",
            filled_volume=200,
            filled_price=15.75,
            commission=2.5,
            trade_id="TRADE-001",
            order=order
        )
        event = result.to_event(engine_id="engine-1", task_id="run-1")
        assert event.filled_quantity == 200
        assert event.fill_price == 15.75
        assert event.commission == 2.5
        assert event.trade_id == "TRADE-001"

    def test_unknown_status_returns_none(self):
        """未知状态返回 None"""
        result = BrokerExecutionResult(
            status=ORDERSTATUS_TYPES.NEW,
            order=self._make_order()
        )
        assert result.to_event() is None

    def test_filled_partial_fill_propagates_status_to_event(self):
        """FILLED 终态(部分成交 filled_volume<volume)必须透传到 event.order_status (#5492 review)

        下游 PortfolioT1Backtest.is_final 依赖 event.order_status==FILLED 判定终态,
        据此释放剩余冻结资金 (release_frozen)。回测路径从不调 order.fill(),
        order.status 恒为 SUBMITTED; 若 to_event 不透传 result.status,
        部分成交(order.transaction_volume<volume)时 is_final=False,
        剩余 frozen_money 永久泄漏、cash 被低估。
        broker 的 result.status 是订单终态的权威来源, 必须随事件透传。
        """
        order = Order(
            portfolio_id="portfolio-001", engine_id="engine-1", task_id="run-1",
            code="000001.SZ", direction=DIRECTION_TYPES.LONG,
            order_type=ORDER_TYPES.MARKETORDER, status=ORDERSTATUS_TYPES.SUBMITTED,
            volume=1000, frozen_money=Decimal("5000"),
        )
        # broker 一次性部分成交: 判定终态 FILLED, 但实际只成交 400 < volume 1000
        result = BrokerExecutionResult(
            status=ORDERSTATUS_TYPES.FILLED,
            broker_order_id="BROKER-PARTIAL",
            filled_volume=400,
            filled_price=10.0,
            order=order,
        )
        event = result.to_event(engine_id="engine-1", task_id="run-1")
        assert event is not None
        assert event.event_type == EVENT_TYPES.ORDERFILLED
        # 关键: 事件须透传 broker 终态判定, 而非退回 order.status(=SUBMITTED)
        assert event.order_status == ORDERSTATUS_TYPES.FILLED
