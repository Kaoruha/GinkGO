from ginkgo.backtest.event.base_event import EventBase
from ginkgo.enums import EVENT_TYPES
from ginkgo.backtest.order import Order
from ginkgo.data.ginkgo_data import GINKGODATA
from ginkgo.libs.ginkgo_pretty import base_repr
from ginkgo.libs.ginkgo_logger import GINKGOLOGGER as gl


class EventCapitalUpdate(EventBase):
    """
    Capital Update occurred in 3 scenes:
    1. Create a new order, the money should be freeze
    2. Order filled
        2.1 When selling the capital should add the amount of selling part
        2.2 When buying the frozen part should be removed
    3. Order Cancelled
        3.1 When selling the frozen shell should be revert
        3.2 When buying the frozen capital should be revert
    """

    def __init__(self, order_id=None, *args, **kwargs) -> None:
        super(EventCapitalUpdate, self).__init__(*args, **kwargs)
        self.event_type = EVENT_TYPES.CAPITALUPDATE
        self.__order = None
        if order_id:
            self.get_order(order_id)

    @property
    def _order(self) -> Order:
        return self.__order

    def get_order(self, order_id: str):
        # Make sure the order cant be edit by the event.
        # Get order from db
        r = GINKGODATA.get_order(order_id)
        if r is None:
            gl.logger.error(f"Order:{order_id} not exsist. Please check your code")
            return
        self.__order = r

        # Status could be 1,3,4
        if self.order_status.value == 2:
            gl.logger.error(
                f"EventCapitalUpdate Should Spawn after Order filled or before Order submmit. Order:{self.order_id} status is {self.order_status}. Please check your code."
            )

    @property
    def timestamp(self):
        if self._order is None:
            return None
        return self.__order.timestamp

    @property
    def code(self):
        if self._order is None:
            return None
        return self.__order.code

    @property
    def direction(self):
        if self._order is None:
            return None
        return self.__order.direction

    @property
    def order_id(self):
        if self._order is None:
            return None
        return self.__order.uuid

    @property
    def order_type(self):
        if self._order is None:
            return None
        return self.__order.order_type

    @property
    def order_status(self):
        if self._order is None:
            return None
        return self.__order.status

    @property
    def limit_price(self):
        if self._order is None:
            return None
        return self.__order.limit_price

    def __repr__(self):
        return base_repr(self, EventCapitalUpdate.__name__, 16, 60)
