"""
FeederPublishMixin

feeder 层价格发布统一 seam（ADR-019）：publish_price_update 背后藏投递/统计/错误契约。
- 投递：经 EngineBindableMixin.publish_event（_engine_put is None 时 loud ERROR）
- 统计：events_published / publish_errors
- self.log：让 EngineBindableMixin.publish_event 的 None-guard 走 :71 ERROR 分支
          （feeder 原无 log 属性会落 :73 INFO，加 log 让配置 bug 可见）

详见 docs/adrs/ADR-019-feeder-publish-seam.md
"""

from ginkgo.libs import GLOG


class FeederPublishMixin:
    """feeder 价格发布 seam 宿主（ADR-019）。

    与 EngineBindableMixin 协作：本 mixin own 统计 + log 标记 + 领域 wrapper，
    EngineBindableMixin own 引擎投递原语（publish_event/_engine_put）。
    __init__ 末尾 super().__init__() 协作 MRO 链，供多继承 feeder 组合。
    """

    def __init__(self, *args, **kwargs):
        self.stats = {"events_published": 0, "publish_errors": 0}
        self.log = GLOG
        super().__init__(*args, **kwargs)

    def publish_price_update(self, event) -> None:
        """发布价格事件到引擎（E1 错误契约）。

        - engine_put 未绑（config bug）：publish_event 走 loud ERROR，不计 events_published
        - runtime 抛（transport bug）：韧性吞，publish_errors += 1，不杀调用流
        - 成功：events_published += 1
        """
        try:
            self.publish_event(event)
        except Exception as e:
            self.stats["publish_errors"] += 1
            GLOG.ERROR(f"publish_price_update failed: {e}")
            return
        if self.engine_put is not None:
            self.stats["events_published"] += 1
