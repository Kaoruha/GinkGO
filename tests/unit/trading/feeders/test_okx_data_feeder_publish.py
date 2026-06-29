"""
OKXDataFeeder 端到端：独立根装 EngineBindableMixin+FeederPublishMixin 后 MRO 通。

验证关键点（ADR-019 Consequences）：
- 独立根 __init__ 缺 super()：补 super().__init__() 触发 mixin 链
- set_event_publisher 删 override 后走 EngineBindableMixin（注入 _engine_put）
- _publish_event wrapper 删除后被 publish_price_update（E1 三态契约）取代
- OKX 无自有 stats（独立根未自建），mixin stats 直接可用

桩用 __abstractmethods__ = frozenset() 绕过 ILiveDataFeeder ABC；
patch OKXMarketDataFeeder 避免 __init__ 实例化真实 REST 适配器（网络）。
"""
from unittest.mock import Mock, patch

import ginkgo.trading.feeders.okx_data_feeder as okx_mod
from ginkgo.trading.feeders.okx_data_feeder import OKXDataFeeder


class _ConcreteOKXDataFeeder(OKXDataFeeder):
    """桩：绕过 ILiveDataFeeder 抽象方法，仅为测 OKXDataFeeder 的 mixin MRO。"""


_ConcreteOKXDataFeeder.__abstractmethods__ = frozenset()


def _make_feeder():
    # __init__ 内 L70 会实例化 OKXMarketDataFeeder（REST 适配器，触网络）；
    # patch 为 MagicMock 使实例化返回 mock，隔离测试。
    with patch.object(okx_mod, "OKXMarketDataFeeder"):
        return _ConcreteOKXDataFeeder()


class TestOKXDataFeederStatsInit:
    def test_stats_has_publish_mixin_fields(self):
        """独立根补 super().__init__() 后，FeederPublishMixin.stats 初始化成功。"""
        feeder = _make_feeder()
        assert "events_published" in feeder.stats
        assert "publish_errors" in feeder.stats
        assert feeder.stats["events_published"] == 0
        assert feeder.stats["publish_errors"] == 0


class TestOKXDataFeederEventPublisherBinding:
    def test_set_event_publisher_routes_to_engine_put_not_legacy_field(self):
        """set_event_publisher 删 override 后走 EngineBindableMixin：注入 _engine_put，旧 _event_publisher 字段消失。"""
        feeder = _make_feeder()
        captured: list = []
        feeder.set_event_publisher(captured.append)
        assert feeder._engine_put == captured.append
        assert not hasattr(feeder, "_event_publisher"), "旧 _event_publisher 字段应已删"


class TestOKXDataFeederPublishPriceUpdate:
    def test_success_routes_and_counts(self):
        feeder = _make_feeder()
        captured: list = []
        feeder.set_event_publisher(captured.append)
        event = Mock()
        feeder.publish_price_update(event)
        assert captured == [event]
        assert feeder.stats["events_published"] == 1

    def test_runtime_error_counts_publish_errors(self):
        feeder = _make_feeder()

        def raising(e):
            raise RuntimeError("ws transport down")

        feeder.set_event_publisher(raising)
        feeder.publish_price_update(Mock())
        assert feeder.stats["publish_errors"] == 1

    def test_legacy_publish_event_wrapper_removed(self):
        """_publish_event wrapper 已删（语义被 publish_price_update E1 契约取代）。"""
        feeder = _make_feeder()
        assert not hasattr(feeder, "_publish_event"), "_publish_event wrapper 应已删"
