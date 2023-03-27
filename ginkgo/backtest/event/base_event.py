import uuid
import datetime
from abc import abstractmethod, ABCMeta
from ginkgo.enums import EVENT_TYPES, SOURCE_TYPES
from ginkgo.libs.ginkgo_pretty import base_repr
from ginkgo.libs.ginkgo_normalize import datetime_normalize


class EventBase(object, metaclass=ABCMeta):
    def __init__(self, *args, **kwargs) -> None:
        super(EventBase, self).__init__(*args, **kwargs)
        self.__timestamp = datetime.datetime.now()
        self.__id = uuid.uuid3(
            uuid.NAMESPACE_DNS, str(datetime.datetime.now()) + EventBase.__name__
        )
        self.__type = None
        self.__source = SOURCE_TYPES.SIM

    @property
    def id(self) -> str:
        return self.__id

    @property
    def source(self) -> SOURCE_TYPES:
        return self.__source

    @source.setter
    def source(self, source: SOURCE_TYPES) -> None:
        self.__source = source

    @property
    def timestamp(self) -> datetime.datetime:
        return self.__timestamp

    @property
    def event_type(self) -> EVENT_TYPES:
        return self.__type

    @event_type.setter
    def event_type(self, event_type) -> None:
        if isinstance(event_type, EVENT_TYPES):
            self.__type = event_type
        elif isinstance(event_type, str):
            self.__type = EVENT_TYPES.enum_convert(event_type)

    def update_time(self, timestamp):
        self.__timestamp = datetime_normalize(timestamp)

    def __repr__(self):
        return base_repr(self, EventBase.__name__, 16, 60)
