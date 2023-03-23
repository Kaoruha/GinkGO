from ginkgo.backtest.event.base_event import EventBase
from ginkgo.enums import EventType, PriceInfo, Source
from ginkgo.backtest.order import Order


class EventOrderSubmission(EventBase):
    def __init__(self, order_id=None, order=None, *args, **kwargs) -> None:
        super(EventPriceUpdate, self).__init__(*args, **kwargs)
        self.event_type = EventType.ORDERSUBMISSION
        self.__order = None
        self.order(order_id)

    @property
    def order(self):
        return self.__order

    @order.setter
    def order(self, order_id: str):
        # Make sure the order cant be edit by the event.
        if self.__order is None:
            pass  # TODO Get order from db

    @property
    def timestamp(self):
        return self.order.timestamp

    @property
    def code(self):
        return self.order.code

    @property
    def direction(self):
        return self.order.direction

    @property
    def order_id(self):
        return self.order.id
