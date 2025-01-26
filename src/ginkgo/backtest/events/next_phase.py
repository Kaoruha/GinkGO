from ginkgo.backtest.events.base_event import EventBase
from ginkgo.enums import EVENT_TYPES
from ginkgo.libs import base_repr


class EventNextPhase(EventBase):
    def __init__(self, *args, **kwargs) -> None:
        super(EventNextPhase, self).__init__(*args, **kwargs)
        self.set_type(EVENT_TYPES.NEXTPHASE)
        self.set_name("EventNextPhase")

    def __repr__(self):
        return base_repr(self, EventNextPhase.__name__, 16, 60)
