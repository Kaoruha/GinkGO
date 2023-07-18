import uuid
import datetime
from abc import abstractmethod, ABCMeta
from ginkgo.enums import EVENT_TYPES, SOURCE_TYPES
from ginkgo.libs import base_repr, datetime_normalize, gen_uuid4


class EventBase(object, metaclass=ABCMeta):
    def __init__(self, *args, **kwargs) -> None:
        super(EventBase, self).__init__(*args, **kwargs)
        self._timestamp = datetime.datetime.now()
        self._uuid = gen_uuid4()
        self._type = None
        self._source = SOURCE_TYPES.SIM

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
    def type(self) -> EVENT_TYPES:
        return self._type

    @type.setter
    def type(self, type: str or EVENT_TYPES) -> None:
        if isinstance(type, EVENT_TYPES):
            self._type = type
        elif isinstance(type, str):
            self._type = EVENT_TYPES.enum_convert(type)

    def update_time(self, timestamp: str or datetime.datetime):
        self._timestamp = datetime_normalize(timestamp)

    def set_source(self, source: SOURCE_TYPES):
        self._source = source

    def __repr__(self):
        return base_repr(self, EventBase.__name__, 16, 60)
