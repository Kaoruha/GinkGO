from ginkgo.backtest.event.base_event import EventBase
from ginkgo.enums import EVENT_TYPES
from ginkgo.backtest.order import Order
from ginkgo.data.ginkgo_data import GINKGODATA
from ginkgo.libs.ginkgo_pretty import base_repr
from ginkgo.libs import GINKGOLOGGER as gl


class EventPositionUpdate(EventBase):
    """
    Position Update occurred after
    1. OrderFilled
        1.1 Buying filled. Should add the position
        1.2 Selling filled. Should update the position
    2. OrderCanceled
        2.1 Buying canceled. do nothing.
        2.2 Selling canceled. Should update the frozen position
    """

    def __init__(self, order_id=None, *args, **kwargs) -> None:
        super(EventPositionUpdate, self).__init__(*args, **kwargs)
        self.event_type = EVENT_TYPES.POSITIONUPDATE
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

        if self.order_status.value != 3 or self.order_status != 4:
            gl.logger.error(
                f"EventPositionUpdate Should Spawn after Order Filled or Canceled. Order:{self.order_id} status is {self.order_status}. Please check your code."
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
        if self._order is None:
            return None
        return self.order.uuid

    @property
    def order_type(self):
        if self.order is None:
            return None
        return self.order.type

    @property
    def order_status(self):
        if self.order is None:
            return None
        return self.order.status

    @property
    def limit_price(self):
        if self.order is None:
            return None
        return float(self.order.limit_price)

    @property
    def volume(self):
        if self.order is None:
            return None
        return self.order.volume

    def __repr__(self):
        return base_repr(self, EventOrderFill.__name__, 16, 60)
