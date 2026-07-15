# #3844: ContextMixin.__init__ 调用签名错误导致 TypeError
# 验证所有 mixin 链末端都有 Base 兜底，未知 kwargs 不会导致 object.__init__() 报错
import pytest

from ginkgo.trading.events.base_event import EventBase
from ginkgo.trading.events.price_update import EventPriceUpdate
from ginkgo.trading.bases.broker_cache_mixin import BrokerCacheMixin
from ginkgo.trading.bases.base_trade_gateway import BaseTradeGateway
from ginkgo.entities.base import Base


class TestMixinChainSink:
    """Mixin 链末端兜底：所有使用 mixin 的类都应以 Base 结尾，不让 mixin 直接碰到 object"""

    def test_eventbase_has_base_in_mro(self):
        """EventBase 的 MRO 中应包含 Base"""
        assert Base in EventBase.__mro__

    def test_base_broker_has_base_in_mro(self):
        """BrokerCacheMixin 的 MRO 中应包含 Base（#6715：原 BaseBroker 弱侧降级为 Mixin）"""
        assert Base in BrokerCacheMixin.__mro__

    def test_base_trade_gateway_has_base_in_mro(self):
        """BaseTradeGateway 的 MRO 中应包含 Base"""
        assert Base in BaseTradeGateway.__mro__

    def test_eventbase_with_unknown_kwargs_no_error(self):
        """EventBase 子类传入未知 kwargs 不应 TypeError"""
        # timestamp 是 TimeMixin 的 property，不是 __init__ 参数
        # 以前会流到 object.__init__() 导致 TypeError
        e = EventPriceUpdate(timestamp="2024-01-01")
        assert e is not None

    def test_eventbase_with_multiple_unknown_kwargs(self):
        """多个未知 kwargs 也不报错"""
        e = EventPriceUpdate(timestamp="2024-01-01", code="000001.SZ", extra=42)
        assert e is not None

    def test_base_broker_with_unknown_kwargs(self):
        """BrokerCacheMixin 传入未知 kwargs 不应 TypeError（#6715：原 BaseBroker 弱侧）"""
        b = BrokerCacheMixin(name="test", extra_param="value")
        assert b is not None

    def test_base_trade_gateway_with_unknown_kwargs(self):
        """BaseTradeGateway 传入未知 kwargs 不应 TypeError"""
        g = BaseTradeGateway(name="test", extra_param="value")
        assert g is not None

    def test_eventbase_normal_init_still_works(self):
        """EventBase 正常初始化仍可用"""
        e = EventPriceUpdate()
        assert e._uuid is not None
        assert isinstance(e._uuid, str)
