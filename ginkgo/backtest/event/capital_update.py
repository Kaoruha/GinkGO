from ginkgo.backtest.event.base_event import EventBase
from ginkgo.enums import EVENT_TYPES
from ginkgo.backtest.order import Order
from ginkgo.data.ginkgo_data import GINKGODATA
from ginkgo.libs.ginkgo_pretty import base_repr
from ginkgo.libs.ginkgo_logger import GINKGOLOGGER as gl


class EventCapitalUpdate(EventBase):
    def __init__(self, order_id=None, *args, **kwargs) -> None:
        super(EventCapitalUpdate, self).__init__(*args, **kwargs)
        self.event_type = EVENT_TYPES.CAPTIALUPDATE
        self.__order = None
        if order_id:
            self.set_order(order_id)

    def get_order(self, order_id: str):
        # Make sure the order cant be edit by the event.
        # Get order from db
        r = GINKGODATA.get_order(order_id)
        self.__order = r

        if self.__order.status.value == 3 or self.__order.status.value == 1:
            return
        else:
            gl.logger.error(
                f"EventCapitalUpdate Should Spawn after Order filled or before Order submmit. Order:{self.order_id} status is {self.order_status}. Please check your code."
            )

    @property
    def timestamp(self):
        return self.__order.timestamp

    @property
    def code(self):
        return self.__order.code

    @property
    def direction(self):
        return self.__order.direction

    @property
    def order_id(self):
        return self.__order.uuid

    @property
    def order_type(self):
        return self.__order.order_type

    @property
    def order_status(self):
        return self.__order.status

    @property
    def limit_price(self):
        return self.__order.limit_price

    def __repr__(self):
        return base_repr(self, EventCapitalUpdate.__name__, 16, 60)
