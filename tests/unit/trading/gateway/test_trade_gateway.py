"""
TradeGateway 单元测试

TDD 覆盖：初始化、订单路由、基础校验、同步/异步执行、超时检测
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime, timedelta

from ginkgo.trading.gateway.trade_gateway import TradeGateway
from ginkgo.trading.brokers.base_broker import BaseBroker
from ginkgo.entities import Order
from ginkgo.enums import ORDERSTATUS_TYPES, DIRECTION_TYPES, ORDER_TYPES, EVENT_TYPES


class StubBroker(BaseBroker):
    """测试用 Broker 桩，满足 isinstance 检查（#6715：继承强侧 BaseBroker）"""
    def __init__(self, market: str = "SIM"):
        super().__init__({})
        self.market = market
        self._result_callback = None
        self._submit_calls = []
        self._cancel_calls = []
        self._connected = True
        self._validate_ok = True
        self._immediate = (market == "SIM")
        self._manual_confirm = False

    def set_result_callback(self, cb):
        self._result_callback = cb

    def supports_immediate_execution(self):
        return self._immediate

    def requires_manual_confirmation(self):
        return self._manual_confirm

    def validate_order(self, order):
        return self._validate_ok

    def is_connected(self):
        return self._connected

    def submit_order_event(self, event):
        self._submit_calls.append(event)
        return Mock(status=ORDERSTATUS_TYPES.SUBMITTED, broker_order_id="stub-123")

    def cancel_order(self, broker_order_id):
        self._cancel_calls.append(broker_order_id)
        return Mock(status=ORDERSTATUS_TYPES.CANCELED)


def make_mock_broker(market: str = "SIM", connected: bool = True) -> StubBroker:
    return StubBroker(market=market)


def make_order(code: str = "000001.SZ", direction=DIRECTION_TYPES.LONG, volume: int = 100) -> Order:
    """创建测试订单"""
    order = Mock(spec=Order)
    order.uuid = "test-order-uuid-1234"
    order.code = code
    order.direction = direction
    order.volume = volume
    order.order_type = ORDER_TYPES.MARKETORDER
    order.price = None
    return order


class TestTradeGatewayInit:
    """初始化行为"""

    def test_single_broker_wrapped_in_list(self):
        broker = make_mock_broker("SIM")
        gw = TradeGateway(brokers=broker, name="test-gw")
        assert len(gw.brokers) == 1
        assert gw.broker is broker

    def test_multiple_brokers(self):
        b1 = make_mock_broker("SIM")
        b2 = make_mock_broker("A股")
        gw = TradeGateway(brokers=[b1, b2], name="test-gw")
        assert len(gw.brokers) == 2

    def test_invalid_brokers_raises(self):
        with pytest.raises(ValueError, match="brokers must be"):
            TradeGateway(brokers="not_a_broker", name="test-gw")

    def test_sim_broker_as_default_for_all_markets(self):
        sim = make_mock_broker("SIM")
        gw = TradeGateway(brokers=sim, name="test-gw")
        assert gw._market_mapping.get("A股") is sim
        assert gw._market_mapping.get("美股") is sim
        assert gw._market_mapping.get("Crypto") is sim

    def test_dedicated_market_takes_priority_over_sim(self):
        sim = make_mock_broker("SIM")
        a_stock = make_mock_broker("A股")
        gw = TradeGateway(brokers=[sim, a_stock], name="test-gw")
        assert gw._market_mapping["A股"] is a_stock
        assert gw._market_mapping["美股"] is sim


class TestGetMarketByCode:
    """市场代码解析"""

    @pytest.fixture
    def gw(self):
        return TradeGateway(brokers=make_mock_broker("SIM"), name="test")

    def test_a_stock_sz(self, gw):
        assert gw._get_market_by_code("000001.SZ") == "A股"

    def test_a_stock_sh(self, gw):
        assert gw._get_market_by_code("600000.SH") == "A股"

    def test_hk_stock(self, gw):
        assert gw._get_market_by_code("00700.HK") == "港股"

    def test_us_stock(self, gw):
        assert gw._get_market_by_code("AAPL") == "美股"

    def test_crypto(self, gw):
        assert gw._get_market_by_code("BTC/USDT") == "Crypto"

    def test_futures(self, gw):
        assert gw._get_market_by_code("IF2506") == "期货"

    def test_empty_code_defaults_a_stock(self, gw):
        assert gw._get_market_by_code("") == "A股"

    def test_unknown_code_defaults_a_stock(self, gw):
        assert gw._get_market_by_code("UNKNOWN") == "A股"


class TestGetBrokerForOrder:
    """订单路由"""

    def test_routes_a_stock_to_correct_broker(self):
        a_broker = make_mock_broker("A股")
        gw = TradeGateway(brokers=a_broker, name="test")
        order = make_order("000001.SZ")
        assert gw.get_broker_for_order(order) is a_broker

    def test_routes_crypto_to_correct_broker(self):
        crypto_broker = make_mock_broker("Crypto")
        gw = TradeGateway(brokers=crypto_broker, name="test")
        order = make_order("BTC/USDT")
        assert gw.get_broker_for_order(order) is crypto_broker

    def test_falls_back_to_sim_broker(self):
        sim = make_mock_broker("SIM")
        gw = TradeGateway(brokers=sim, name="test")
        order = make_order("000001.SZ")
        assert gw.get_broker_for_order(order) is sim

    def test_returns_none_when_no_broker_for_market(self):
        """只有 A股 broker，但下单美股 → 无匹配"""
        a_broker = make_mock_broker("A股")
        gw = TradeGateway(brokers=a_broker, name="test")
        order = make_order("AAPL")
        assert gw.get_broker_for_order(order) is None


class TestValidateOrderBasic:
    """基础订单校验"""

    @pytest.fixture
    def gw(self):
        return TradeGateway(brokers=make_mock_broker("SIM"), name="test")

    def test_valid_order(self, gw):
        order = make_order()
        assert gw._validate_order_basic(order) is True

    def test_reject_none_order(self, gw):
        assert gw._validate_order_basic(None) is False

    def test_reject_order_without_uuid(self, gw):
        order = Mock(spec=Order)
        del order.uuid
        order.code = "000001.SZ"
        order.volume = 100
        assert gw._validate_order_basic(order) is False

    def test_reject_empty_code(self, gw):
        order = make_order()
        order.code = ""
        assert gw._validate_order_basic(order) is False

    def test_reject_zero_volume(self, gw):
        order = make_order()
        order.volume = 0
        assert gw._validate_order_basic(order) is False

    def test_reject_negative_volume(self, gw):
        order = make_order()
        order.volume = -1
        assert gw._validate_order_basic(order) is False


class TestOnOrderAckSyncExecution:
    """同步执行路径（回测模式）"""

    @pytest.fixture
    def gw(self):
        broker = make_mock_broker("SIM")
        gw = TradeGateway(brokers=broker, name="test")
        gw.set_event_publisher(Mock())
        return gw

    def _make_ack_event(self, order):
        event = Mock()
        event.payload = order
        event.broker_order_id = "broker-123"
        event.ack_message = "ACK"
        event.portfolio_id = "test-portfolio"
        return event

    def test_sync_submission_updates_order_status(self, gw):
        order = make_order()
        event = self._make_ack_event(order)
        gw.on_order_ack(event)
        assert len(gw.brokers[0]._submit_calls) == 1

    def test_rejects_invalid_order(self, gw):
        order = Mock(spec=Order)
        order.code = ""
        order.volume = 100
        order.uuid = "bad-order"
        event = self._make_ack_event(order)
        gw.on_order_ack(event)
        assert len(gw.brokers[0]._submit_calls) == 0

    def test_rejects_when_no_broker_matches(self, gw):
        """SIM broker 只覆盖默认市场，code 无法匹配时仍走 SIM"""
        # 极端情况：去掉 SIM 的默认映射
        gw._market_mapping.clear()
        order = make_order("UNKNOWN.CODE")
        event = self._make_ack_event(order)
        gw.on_order_ack(event)
        assert len(gw.brokers[0]._submit_calls) == 0


class TestHandleAsyncResult:
    """异步执行结果处理"""

    @pytest.fixture
    def gw(self):
        broker = make_mock_broker("Crypto")
        gw = TradeGateway(brokers=broker, name="test")
        gw.set_event_publisher(Mock())
        return gw

    def test_ignores_unknown_order(self, gw):
        result = Mock()
        result.broker_order_id = "unknown-123"
        result.status = ORDERSTATUS_TYPES.FILLED
        gw._handle_async_result(result)
        # 不应崩溃

    def test_processes_filled_result(self, gw):
        order = make_order("BTC/USDT")
        broker = gw.brokers[0]
        gw.track_order("broker-456", {
            "order": order,
            "broker": broker,
            "submit_time": datetime.now(),
            "execution_mode": "live",
        })
        result = Mock()
        result.broker_order_id = "broker-456"
        result.status = ORDERSTATUS_TYPES.FILLED
        result.filled_volume = 0.01
        result.filled_price = 50000.0
        result.error_message = None
        with patch.object(gw, '_handle_execution_result'):
            gw._handle_async_result(result)
        # 订单应从跟踪中移除
        assert gw.get_tracked_order("broker-456") is None


class TestCheckOrderTimeouts:
    """超时检测"""

    @pytest.fixture
    def gw(self):
        broker = make_mock_broker("SIM")
        gw = TradeGateway(brokers=broker, name="test")
        gw.set_event_publisher(Mock())
        return gw

    def test_detects_timed_out_order(self, gw):
        order = make_order()
        old_time = datetime.now() - timedelta(seconds=600)
        gw.track_order("timeout-001", {
            "order": order,
            "broker": gw.brokers[0],
            "submit_time": old_time,
            "timeout_seconds": 300,
        })
        timed_out = gw.check_order_timeouts()
        assert "timeout-001" in timed_out

    def test_no_timeout_for_recent_order(self, gw):
        order = make_order()
        gw.track_order("fresh-001", {
            "order": order,
            "broker": gw.brokers[0],
            "submit_time": datetime.now(),
            "timeout_seconds": 300,
        })
        timed_out = gw.check_order_timeouts()
        assert "fresh-001" not in timed_out


class TestSaveSubmittedOrderRecordFrozen:
    """
    _save_submitted_order_record 冻结字段传递 (#6056 frozen 拆分后)

    #6056 将 Order.frozen 拆分为 frozen_money + frozen_volume，
    OrderRecordCRUD.create_order_record 现在读 frozen_money/frozen_volume kwargs。
    trade_gateway 必须传对 kwarg 名，否则冻结金额静默写 0。
    """
    from decimal import Decimal

    @pytest.fixture
    def gw_with_engine(self):
        broker = make_mock_broker("SIM")
        gw = TradeGateway(brokers=broker, name="test")
        engine = Mock()
        engine.engine_id = "engine-uuid-1"
        engine.task_id = "task-uuid-1"
        gw._bound_engine = engine
        gw.set_event_publisher(Mock())
        return gw

    def test_passes_frozen_money_and_volume_not_frozen_kwarg(self, gw_with_engine):
        """SUBMITTED 记录必须传 frozen_money/frozen_volume，禁止残留 frozen= kwarg"""
        from ginkgo.data.containers import container

        order = make_order()
        order.frozen_money = self.Decimal("15000")
        order.frozen_volume = 500
        order.limit_price = self.Decimal("20")
        order.timestamp = datetime.now()
        order.business_timestamp = order.timestamp

        event = Mock()
        event.portfolio_id = "portfolio-uuid-1"

        mock_service = Mock()
        with patch.object(container, "result_service", return_value=mock_service):
            gw_with_engine._save_submitted_order_record(order, event)

        mock_service.create_order_record.assert_called_once()
        kwargs = mock_service.create_order_record.call_args.kwargs
        assert "frozen" not in kwargs, (
            "不应再用 frozen= kwarg (#6056 拆分后改用 frozen_money/frozen_volume)"
        )
        assert kwargs.get("frozen_money") == self.Decimal("15000"), (
            f"frozen_money 未正确传递: {kwargs}"
        )
        assert kwargs.get("frozen_volume") == 500, (
            f"frozen_volume 未正确传递: {kwargs}"
        )
