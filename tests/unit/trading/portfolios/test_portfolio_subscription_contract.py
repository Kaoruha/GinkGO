"""
Portfolio 类族事件订阅契约测试（ADR-017 迁移 #12）

验证三类 _subscriptions 映射，对照 tce:798-816 component_event_mapping 的旧类名注册表：
  - PortfolioBase：4 核心抽象 handler 声明类族契约（PRICEUPDATE/SIGNAL/ORDERPARTIALLYFILLED/ORDERCANCELACK）
  - PortfolioT1Backtest：继承 Base 4 个 + 自己加 4 个
    （on_order_filled/on_position_update/on_capital_update/on_portfolio_update）
  - PortfolioLive：换映射（PRICEUPDATE→on_price_update，方法名漂移）+
    一方法多 event（ORDERFILLED+ORDERPARTIALLYFILLED→on_order_partially_filled，取代转发壳）+
    继承 Base signal/cancel_ack

_subscriptions 是类属性（__init_subclass__ 在类创建期生成），无需实例化 Portfolio，
import 类即可断言 —— 避开 Portfolio 重型依赖（notification_service/analyzers/context）。
"""

from ginkgo.enums import EVENT_TYPES
from ginkgo.trading.bases.portfolio_base import PortfolioBase
from ginkgo.trading.portfolios.t1backtest import PortfolioT1Backtest
from ginkgo.trading.portfolios.portfolio_live import PortfolioLive


class TestPortfolioBaseSubscriptionContract:
    """PortfolioBase 直接订阅 3 事件（对照 tce:771-772 + engine_assembly:714 manual register）

    ORDERPARTIALLYFILLED 不在此列：回测路径经 TradeGateway.on_order_partially_filled
    路由器按 portfolio_id 转发调用 Portfolio.on_order_partially_filled（方法调用，
    非引擎订阅）。若 Portfolio 直接订阅，引擎触发 + Gateway 路由 = 双重处理。
    on_order_partially_filled 仍是抽象方法，约束子类实现以供 Gateway 路由调用。
    """

    def test_base_declares_three_direct_subscriptions(self):
        s = PortfolioBase._subscriptions
        assert s[EVENT_TYPES.PRICEUPDATE] == "on_price_received"
        assert s[EVENT_TYPES.SIGNALGENERATION] == "on_signal"
        assert s[EVENT_TYPES.ORDERCANCELACK] == "on_order_cancel_ack"
        # ORDERPARTIALLYFILLED 通过 Gateway 路由，Portfolio 不直接订阅
        assert EVENT_TYPES.ORDERPARTIALLYFILLED not in s


class TestT1BacktestSubscriptionContract:
    """T1Backtest 继承 Base 3 直接订阅 + 自己加 ORDERFILLED（对照 tce:770-777）"""

    def test_t1_inherits_base_three_direct(self):
        s = PortfolioT1Backtest._subscriptions
        assert s[EVENT_TYPES.PRICEUPDATE] == "on_price_received"
        assert s[EVENT_TYPES.SIGNALGENERATION] == "on_signal"
        assert s[EVENT_TYPES.ORDERCANCELACK] == "on_order_cancel_ack"
        assert EVENT_TYPES.ORDERPARTIALLYFILLED not in s  # Gateway 路由

    def test_t1_adds_order_filled_subscription(self):
        """T1Backtest 只额外加 on_order_filled。

        POSITIONUPDATE/CAPITALUPDATE/PORTFOLIOUPDATE 在旧 tce:798-807 注册表写了，
        但 T1Backtest 无此方法（hasattr False，死注册），迁移后不应出现幽灵映射。
        """
        s = PortfolioT1Backtest._subscriptions
        assert s[EVENT_TYPES.ORDERFILLED] == "on_order_filled"
        assert EVENT_TYPES.POSITIONUPDATE not in s
        assert EVENT_TYPES.CAPITALUPDATE not in s
        assert EVENT_TYPES.PORTFOLIOUPDATE not in s


class TestPortfolioLiveSubscriptionContract:
    """PortfolioLive：换映射 + 一方法多 event + 继承（取代旧类名注册缺失 + 转发壳）"""

    def test_live_remaps_priceupdate_to_on_price_update(self):
        """方法名漂移：on_price_update 覆盖父类 on_price_received 映射（B2 换映射免费）"""
        s = PortfolioLive._subscriptions
        assert s[EVENT_TYPES.PRICEUPDATE] == "on_price_update"

    def test_live_one_method_many_events_for_order_filled(self):
        """on_order_partially_filled 同时订阅 PARTIALLY_FILLED + FILLED（取代 :383 转发壳）"""
        s = PortfolioLive._subscriptions
        assert s[EVENT_TYPES.ORDERPARTIALLYFILLED] == "on_order_partially_filled"
        assert s[EVENT_TYPES.ORDERFILLED] == "on_order_partially_filled"

    def test_live_inherits_signal_and_cancel_ack(self):
        """继承 Base 的 signal/cancel_ack（同名 override，不需重标）"""
        s = PortfolioLive._subscriptions
        assert s[EVENT_TYPES.SIGNALGENERATION] == "on_signal"
        assert s[EVENT_TYPES.ORDERCANCELACK] == "on_order_cancel_ack"
