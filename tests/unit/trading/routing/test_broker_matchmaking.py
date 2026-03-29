"""
BrokerMatchMaking 订单路由单元测试

测试 SimBroker 和 TradeGateway 的订单路由、撮合和执行结果
"""
import pytest
from datetime import datetime
from decimal import Decimal
from unittest.mock import MagicMock

from ginkgo.trading.brokers.sim_broker import SimBroker
from ginkgo.trading.gateway.trade_gateway import TradeGateway
from ginkgo.entities.order import Order
from ginkgo.enums import (
    DIRECTION_TYPES, ORDER_TYPES, ORDERSTATUS_TYPES, ATTITUDE_TYPES,
)
from ginkgo.trading.interfaces.broker_interface import BrokerExecutionResult


def _make_order(code="000001.SZ", volume=100, direction=DIRECTION_TYPES.LONG,
                limit_price=Decimal("10.00")):
    """构造最小化真实 Order 对象"""
    return Order(
        portfolio_id="p-001", engine_id="e-001", run_id="r-001",
        code=code, direction=direction,
        order_type=ORDER_TYPES.LIMITORDER, status=ORDERSTATUS_TYPES.SUBMITTED,
        volume=volume, limit_price=limit_price,
    )


def _make_event(order):
    """构造事件对象"""
    event = MagicMock()
    event.payload = order
    event.portfolio_id = "p-001"
    return event


def _make_market_data(close):
    """构造满足 SimBroker 验证的最小市场数据"""
    return {
        "open": close, "high": close, "low": close,
        "close": close, "volume": 1000000,
    }


def _submit(broker, code="000001.SZ", volume=100, direction=DIRECTION_TYPES.LONG,
            limit_price=Decimal("10.00"), set_price=None):
    """快捷方法：创建 order + event 并提交"""
    order = _make_order(code=code, volume=volume, direction=direction,
                        limit_price=limit_price)
    event = _make_event(order)
    if set_price is not None:
        broker.set_market_data(code, _make_market_data(set_price))
    return broker.submit_order_event(event)


@pytest.mark.unit
class TestBrokerConstruction:
    """SimBroker 构造和属性"""

    def test_default_broker_name(self):
        broker = SimBroker(name="TestBroker")
        assert broker.name == "TestBroker"

    def test_default_market(self):
        broker = SimBroker(name="SimBroker")
        assert broker.market == "SIM"

    def test_gateway_holds_brokers(self):
        broker = SimBroker(name="SimBroker")
        gateway = TradeGateway(brokers=[broker])
        assert len(gateway.brokers) == 1
        assert gateway.brokers[0].name == "SimBroker"

    def test_gateway_multiple_brokers(self):
        gateway = TradeGateway(brokers=[
            SimBroker(name="B1"), SimBroker(name="B2")
        ])
        assert len(gateway.brokers) == 2

    def test_submit_order_event_is_callable(self):
        """submit_order_event 方法可调用"""
        broker = SimBroker(name="SimBroker")
        assert callable(broker.submit_order_event)


@pytest.mark.unit
class TestSimBrokerExecution:
    """SimBroker 订单执行结果验证"""

    def test_submit_returns_broker_execution_result(self):
        """提交订单返回 BrokerExecutionResult"""
        broker = SimBroker(name="SimBroker")
        result = _submit(broker, set_price="10.00")
        assert isinstance(result, BrokerExecutionResult)

    def test_filled_with_market_data(self):
        """有市场价格时订单应成交"""
        broker = SimBroker(name="SimBroker", attitude=ATTITUDE_TYPES.OPTIMISTIC)
        result = _submit(broker, set_price="10.00")
        assert result.status == ORDERSTATUS_TYPES.FILLED
        assert result.filled_volume == 100
        assert result.filled_price > 0

    def test_filled_price_matches_market(self):
        """成交价应等于市场价格"""
        broker = SimBroker(name="SimBroker", attitude=ATTITUDE_TYPES.OPTIMISTIC)
        result = _submit(broker, limit_price=Decimal("10.00"), set_price="10.00")
        assert result.filled_price == Decimal("10.00")

    def test_commission_calculated(self):
        """手续费应正确计算"""
        broker = SimBroker(name="SimBroker", attitude=ATTITUDE_TYPES.OPTIMISTIC)
        result = _submit(broker, volume=100, set_price="10.00")
        assert result.commission > 0

    def test_commission_min(self):
        """手续费有最低限制"""
        broker = SimBroker(name="SimBroker", config={"commission_rate": 0.0003, "commission_min": 5})
        assert broker._commission_rate == Decimal("0.0003")
        assert broker._commission_min == 5

    def test_no_market_data_returns_status(self):
        """无市场价格时仍返回结果（不会崩溃）"""
        broker = SimBroker(name="SimBroker")
        result = _submit(broker, set_price=None)
        assert isinstance(result, BrokerExecutionResult)

    def test_multiple_orders_sequential(self):
        """连续提交多个订单"""
        broker = SimBroker(name="SimBroker", attitude=ATTITUDE_TYPES.OPTIMISTIC)
        r1 = _submit(broker, code="000001.SZ", set_price="10.00")
        r2 = _submit(broker, code="000002.SZ", set_price="20.00")
        assert isinstance(r1, BrokerExecutionResult)
        assert isinstance(r2, BrokerExecutionResult)

    def test_sell_order_execution(self):
        """卖出订单执行"""
        broker = SimBroker(name="SimBroker", attitude=ATTITUDE_TYPES.OPTIMISTIC)
        result = _submit(broker, direction=DIRECTION_TYPES.SHORT, set_price="10.00")
        assert isinstance(result, BrokerExecutionResult)


@pytest.mark.unit
class TestSimBrokerExecutionMode:
    """执行模式检测"""

    def test_supports_immediate_execution(self):
        broker = SimBroker(name="SimBroker")
        assert broker.supports_immediate_execution() is True

    def test_does_not_support_api_trading(self):
        broker = SimBroker(name="SimBroker")
        assert broker.supports_api_trading() is False

    def test_does_not_require_manual_confirmation(self):
        broker = SimBroker(name="SimBroker")
        assert broker.requires_manual_confirmation() is False


@pytest.mark.unit
class TestTradeGateway:
    """TradeGateway 路由测试"""

    def test_gateway_routes_to_default_broker(self):
        """Gateway 有默认 broker 可用于路由"""
        broker = SimBroker(name="SimBroker", attitude=ATTITUDE_TYPES.OPTIMISTIC)
        gateway = TradeGateway(brokers=[broker])
        order = _make_order()
        routed = gateway.get_broker_for_order(order)
        assert routed is not None

    def test_gateway_broker_identity(self):
        """Gateway 中的 broker 是同一实例"""
        broker = SimBroker(name="SimBroker")
        gateway = TradeGateway(brokers=[broker])
        assert gateway.brokers[0] is broker


@pytest.mark.unit
class TestBrokerInfo:
    """Broker 信息获取"""

    def test_info_contains_name(self):
        broker = SimBroker(name="MyBroker")
        info = broker.get_broker_info()
        assert info["name"] == "MyBroker"

    def test_info_contains_position_count(self):
        broker = SimBroker(name="SimBroker")
        info = broker.get_broker_info()
        assert "position_count" in info
        assert isinstance(info["position_count"], int)


@pytest.mark.unit
class TestPriceData:
    """价格数据管理"""

    def test_set_market_data(self):
        broker = SimBroker(name="SimBroker")
        broker.set_market_data("000001.SZ", {"close": "10.00"})
        # 不崩溃即可

    def test_set_multiple_stocks(self):
        broker = SimBroker(name="SimBroker")
        broker.set_market_data("000001.SZ", {"close": "10.00"})
        broker.set_market_data("600036.SH", {"close": "35.00"})
