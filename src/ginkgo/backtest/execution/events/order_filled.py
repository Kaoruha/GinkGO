from .order_related import EventOrderRelated
from ginkgo.enums import EVENT_TYPES


class EventOrderFilled(EventOrderRelated):
    """
    OrderFill may happened after submmit.
    """

    def __init__(self, order, *args, **kwargs) -> None:
        super(EventOrderFilled, self).__init__(order, *args, **kwargs)
        self.set_type(EVENT_TYPES.ORDERFILLED)
