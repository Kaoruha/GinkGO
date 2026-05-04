"""
性能: 210MB RSS, 1.34s, 13 tests [PASS]
"""

import pytest
from decimal import Decimal
from unittest.mock import MagicMock
from ginkgo.trading.brokers.sim_broker import SimBroker
from ginkgo.entities.order import Order
from ginkgo.enums import DIRECTION_TYPES, ORDERSTATUS_TYPES, ORDER_TYPES, ATTITUDE_TYPES

class TestSimBrokerLimitPrice:
    def test_buy_at_limit_up_should_block(self):
        broker = SimBroker()
        broker._current_market_data = {
            "000001.SZ": {
                "limit_up": Decimal("10.00"),
                "limit_down": Decimal("9.00"),
                "current_price": Decimal("10.00"),
            }
        }
        assert broker._is_limit_blocked("000001.SZ", Decimal("10.00"), "buy") is True

    def test_buy_below_limit_up_should_pass(self):
        broker = SimBroker()
        broker._current_market_data = {
            "000001.SZ": {
                "limit_up": Decimal("10.00"),
                "limit_down": Decimal("9.00"),
                "current_price": Decimal("9.50"),
            }
        }
        assert broker._is_limit_blocked("000001.SZ", Decimal("9.80"), "buy") is False

    def test_sell_at_limit_down_should_block(self):
        broker = SimBroker()
        broker._current_market_data = {
            "000001.SZ": {
                "limit_up": Decimal("10.00"),
                "limit_down": Decimal("9.00"),
                "current_price": Decimal("9.00"),
            }
        }
        assert broker._is_limit_blocked("000001.SZ", Decimal("9.00"), "sell") is True

    def test_sell_above_limit_down_should_pass(self):
        broker = SimBroker()
        broker._current_market_data = {
            "000001.SZ": {
                "limit_up": Decimal("10.00"),
                "limit_down": Decimal("9.00"),
                "current_price": Decimal("9.50"),
            }
        }
        assert broker._is_limit_blocked("000001.SZ", Decimal("9.20"), "sell") is False

    def test_buy_above_limit_up_should_block(self):
        """买入价高于涨停价也应拦截"""
        broker = SimBroker()
        broker._current_market_data = {
            "000001.SZ": {
                "limit_up": Decimal("10.00"),
                "limit_down": Decimal("9.00"),
                "current_price": Decimal("10.00"),
            }
        }
        assert broker._is_limit_blocked("000001.SZ", Decimal("10.50"), "buy") is True

    def test_sell_at_limit_up_should_pass(self):
        """涨停价卖出应通过"""
        broker = SimBroker()
        broker._current_market_data = {
            "000001.SZ": {
                "limit_up": Decimal("10.00"),
                "limit_down": Decimal("9.00"),
                "current_price": Decimal("10.00"),
            }
        }
        assert broker._is_limit_blocked("000001.SZ", Decimal("10.00"), "sell") is False

    def test_sell_below_limit_down_should_block(self):
        """卖出价低于跌停价也应拦截"""
        broker = SimBroker()
        broker._current_market_data = {
            "000001.SZ": {
                "limit_up": Decimal("10.00"),
                "limit_down": Decimal("9.00"),
                "current_price": Decimal("9.00"),
            }
        }
        assert broker._is_limit_blocked("000001.SZ", Decimal("8.50"), "sell") is True

    def test_buy_at_limit_down_should_pass(self):
        """跌停价买入应通过"""
        broker = SimBroker()
        broker._current_market_data = {
            "000001.SZ": {
                "limit_up": Decimal("10.00"),
                "limit_down": Decimal("9.00"),
                "current_price": Decimal("9.00"),
            }
        }
        assert broker._is_limit_blocked("000001.SZ", Decimal("9.00"), "buy") is False

    def test_no_market_data_should_pass(self):
        broker = SimBroker()
        assert broker._is_limit_blocked("UNKNOWN.SZ", Decimal("10.00"), "buy") is False

    def test_missing_limit_fields_should_pass(self):
        """market_data 存在但缺少 limit_up/limit_down 字段时应通过"""
        broker = SimBroker()
        broker._current_market_data = {
            "000001.SZ": {"current_price": Decimal("10.00")}
        }
        assert broker._is_limit_blocked("000001.SZ", Decimal("10.00"), "buy") is False


def _make_market_data(limit_up, limit_down, close):
    """构造满足 _is_price_valid 的最小市场数据"""
    return {
        "open": close, "high": close, "low": close,
        "close": close, "volume": 1000000,
        "limit_up": limit_up, "limit_down": limit_down,
    }


def _make_order(code, direction, limit_price):
    """构造最小化 Order 对象"""
    return Order(
        portfolio_id="p-001", engine_id="e-001", task_id="r-001",
        code=code, direction=direction,
        order_type=ORDER_TYPES.LIMITORDER, status=ORDERSTATUS_TYPES.SUBMITTED,
        volume=100, limit_price=limit_price,
    )


def _make_event(order):
    """构造带有 payload 的事件对象"""
    event = MagicMock()
    event.payload = order
    return event


class TestSimBrokerLimitPriceIntegration:
    """涨跌停拦截在 submit_order_event 完整执行流程中的集成测试"""

    def test_buy_at_limit_up_returns_canceled(self):
        """涨停价买入：submit_order_event 返回 CANCELED"""
        broker = SimBroker(attitude=ATTITUDE_TYPES.OPTIMISTIC)
        broker._current_market_data = {
            "000001.SZ": _make_market_data(
                Decimal("10.00"), Decimal("9.00"), Decimal("9.50"))
        }
        order = _make_order("000001.SZ", DIRECTION_TYPES.LONG, Decimal("10.00"))
        result = broker.submit_order_event(_make_event(order))
        assert result.status == ORDERSTATUS_TYPES.CANCELED
        assert result.error_message == "Price limit up/down"

    def test_sell_at_limit_down_returns_canceled(self):
        """跌停价卖出：submit_order_event 返回 CANCELED"""
        broker = SimBroker(attitude=ATTITUDE_TYPES.OPTIMISTIC)
        broker._current_market_data = {
            "000001.SZ": _make_market_data(
                Decimal("10.00"), Decimal("9.00"), Decimal("9.50"))
        }
        order = _make_order("000001.SZ", DIRECTION_TYPES.SHORT, Decimal("9.00"))
        result = broker.submit_order_event(_make_event(order))
        assert result.status == ORDERSTATUS_TYPES.CANCELED
        assert result.error_message == "Price limit up/down"

    def test_normal_buy_returns_filled(self):
        """正常价格买入：submit_order_event 返回 FILLED（非 CANCELED）"""
        broker = SimBroker(attitude=ATTITUDE_TYPES.OPTIMISTIC)
        broker._current_market_data = {
            "000001.SZ": _make_market_data(
                Decimal("10.00"), Decimal("9.00"), Decimal("9.50"))
        }
        order = _make_order("000001.SZ", DIRECTION_TYPES.LONG, Decimal("9.80"))
        result = broker.submit_order_event(_make_event(order))
        assert result.status != ORDERSTATUS_TYPES.CANCELED
