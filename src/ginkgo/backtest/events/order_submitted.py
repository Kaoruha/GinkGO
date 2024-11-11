from ginkgo.backtest.events.order_related import EventOrderRelated
from ginkgo.backtest.order import Order
from ginkgo.enums import EVENT_TYPES


class EventOrderSubmitted(EventOrderRelated):
    """
    Order Submission can happened after order created and pass the risk managerment.
    """

    def __init__(self, order: Order, *args, **kwargs) -> None:
        super(EventOrderSubmitted, self).__init__(order, *args, **kwargs)
        self.set_type(EVENT_TYPES.ORDERSUBMITTED)
