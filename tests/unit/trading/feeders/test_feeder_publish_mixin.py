"""
FeederPublishMixin 单元测试

TDD 覆盖（publish_price_update 接口面三态）：
- 成功路径：经 EngineBindableMixin 投递到 engine.put 并计数 events_published
- None-binding：_engine_put 未绑时不抛、不计 events_published、走 loud ERROR
- runtime 抛：publish_event 抛异常时韧性吞、计数 publish_errors、不杀调用流
"""

from unittest.mock import Mock

from ginkgo.entities.mixins.engine_bindable_mixin import EngineBindableMixin
from ginkgo.trading.feeders.mixins.feeder_publish_mixin import FeederPublishMixin


class StubFeeder(EngineBindableMixin, FeederPublishMixin):
    """测试用 feeder 桩：装两个 mixin，满足 publish_price_update 的依赖。

    不定义 __init__，靠 MRO（EngineBindableMixin → FeederPublishMixin → object）
    协作链触发各 mixin 的初始化。
    """

    pass


def make_event():
    """创建测试价格事件桩（publish_price_update 对 event 不解构，任意对象即可）。"""
    event = Mock()
    event.name = "EventPriceUpdate"
    return event


class TestPublishPriceUpdateSuccess:
    def test_routes_to_engine_put_and_increments_events_published(self):
        """成功路径：publish_price_update 把 event 投递给 engine.put，并 events_published += 1。"""
        captured = []
        feeder = StubFeeder()
        feeder.set_event_publisher(captured.append)

        event = make_event()
        feeder.publish_price_update(event)

        assert captured == [event], "event 应原样投递到 engine.put"
        assert feeder.stats["events_published"] == 1
        assert feeder.stats["publish_errors"] == 0


class TestPublishPriceUpdateNoneBinding:
    def test_unbound_engine_put_neither_counts_nor_raises(self):
        """None-binding：_engine_put 未绑时不抛、events_published 不增（非成功投递）。

        self.log=GLOG 已设，使 EngineBindableMixin.publish_event 的 None-guard
        走 engine_bindable_mixin.py:71 loud ERROR（配置 bug 可见）。
        """
        feeder = StubFeeder()
        # 不调 set_event_publisher → _engine_put 保持 None
        event = make_event()
        feeder.publish_price_update(event)  # 不应抛

        assert feeder.stats["events_published"] == 0, "None-binding 不应计为成功投递"
        assert feeder.stats["publish_errors"] == 0, "None-binding 是配置问题非 runtime 抛"


class TestPublishPriceUpdateRuntimeError:
    def test_runtime_exception_resilient_and_counts_publish_errors(self):
        """runtime 抛：engine.put 抛异常时韧性吞、publish_errors += 1、不向上抛（不杀 WS 流）。

        E1 错误契约第三层：与 None-binding（config bug，loud ERROR）区分——
        runtime 抛是 transport/接收 bug，韧性吞 + 计数，防单 tick 拖垮接收循环。
        """
        feeder = StubFeeder()

        def raising_publisher(event):
            raise RuntimeError("transport down")

        feeder.set_event_publisher(raising_publisher)
        event = make_event()
        feeder.publish_price_update(event)  # 不应向上抛

        assert feeder.stats["events_published"] == 0, "投递失败不计成功"
        assert feeder.stats["publish_errors"] == 1
