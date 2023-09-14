from ginkgo.backtest.events.order_related import EventOrderRelated
from ginkgo.enums import EVENT_TYPES


class EventOrderSubmitted(EventOrderRelated):
    """
    Order Submission can happened after order created and pass the risk managerment.
    """

    def __init__(self, order_id: str = "", *args, **kwargs) -> None:
        super(EventOrderSubmitted, self).__init__(*args, **kwargs)
        self.set_type(EVENT_TYPES.ORDERSUBMITTED)
        self._order = None
        if order_id != "":
            self._order_id = order_id
