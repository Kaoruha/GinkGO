from ginkgo.backtest.execution.events.base_event import EventBase
from ginkgo.enums import EVENT_TYPES
from ginkgo.backtest.entities.signal import Signal
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
        return self.value.timestamp

    def __repr__(self):
        return base_repr(self, EventSignalGeneration.__name__, 16, 60)
