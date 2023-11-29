from ginkgo.enums import EVENT_TYPES, ORDERSTATUS_TYPES
from ginkgo.backtest.order import Order
from ginkgo.libs import base_repr
from ginkgo.backtest.events.base_event import EventBase
from ginkgo.libs.ginkgo_logger import GLOG
from ginkgo.data.ginkgo_data import GDATA
from ginkgo.libs.ginkgo_normalize import datetime_normalize


class EventCapitalUpdate(EventBase):
    """
    Capital Update occurred in 3 scenes:
    1. Create a new order, the money should be frozen
    2. Order filled
        2.1 When selling the capital should add the amount of selling part
        2.2 When buying the frozen part should be removed
    3. Order Cancelled
        3.1 When selling the frozen shell should be revert
        3.2 When buying the frozen capital should be revert

    Seems like this event is not necessary.
    """

    def __init__(self, *args, **kwargs) -> None:
        super(EventCapitalUpdate, self).__init__(*args, **kwargs)
        self.set_type(EVENT_TYPES.CAPITALUPDATE)

    def __repr__(self):
        return base_repr(self, EventCapitalUpdate.__name__, 16, 60)
