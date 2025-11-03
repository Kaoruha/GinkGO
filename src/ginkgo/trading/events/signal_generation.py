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
        业务数据时间戳 - 返回信号数据的时间，如果没有信号数据则返回事件时间
        """
        return self.value.timestamp if self.value else self.timestamp

    def __repr__(self):
        return base_repr(self, EventSignalGeneration.__name__, 16, 60)
