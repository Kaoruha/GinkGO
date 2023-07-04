from ginkgo.backtest.event.base_event import EventBase
from ginkgo.enums import EVENT_TYPES
from ginkgo.backtest.order import Order
from ginkgo.data.ginkgo_data import GDATA
from ginkgo.libs.ginkgo_pretty import base_repr
from ginkgo.libs import GLOG


class EventNextPhase(EventBase):
    def __init__(self, order_id=None, *args, **kwargs) -> None:
        super(EventOrderFill, self).__init__(*args, **kwargs)
        self.event_type = EVENT_TYPES.NEXTPHASE

    def __repr__(self):
        return base_repr(self, EventOrderFill.__name__, 16, 60)
