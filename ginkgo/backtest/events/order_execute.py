from ginkgo.backtest.events.order_related import EventOrderRelated
from ginkgo.enums import EVENT_TYPES


class EventOrderExecute(EventOrderRelated):
    """
    OrderFill may happened after submmit.
    """

    def __init__(self, order_id: str = "", *args, **kwargs) -> None:
        super(EventOrderExecute, self).__init__(*args, **kwargs)
        self.event_type = EVENT_TYPES.ORDEREXECUTE
        self._order = None
        if order_id != "":
            self._order_id = order_id
