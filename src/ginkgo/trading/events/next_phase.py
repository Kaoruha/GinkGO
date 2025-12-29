# Upstream: Backtest Engines(阶段推进控制)、Portfolio Manager(下一阶段通知)
# Downstream: EventBase(继承提供事件基础能力)、EVENT_TYPES(事件类型枚举NEXTPHASE)、base_repr(字符串表示)
# Role: EventNextPhase下一阶段事件用于Engine控制流程推进，定义phase_type等属性






from ginkgo.trading.events.base_event import EventBase
from ginkgo.enums import EVENT_TYPES
from ginkgo.libs import base_repr


class EventNextPhase(EventBase):
    def __init__(self, *args, **kwargs) -> None:
        super(EventNextPhase, self).__init__(*args, **kwargs)
        self.set_type(EVENT_TYPES.NEXTPHASE)
        self.set_name("EventNextPhase")

    def __repr__(self):
        return base_repr(self, EventNextPhase.__name__, 16, 60)
