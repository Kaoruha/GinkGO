"""
EventOrderRelated 模块

该模块定义了一个与订单相关的事件类，用于处理与订单相关的操作。
事件包含订单的详细信息，如订单ID、时间戳、代码、方向、类型、状态等。
"""

from ginkgo.enums import EVENT_TYPES, ORDERSTATUS_TYPES
from ginkgo.trading.entities.order import Order
from ginkgo.libs import base_repr
from ginkgo.trading.events.base_event import EventBase


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

        # 统一使用payload
        self.payload = order

    @property
    def order_id(self) -> str:
        return self._order_id

    
    @property
    def timestamp(self):
        """
        事件时间戳 - 始终返回事件创建时间
        """
        return super().timestamp

    @property
    def business_timestamp(self):
        """
        业务数据时间戳 - 返回订单数据的时间，如果没有订单数据则返回事件时间
        """
        return self.payload.timestamp if self.payload else self.timestamp

    @property
    def code(self):
        return self.payload.code if self.payload else None

    @property
    def direction(self):
        return self.payload.direction if self.payload else None

# 删除重复的order_id属性定义（第32-33行已定义）

    @property
    def order_type(self):
        return self.payload.order_type if self.payload else None

    @property
    def order_status(self):
        return self.payload.status if self.payload else None

    @property
    def limit_price(self):
        return self.payload.limit_price if self.payload else None

    @property
    def volume(self):
        return self.payload.volume if self.payload else None

    @property
    def frozen_money(self):
        return self.payload.frozen_money if self.payload else None

    @property
    def frozen_volume(self):
        return self.payload.frozen_volume if self.payload else None

    @property
    def transaction_price(self):
        return self.payload.transaction_price if self.payload else None

    @property
    def transaction_volume(self):
        return self.payload.transaction_volume if self.payload else None

    @property
    def remain(self):
        return self.payload.remain if self.payload else None

    @property
    def fee(self):
        return self.payload.fee if self.payload else None

    def __repr__(self):
        return base_repr(self, EventOrderRelated.__name__, 24, 70)
