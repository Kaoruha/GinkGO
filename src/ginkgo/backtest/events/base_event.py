import uuid
import datetime
from abc import abstractmethod, ABCMeta
from ginkgo.enums import EVENT_TYPES, SOURCE_TYPES
from ginkgo.libs import base_repr, datetime_normalize


class EventBase(object, metaclass=ABCMeta):
    def __init__(self, name: str = "EventBase", *args, **kwargs) -> None:
        super(EventBase, self).__init__(*args, **kwargs)
        self._name = ""
        self.set_name(name)
        self._timestamp = datetime.datetime.now()
        self._uuid = uuid.uuid4().hex
        self._event_type = None
        self._source = SOURCE_TYPES.SIM

    @property
    def name(self) -> str:
        return self._name

    def set_name(self, name: str) -> str:
        self._name = name
        return self._name

    @property
    def uuid(self) -> str:
        return self._uuid

    @property
    def source(self) -> SOURCE_TYPES:
        return self._source

    @property
    def timestamp(self) -> datetime.datetime:
        return self._timestamp

    @property
    def event_type(self) -> EVENT_TYPES:
        return self._event_type

    def set_type(self, type: str or EVENT_TYPES) -> None:
        if isinstance(type, EVENT_TYPES):
            self._event_type = type
        elif isinstance(type, str):
            self._event_type = EVENT_TYPES.enum_convert(type)

    def set_time(self, timestamp: any):
        self._timestamp = datetime_normalize(timestamp)

    def set_source(self, source: SOURCE_TYPES):
        self._source = source

    def __repr__(self):
        return base_repr(self, EventBase.__name__, 16, 60)
