from ginkgo.enums import EVENT_TYPES, ORDERSTATUS_TYPES
from ginkgo.backtest.order import Order
from ginkgo.libs import base_repr
from ginkgo.backtest.events.base_event import EventBase


class EventOrderRelated(EventBase):
    """
    Order Related Event
    """

    def __init__(self, order: Order, *args, **kwargs) -> None:
        super(EventOrderRelated, self).__init__(*args, **kwargs)
        self.set_type(EVENT_TYPES.OTHER)
        self._order = order
        self._order_id = order.uuid

    @property
    def order_id(self) -> str:
        return self._order_id

    @property
    def value(self) -> Order:
        return self._order

    @property
    def timestamp(self):
        if self.value is None:
            return None
        return self.value.timestamp

    @property
    def code(self):
        if self.value is None:
            return None
        return self.value.code

    @property
    def direction(self):
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
            return None
        return self.value.status

    @property
    def limit_price(self):
        if self.value is None:
            return None
        return self.value.limit_price

    @property
    def volume(self):
        if self.value is None:
            return None
        return self.value.volume

    @property
    def frozen(self):
        if self.value is None:
            return None
        return self.value.frozen

    @property
    def transaction_price(self):
        if self.value is None:
            return None
        return self.value.transaction_price

    @property
    def transaction_volume(self):
        if self.value is None:
            return None
        return self.value.transaction_volume

    @property
    def remain(self):
        if self.value is None:
            return None
        return self.value.remain

    @property
    def fee(self):
        if self.value is None:
            return None
        return self.value.fee

    @property
    def portfolio_id(self) -> str:
        if self.value is None:
            return None
        return self.value.portfolio_id

    def __repr__(self):
        return base_repr(self, EventOrderRelated.__name__, 24, 70)
