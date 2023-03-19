import uuid
import datetime
from abc import abstractmethod, ABCMeta
from ginkgo.backtest.enums import EventType, Source
from ginkgo.libs.ginkgo_pretty import pretty_repr
from ginkgo.libs.ginkgo_normalize import datetime_normalize


class EventBase(object, metaclass=ABCMeta):
    def __init__(self, *args, **kwargs) -> None:
        super(EventBase, self).__init__(*args, **kwargs)
        self.__timestamp = datetime.datetime.now()
        self.__id = uuid.uuid3(
            uuid.NAMESPACE_DNS, str(self.timestamp) + EventBase.__name__
        )
        self.__type = None
        self.__source = Source.SIM

    @property
    def id(self) -> str:
        return self.__id

    @property
    def source(self) -> Source:
        return self.__source

    @source.setter
    def source(self, source: Source) -> None:
        self.__source = source

    @property
    def timestamp(self) -> datetime.datetime:
        return self.__timestamp

    @property
    def event_type(self) -> EventType:
        return self.__type

    @event_type.setter
    def event_type(self, event_type) -> None:
        if isinstance(event_type, EventType):
            self.__type = event_type
        elif isinstance(event_type, str):
            self.__type = EventType.enum_convert(event_type)

    def update_time(self, timestamp):
        self.__timestamp = datetime_normalize(timestamp)

    def __repr__(self):
        mem = f"Mem   : {hex(id(self))}"
        event_id = f"ID    : {self.id}"
        date = f"Date  : {self.timestamp}"
        event_t = f"Type  : {self.event_type} : {self.event_type.value}"
        source = f"Source: {self.source} : {self.source.value}"
        msg = [mem, event_id, date, event_t, source]
        return pretty_repr(EventBase.__name__, msg, 50)
