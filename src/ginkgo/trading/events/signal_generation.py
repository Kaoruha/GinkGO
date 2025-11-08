from ginkgo.trading.events.base_event import EventBase
from ginkgo.enums import EVENT_TYPES
from ginkgo.trading.entities.signal import Signal
from ginkgo.libs import base_repr


class EventSignalGeneration(EventBase):
    def __init__(self, signal, name: str = "EventSignalGen", *args, **kwargs):
        super(EventSignalGeneration, self).__init__(name, *args, **kwargs)
        self.set_type(EVENT_TYPES.SIGNALGENERATION)
        self._signal = signal

    @property
    def value(self):
        return self._signal

    @property
    def code(self):
        return self.value.code

    @property
    def direction(self):
        return self.value.direction

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
        if self.value is None:
            return self.timestamp
        # 优先使用信号的business_timestamp，这是信号触发的真正业务时间
        if hasattr(self.value, 'business_timestamp') and self.value.business_timestamp is not None:
            return self.value.business_timestamp
        # 回退到信号的timestamp（信号创建时间）
        return self.value.timestamp

    def __repr__(self):
        return base_repr(self, EventSignalGeneration.__name__, 16, 60)
