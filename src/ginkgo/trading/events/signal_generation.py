# Upstream: Strategies(生成Signal后创建EventSignalGeneration)、Portfolio Manager(接收Event并处理Signal)
# Downstream: EventBase(继承提供时间戳/上下文/组件基础能力)、EVENT_TYPES(事件类型枚举SIGNALGENERATION)、Signal实体(payload载荷)
# Role: 信号生成事件继承EventBase类型为SIGNALGENERATION携带Signal对象支持交易系统功能和组件集成提供完整业务支持






from ginkgo.trading.events.base_event import EventBase
from ginkgo.enums import EVENT_TYPES
from ginkgo.trading.entities.signal import Signal
from ginkgo.libs import base_repr


class EventSignalGeneration(EventBase):
    def __init__(self, signal, name: str = "EventSignalGen", *args, **kwargs):
        super(EventSignalGeneration, self).__init__(name, *args, **kwargs)
        self.set_type(EVENT_TYPES.SIGNALGENERATION)
        # 统一使用payload
        self.payload = signal

    @property
    def code(self):
        return self.payload.code

    @property
    def direction(self):
        return self.payload.direction

    @property
    def timestamp(self):
        """
        事件时间戳 - 始终返回事件创建时间
        """
        return super().timestamp

    @property
    def business_timestamp(self):
        """
        业务数据时间戳 - 返回信号的业务时间戳（信号触发的业务时间），
        如果信号没有业务时间戳则回退到信号的时间戳，最后才回退到事件时间
        """
        if self.payload is None:
            print(f"   🔍 [EVENT_SIGNAL_DEBUG] business_timestamp: payload is None, returning event.timestamp={self.timestamp}")
            return self.timestamp

        # 优先使用信号的business_timestamp，这是信号触发的真正业务时间
        if hasattr(self.payload, 'business_timestamp') and self.payload.business_timestamp is not None:
            print(f"   🔍 [EVENT_SIGNAL_DEBUG] business_timestamp: using payload.business_timestamp={self.payload.business_timestamp}")
            return self.payload.business_timestamp

        # 回退到信号的timestamp（信号创建时间）
        print(f"   🔍 [EVENT_SIGNAL_DEBUG] business_timestamp: payload.business_timestamp is None or missing, using payload.timestamp={self.payload.timestamp}")
        return self.payload.timestamp

    def __repr__(self):
        return base_repr(self, EventSignalGeneration.__name__, 16, 60)
