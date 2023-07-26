from ginkgo.enums import EVENT_TYPES, ORDERSTATUS_TYPES
from ginkgo.backtest.order import Order
from ginkgo.libs import base_repr
from ginkgo.backtest.events.base_event import EventBase
from ginkgo import GLOG
from ginkgo.data.ginkgo_data import GDATA


class EventOrderRelated(EventBase):
    """
    Order Related Event
    """

    def __init__(self, order_id: str = "", *args, **kwargs) -> None:
        super(EventOrderRelated, self).__init__(*args, **kwargs)
        self.event_type = EVENT_TYPES.OTHER
        self._order = None
        if order_id != "":
            self._order_id = order_id

    @property
    def order_id(self) -> str:
        return self._order_id

    @property
    def order(self) -> Order:
        if self._order is None:
            # if _order not exist, try get from db
            self.get_order(self.order_id)
        return self._order

    def get_order(self, order_id: str):
        """
        Get order from database
        """
        r = GDATA.get_order_df(order_id)
        if r is None:
            GLOG.logger.error(f"Order:{order_id} not exsist. Please check your code")
            return
        o = Order()
        o.set(r)
        self._order = o

        # # Status could be 1,3,4
        # if self.order_status.value == ORDERSTATUS_TYPES.SUBMITTED:
        #     GLOG.logger.error(
        #         f"EventOrderRelated Should Spawn after Order filled or before Order submmit. Order:{self.order_id} status is {self.order_status}. Please check your code."
        #     )

    @property
    def timestamp(self):
        if self.order is None:
            self.get_order(self.order_id)
        if self.order is None:
            return None
        return self.order.timestamp

    @property
    def code(self):
        if self.order is None:
            self.get_order(self.order_id)
        if self.order is None:
            return None
        return self.order.code.strip(b"\x00".decode())

    @property
    def direction(self):
        if self.order is None:
            self.get_order(self.order_id)
        if self.order is None:
            return None
        return self.order.direction

    @property
    def order_id(self):
        return self._order_id

    @property
    def order_type(self):
        if self.order is None:
            self.get_order(self.order_id)
        if self.order is None:
            return None
        return self.order.type

    @property
    def order_status(self):
        if self.order is None:
            self.get_order(self.order_id)
        if self.order is None:
            return None
        return self.order.status

    @property
    def limit_price(self):
        if self.order is None:
            self.get_order(self.order_id)
        if self.order is None:
            return None
        return self.order.limit_price

    @property
    def volume(self):
        if self.order is None:
            self.get_order(self.order_id)
        if self.order is None:
            return None
        return self.order.volume

    @property
    def freeze(self):
        if self.order is None:
            self.get_order(self.order_id)
        if self.order is None:
            return None
        return self.order.freeze

    @property
    def transaction_price(self):
        if self.order is None:
            self.get_order(self.order_id)
        if self.order is None:
            return None
        return self.order.transaction_price

    @property
    def remain(self):
        if self.order is None:
            self.get_order(self.order_id)
        if self.order is None:
            return None
        return self.order.remain

    def __repr__(self):
        return base_repr(self, EventOrderRelated.__name__, 16, 60)
