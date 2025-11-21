"""
组件时间推进事件

用于Engine分阶段控制组件时间推进的事件，确保组件间的时间推进顺序：
1. Matchmaking (同步推进)
2. Portfolio (异步推进) → EventInterestUpdate
3. Feeder (异步推进) → EventPriceUpdate

通过事件队列的FIFO特性，自然保证EventInterestUpdate在Feeder推进前被处理。
"""

from datetime import datetime
from ginkgo.trading.events.base_event import EventBase
from ginkgo.enums import EVENT_TYPES
from ginkgo.libs import base_repr


class ComponentTimeAdvanceInfo:
    """
    组件时间推进信息载体

    封装组件时间推进的目标时间和组件类型，遵循Event数据统一封装在value中的规范。
    """

    def __init__(self, target_time: datetime, component_type: str):
        """
        Args:
            target_time: 目标时间
            component_type: 组件类型 ("portfolio" | "feeder")
        """
        self.target_time = target_time
        self.component_type = component_type

    def __repr__(self):
        return f"ComponentTimeAdvanceInfo(target_time={self.target_time}, component_type={self.component_type})"


class EventComponentTimeAdvance(EventBase):
    """
    组件时间推进事件

    Engine使用此事件分阶段控制组件时间推进，确保：
    - Portfolio先推进，发布EventInterestUpdate
    - mainloop处理EventInterestUpdate，Feeder更新兴趣集
    - Feeder最后推进，仅为interested_codes生成EventPriceUpdate
    """

    def __init__(self, target_time: datetime, component_type: str, *args, **kwargs):
        """
        Args:
            target_time: 目标时间
            component_type: 组件类型 ("portfolio" | "feeder")
        """
        super(EventComponentTimeAdvance, self).__init__(*args, **kwargs)

        # 创建信息载体并封装到payload中
        info = ComponentTimeAdvanceInfo(target_time, component_type)
        self.payload = info

        # 设置事件类型和名称
        self.set_type(EVENT_TYPES.COMPONENT_TIME_ADVANCE)
        self.set_name(f"EventComponentTimeAdvance_{component_type}")

        # 设置事件时间戳
        self.set_time(target_time)

    @property
    def target_time(self) -> datetime:
        """便捷访问：目标时间"""
        return self.payload.target_time

    @property
    def component_type(self) -> str:
        """便捷访问：组件类型"""
        return self.payload.component_type

    def __repr__(self):
        return base_repr(
            self,
            EventComponentTimeAdvance.__name__,
            16,
            60,
            additional_info=f"target_time={self.target_time}, component_type={self.component_type}"
        )
