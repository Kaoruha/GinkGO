from .order_related import EventOrderRelated
from ginkgo.enums import EVENT_TYPES


class EventPositionUpdate(EventOrderRelated):

    """
    Position Update occurred after
    1. OrderFilled
        1.1 Buying filled. Should add the position
        1.2 Selling filled. Should update the position
    2. OrderCanceled
        2.1 Buying canceled. do nothing.
        2.2 Selling canceled. Should update the frozen position
    """

    def __init__(self, order_id: str = "", *args, **kwargs) -> None:
        super(EventPositionUpdate, self).__init__(*args, **kwargs)
        self.set_type(EVENT_TYPES.POSITIONUPDATE)
        self._order = None
        if order_id != "":
            self._order_id = order_id
