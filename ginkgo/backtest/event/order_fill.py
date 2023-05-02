from ginkgo.backtest.event.base_event import EventBase
from ginkgo.enums import EVENT_TYPES
from ginkgo.backtest.order import Order
from ginkgo.data.ginkgo_data import GINKGODATA
from ginkgo.libs.ginkgo_pretty import base_repr
from ginkgo.libs import GINKGOLOGGER as gl


class EventOrderFill(EventBase):
    """
    OrderFill may happened after submmit.
    """

    def __init__(self, order_id=None, *args, **kwargs) -> None:
        super(EventOrderFill, self).__init__(*args, **kwargs)
        self.event_type = EVENT_TYPES.ORDERFILL
        self._order = None
        if order_id:
            self.get_order(order_id)

    @property
    def order(self) -> Order:
        return self._order

    def get_order(self, order_id: str):
        # Make sure the order cant be edit by the event.
        # Get order from db
        r = GINKGODATA.get_order(order_id)
        if r is None:
            gl.logger.error(f"Order:{order_id} not exsist. Please check your code")
            return
        self._order = r

        # Status could be only 2
        if self.order_status.value != 2:
            gl.logger.error(
                f"EventOrderFill Should Spawn after Order submmit. Order:{self.order_id} status is {self.order_status}. Please check your code."
            )

    @property
    def timestamp(self):
        if self.order is None:
            return None
        return self.order.timestamp

    @property
    def code(self):
        if self.order is None:
            return None
        return self.order.code

    @property
    def direction(self):
        if self.order is None:
            return None
        return self.order.direction

    @property
    def order_id(self):
        if self.order is None:
            return None
        return self.order.uuid

    @property
    def order_type(self):
        if self.order is None:
            return None
        return self.order.order_type

    @property
    def order_status(self):
        if self.order is None:
            return None
        return self.order.status

    @property
    def limit_price(self):
        if self.order is None:
            return None
        return self.order.limit_price

    def __repr__(self):
        return base_repr(self, EventOrderFill.__name__, 16, 60)
