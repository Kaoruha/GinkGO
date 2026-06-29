"""
LiveDataFeeder 端到端：装 EngineBindableMixin+FeederPublishMixin 后 MRO 通 + stats 合并。

验证关键风险点（ADR-019 Consequences）：
- stats 合并：LiveDataFeeder 自有 stats 字段与 FeederPublishMixin.stats 重叠，
  __init__ 补 super().__init__() 后须 update（非覆盖），保留 publish_errors
- set_event_publisher：删 override 后走 EngineBindableMixin（注入 _engine_put）
- publish_price_update 接线 + 三态计数

桩用 __abstractmethods__ = frozenset() 绕过 ILiveDataFeeder ABC，不依赖 GCONF/WS。
"""
from unittest.mock import Mock

from ginkgo.trading.feeders.live_feeder import LiveDataFeeder


class _ConcreteLiveDataFeeder(LiveDataFeeder):
    """桩：绕过 ILiveDataFeeder 抽象方法，仅为测 LiveDataFeeder 的 mixin MRO + stats 合并。"""


_ConcreteLiveDataFeeder.__abstractmethods__ = frozenset()


def _make_feeder():
    return _ConcreteLiveDataFeeder()


class TestLiveDataFeederStatsMerge:
    def test_stats_keeps_both_publish_mixin_and_feeder_fields(self):
        """stats 合并：保留 FeederPublishMixin 的 events_published/publish_errors + LiveDataFeeder 特有字段。

        关键：LiveDataFeeder.__init__ 的 self.stats 不能覆盖 FeederPublishMixin 设的 stats
        （否则丢 publish_errors → runtime 抛时 stats["publish_errors"] += 1 触发 KeyError）。
        """
        feeder = _make_feeder()
        assert "events_published" in feeder.stats
        assert "publish_errors" in feeder.stats, "FeederPublishMixin 字段未被 LiveDataFeeder.stats 覆盖"
        assert "messages_received" in feeder.stats
        assert "connection_errors" in feeder.stats


class TestLiveDataFeederEventPublisherBinding:
    def test_set_event_publisher_routes_to_engine_put_not_legacy_field(self):
        """set_event_publisher 删 override 后走 EngineBindableMixin：注入 _engine_put，旧 event_publisher 字段消失。"""
        feeder = _make_feeder()
        captured: list = []
        feeder.set_event_publisher(captured.append)
        assert feeder._engine_put == captured.append
        assert not hasattr(feeder, "event_publisher"), "旧 event_publisher 字段应已删"


class TestLiveDataFeederPublishPriceUpdate:
    def test_success_routes_and_counts(self):
        feeder = _make_feeder()
        captured: list = []
        feeder.set_event_publisher(captured.append)
        event = Mock()
        feeder.publish_price_update(event)
        assert captured == [event]
        assert feeder.stats["events_published"] == 1

    def test_runtime_error_counts_publish_errors_no_keyerror(self):
        """runtime 抛计 publish_errors——验证 stats 合并未丢该字段（无 KeyError）。"""
        feeder = _make_feeder()

        def raising(e):
            raise RuntimeError("transport down")

        feeder.set_event_publisher(raising)
        feeder.publish_price_update(Mock())
        assert feeder.stats["publish_errors"] == 1
