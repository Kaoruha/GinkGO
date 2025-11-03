"""
时间推进事件

扩展EventNextPhase概念，携带具体的目标时间信息，
用于在mainloop中统一处理时间推进逻辑。
"""

import datetime
from ginkgo.trading.events.base_event import EventBase
from ginkgo.enums import EVENT_TYPES
from ginkgo.libs import base_repr


class EventTimeAdvance(EventBase):
    """时间推进事件
    
    携带目标时间的时间推进事件，用于在事件驱动架构中
    统一处理时间推进逻辑，替代直接调用advance_time_to。
    """

    def __init__(self, target_time: datetime.datetime, phase_id: str = None, *args, **kwargs) -> None:
        super(EventTimeAdvance, self).__init__(*args, **kwargs)
        self.set_type(EVENT_TYPES.TIME_ADVANCE)
        self.set_name("EventTimeAdvance")
        
        # 关键属性：携带具体的目标时间
        self.target_time = target_time
        
        # 阶段ID，用于追踪完成状态
        self.phase_id = phase_id or f"time_advance_{target_time.isoformat()}"
        
        # 设置事件时间戳为目标时间
        self.set_time(target_time)

    @property
    def target_datetime(self) -> datetime.datetime:
        """获取目标时间（兼容性属性）"""
        return self.target_time

    def __repr__(self):
        return base_repr(
            self, 
            EventTimeAdvance.__name__, 
            16, 
            60,
            additional_info=f"target_time={self.target_time}, phase_id={self.phase_id}"
        )