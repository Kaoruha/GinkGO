"""
EventOrderRelated 模块

该模块定义了一个与订单相关的事件类，用于处理与订单相关的操作。
事件包含订单的详细信息，如订单ID、时间戳、代码、方向、类型、状态等。
"""

from ginkgo.enums import EVENT_TYPES, ORDERSTATUS_TYPES
from ginkgo.backtest.order import Order
from ginkgo.libs import base_repr
from ginkgo.backtest.events.base_event import EventBase


class EventOrderRelated(EventBase):
    """
    订单相关事件类

    继承自 EventBase，用于处理与订单相关的操作。
    """

    def __init__(self, order: Order, *args, **kwargs) -> None:
        if not isinstance(order, Order):
            raise ValueError("Order must be an instance of Order.")
        super(EventOrderRelated, self).__init__(*args, **kwargs)
        self.set_type(EVENT_TYPES.OTHER)
        self._order = order
        self._order_id = order.uuid
        self.portfolio_id = order.portfolio_id
        self.engine_id = order.engine_id

    @property
    def order_id(self) -> str:
        return self._order_id

    @property
    def value(self) -> Order:
        return self._order

    @property
    def timestamp(self):
        return self.value.timestamp if self.value else None

    @property
    def code(self):
        return self.value.code if self.value else None

    @property
    def direction(self):
        return self.value.direction if self.value else None

    @property
    def order_id(self):
        return self._order_id

    @property
    def order_type(self):
        return self.value.order_type if self.value else None

    @property
    def order_status(self):
        return self.value.status if self.value else None

    @property
    def limit_price(self):
        return self.value.limit_price if self.value else None

    @property
    def volume(self):
        return self.value.volume if self.value else None

    @property
    def frozen(self):
        return self.value.frozen if self.value else None

    @property
    def transaction_price(self):
        return self.value.transaction_price if self.value else None

    @property
    def transaction_volume(self):
        return self.value.transaction_volume if self.value else None

    @property
    def remain(self):
        return self.value.remain if self.value else None

    @property
    def fee(self):
        return self.value.fee if self.value else None

    def __repr__(self):
        return base_repr(self, EventOrderRelated.__name__, 24, 70)
