from ginkgo.enums import EVENT_TYPES, ORDERSTATUS_TYPES
from ginkgo.backtest.order import Order
from ginkgo.libs import base_repr
from ginkgo.backtest.events.base_event import EventBase
from ginkgo.libs.ginkgo_logger import GLOG
from ginkgo.data.ginkgo_data import GDATA


class EventOrderRelated(EventBase):
    """
    Order Related Event
    """

    def __init__(self, order_id: str = "", *args, **kwargs) -> None:
        super(EventOrderRelated, self).__init__(*args, **kwargs)
        self.set_type(EVENT_TYPES.OTHER)
        self._order = None
        self._order_id = ""
        if order_id != "":
            self._order_id = order_id

    @property
    def order_id(self) -> str:
        return self._order_id

    @property
    def value(self) -> Order:
        if self._order is None:
            # if _order not exist, try get from db
            self.get_order(self.order_id)
        return self._order

    def get_order(self, order_id: str):
        """
        Get order from database
        """
        r = GDATA.get_order_df(order_id)
        if r.shape[0] == 0:
            GLOG.CRITICAL(f"Order:{order_id} not exsist. Please check your code")
            return
        if r is None:
            GLOG.CRITICAL(f"111Order:{order_id} not exsist. Please check your code")
            return
        o = Order()
        try:
            o.set(r.iloc[0])
        except Exception as e:
            print(e)
        self._order = o

        # Status could be 1,3,4
        if self.order_status.value == ORDERSTATUS_TYPES.SUBMITTED:
            GLOG.ERROR(
                f"EventOrderRelated Should Spawn after Order filled or before Order submmit. Order:{self.order_id} status is {self.order_status}. Please check your code."
            )

    @property
    def timestamp(self):
        if self.value is None:
            self.get_order(self.order_id)
        if self.value is None:
            return None
        return self.value.timestamp

    @property
    def code(self):
        if self.value is None:
            self.get_order(self.order_id)
        if self.value is None:
            return None
        return self.value.code.strip(b"\x00".decode())

    @property
    def direction(self):
        if self.value is None:
            self.get_order(self.order_id)
        if self.value is None:
            return None
        return self.value.direction

    @property
    def order_id(self):
        return self._order_id

    @property
    def order_type(self):
        if self.value is None:
            self.get_order(self.order_id)
        if self.value is None:
            return None
        return self.value.type

    @property
    def order_status(self):
        if self.value is None:
            self.get_order(self.order_id)
        if self.value is None:
            return None
        return self.value.status

    @property
    def limit_price(self):
        if self.value is None:
            self.get_order(self.order_id)
        if self.value is None:
            return None
        return self.value.limit_price

    @property
    def volume(self):
        if self.value is None:
            self.get_order(self.order_id)
        if self.value is None:
            return None
        return self.value.volume

    @property
    def frozen(self):
        if self.value is None:
            self.get_order(self.order_id)
        if self.value is None:
            return None
        return self.value.frozen

    @property
    def transaction_price(self):
        if self.value is None:
            self.get_order(self.order_id)
        if self.value is None:
            return None
        return self.value.transaction_price

    @property
    def remain(self):
        if self.value is None:
            self.get_order(self.order_id)
        if self.value is None:
            return None
        return self.value.remain

    @property
    def fee(self):
        if self.value is None:
            self.get_order(self.order_id)
        if self.value is None:
            return None
        return self.value.fee

    @property
    def backtest_id(self) -> str:
        if self.value is None:
            self.get_order(self.order_id)
        if self.value is None:
            return None
        return self.value.backtest_id

    def __repr__(self):
        return base_repr(self, EventOrderRelated.__name__, 16, 60)
