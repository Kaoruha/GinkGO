from ginkgo.backtest.events.order_related import EventOrderRelated
from ginkgo.enums import EVENT_TYPES


class EventOrderExecute(EventOrderRelated):
    """
    OrderFill may happened after submmit.
    """

    def __init__(self, order, *args, **kwargs) -> None:
        super(EventOrderExecute, self).__init__(order, *args, **kwargs)
        self.set_type(EVENT_TYPES.ORDEREXECUTE)
