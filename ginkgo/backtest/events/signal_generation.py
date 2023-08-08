from ginkgo.backtest.events.base_event import EventBase
from ginkgo.enums import EVENT_TYPES
from ginkgo.backtest.signal import Signal


class EventSigalGeneration(EventBase):
    def __init__(self, signal, *args, **kwargs):
        super(EventSigalGeneration, self).__init__(*args, **kwargs)
        self.event_type = EVENT_TYPES.SIGNALGENERATION
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
