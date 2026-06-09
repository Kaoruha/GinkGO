"""
Tests for BrokerExecutionResult.to_event() — transaction_price/volume sync.

Broker 执行结果转事件时，应将 filled_price/filled_volume 回填到 order 对象，
否则下游报告读取 order.transaction_price 恒为 0。

Related: transaction_price=0 次生 bug
"""

import pytest
from decimal import Decimal

from ginkgo.enums import ORDERSTATUS_TYPES, DIRECTION_TYPES, ORDER_TYPES
from ginkgo.entities import Order
from ginkgo.trading.interfaces.broker_interface import BrokerExecutionResult


class TestBrokerExecutionResultTransactionPriceSync:
    """Verify that to_event() syncs order transaction fields on fill."""

    def _make_order(self, volume: int = 1000, code: str = "000004.SZ") -> Order:
        return Order(
            code=code,
            direction=DIRECTION_TYPES.LONG,
            order_type=ORDER_TYPES.MARKETORDER,
            volume=volume,
            portfolio_id="test-portfolio",
            engine_id="test-engine",
        )

    # ---- TDD RED: 以下测试当前应失败 ----

    def test_filled_order_transaction_price_synced(self):
        """to_event() 应将 filled_price 回填到 order.transaction_price"""
        order = self._make_order(volume=1000)
        assert order.transaction_price == 0, "precondition: price starts at 0"

        result = BrokerExecutionResult(
            status=ORDERSTATUS_TYPES.FILLED,
            filled_volume=1000,
            filled_price=16.57,
            commission=5.0,
            order=order,
        )
        event = result.to_event(engine_id="test-engine", task_id="test-task")

        assert event is not None
        assert order.transaction_price == Decimal("16.57"), (
            f"order.transaction_price should be 16.57, got {order.transaction_price}"
        )
        assert order.transaction_volume == 1000, (
            f"order.transaction_volume should be 1000, got {order.transaction_volume}"
        )

    def test_partial_fill_transaction_price_synced(self):
        """部分成交也应回填 transaction_price/volume"""
        order = self._make_order(volume=2000)

        result = BrokerExecutionResult(
            status=ORDERSTATUS_TYPES.PARTIAL_FILLED,
            filled_volume=500,
            filled_price=17.82,
            commission=2.5,
            order=order,
        )
        event = result.to_event(engine_id="test-engine", task_id="test-task")

        assert event is not None
        assert order.transaction_price == Decimal("17.82"), (
            f"order.transaction_price should be 17.82, got {order.transaction_price}"
        )
        assert order.transaction_volume == 500, (
            f"order.transaction_volume should be 500, got {order.transaction_volume}"
        )

    def test_submitted_does_not_touch_transaction_price(self):
        """SUBMITTED 状态不应修改 order transaction 字段"""
        order = self._make_order()

        result = BrokerExecutionResult(
            status=ORDERSTATUS_TYPES.SUBMITTED,
            broker_order_id="broker-123",
            order=order,
        )
        result.to_event(engine_id="test-engine", task_id="test-task")

        assert order.transaction_price == 0
        assert order.transaction_volume == 0
