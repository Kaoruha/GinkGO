"""
BacktestFeeder + TradeGateway 事件订阅契约测试（ADR-017 迁移 #13）

对照 tce:778-785 component_event_mapping：
  - BacktestFeeder: INTERESTUPDATE→on_interest_update
  - TradeGateway: PRICEUPDATE→on_price_received、ORDERACK→on_order_ack、
                  ORDERPARTIALLYFILLED→on_order_partially_filled（路由器，按 portfolio_id 转发）

_subscriptions 是类属性（__init_subclass__ 在类创建期生成），import 类即可断言，
无需实例化 —— 避开 Broker/Router/数据源重依赖。
"""

from ginkgo.enums import EVENT_TYPES
from ginkgo.trading.feeders.backtest_feeder import BacktestFeeder
from ginkgo.trading.gateway.trade_gateway import TradeGateway


class TestBacktestFeederSubscriptionContract:
    """BacktestFeeder 订阅利息更新（对照 tce:780）"""

    def test_feeder_subscribes_interest_update(self):
        s = BacktestFeeder._subscriptions
        assert s[EVENT_TYPES.INTERESTUPDATE] == "on_interest_update"


class TestTradeGatewaySubscriptionContract:
    """TradeGateway 路由器订阅 3 事件（对照 tce:783-785）"""

    def test_gateway_subscribes_price_update(self):
        """PRICEUPDATE→on_price_received：更新 Broker 市场数据缓存（处理器，非路由）"""
        assert TradeGateway._subscriptions[EVENT_TYPES.PRICEUPDATE] == "on_price_received"

    def test_gateway_subscribes_order_ack(self):
        """ORDERACK→on_order_ack：记录订单确认 + 选 Broker 执行（处理器）"""
        assert TradeGateway._subscriptions[EVENT_TYPES.ORDERACK] == "on_order_ack"

    def test_gateway_subscribes_order_partially_filled(self):
        """ORDERPARTIALLYFILLED→on_order_partially_filled：按 portfolio_id 路由到 Portfolio"""
        assert (
            TradeGateway._subscriptions[EVENT_TYPES.ORDERPARTIALLYFILLED]
            == "on_order_partially_filled"
        )
