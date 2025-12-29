# Upstream: Data Feeder(监听更新关注标的)、Portfolio(advance_time后发布)、Selector(pick选股后触发)
# Downstream: EventBase(继承提供事件基础能力)、EVENT_TYPES(事件类型枚举INTERESTUPDATE)
# Role: EventInterestUpdate利息更新事件继承EventBase，封装利息信息，提供便捷属性访问利息数据






"""
关注标的更新事件（去除订阅/广播模式的粘连，统一用事件通告 Feeder）
"""

from typing import List
from datetime import datetime

from ginkgo.trading.events.base_event import EventBase
from ginkgo.enums import EVENT_TYPES


class EventInterestUpdate(EventBase):
    """
    通知数据供给层当前应关注的标的集合。
    由 Portfolio 在 advance_time 后根据 selector 输出发布。
    Feeder 监听该事件，用于更新内部感兴趣标的集合。
    """

    def __init__(self, portfolio_id: str, codes: List[str], timestamp: datetime = None, *args, **kwargs) -> None:
        super().__init__(name="InterestUpdate", *args, **kwargs)
        self.set_type(EVENT_TYPES.INTERESTUPDATE)
        self._portfolio_id = portfolio_id
        self._codes = list(dict.fromkeys(codes))  # 去重
        if timestamp:
            self.set_time(timestamp)

    @property
    def portfolio_id(self) -> str:
        return self._portfolio_id

    @property
    def codes(self) -> List[str]:
        return self._codes

    def __repr__(self) -> str:
        return f"EventInterestUpdate(portfolio_id={self._portfolio_id[:8]}, codes={len(self._codes)})"

