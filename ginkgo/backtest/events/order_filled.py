from ginkgo.backtest.events.order_related import EventOrderRelated
from ginkgo.enums import EVENT_TYPES


class EventOrderFilled(EventOrderRelated):
    """
    OrderFill may happened after submmit.
    """

    def __init__(self, order_id: str = "", *args, **kwargs) -> None:
        super(EventOrderFilled, self).__init__(*args, **kwargs)
        self.set_type(EVENT_TYPES.ORDERFILLED)
        self._order = None
        if order_id != "":
            self._order_id = order_id
