# Upstream: Portfolio Manager(资金变更通知)、Broker(订单资金冻结/解冻)
# Downstream: EventBase(继承提供事件基础能力)、EVENT_TYPES(事件类型枚举CAPITALUPDATE)、ORDERSTATUS_TYPES(订单状态枚举)
# Role: EventCapitalUpdate资金更新事件继承EventBase，封装CapitalAdjustment对象，提供便捷属性访问资金变动信息






"""
EventCapitalUpdate 模块

该模块定义了一个资金更新事件类，用于处理与资金更新相关的操作。
资金更新可能发生在以下场景：
1. 创建新订单时，资金应被冻结。
2. 订单成交时：
   - 卖出时，资金应增加。
   - 买入时，冻结资金应被移除。
3. 订单取消时：
   - 卖出时，冻结资金应被恢复。
   - 买入时，冻结资金应被恢复。
"""

from ginkgo.enums import EVENT_TYPES, ORDERSTATUS_TYPES
from ginkgo.libs import base_repr
from ginkgo.trading.events.base_event import EventBase


class EventCapitalUpdate(EventBase):
    """
    Capital Update occurred in 3 scenes:
    1. Create a new order, the money should be frozen
    2. Order filled
        2.1 When selling the capital should add the amount of selling part
        2.2 When buying the frozen part should be removed
    3. Order Cancelled
        3.1 When selling the frozen shell should be revert
        3.2 When buying the frozen capital should be revert

    Seems like this event is not necessary.
    """

    def __init__(self, *args, **kwargs) -> None:
        super(EventCapitalUpdate, self).__init__(*args, **kwargs)
        self.set_type(EVENT_TYPES.CAPITALUPDATE)

    def __repr__(self):
        return base_repr(self, EventCapitalUpdate.__name__, 16, 60)
