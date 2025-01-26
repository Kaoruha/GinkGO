"""
EventBase 模块

该模块定义了一个事件基类，用于表示系统中的各种事件。
事件包含名称、时间戳、UUID、事件类型和来源等属性。
"""

import uuid
import datetime
from abc import abstractmethod, ABCMeta
from ginkgo.enums import EVENT_TYPES, SOURCE_TYPES
from ginkgo.libs import base_repr, datetime_normalize


class EventBase(object, metaclass=ABCMeta):
    """
    事件基类

    用于表示系统中的各种事件。包含以下属性：
    - 名称 (name)
    - 时间戳 (timestamp)
    - UUID (uuid)
    - 事件类型 (event_type)
    - 来源 (source)
    """

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

    @name.setter
    def name(self, name) -> str:
        if not isinstance(name, str):
            raise ValueError("Name must be a string.")
        self._name = name
        return self._name

    def set_name(self, name: str) -> str:
        if not isinstance(name, str):
            raise ValueError("Name must be a string.")
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

    @event_type.setter
    def event_type(self, type: str or EVENT_TYPES) -> None:
        if isinstance(type, EVENT_TYPES):
            self._event_type = type
        elif isinstance(type, str):
            self._event_type = EVENT_TYPES.enum_convert(type)
        else:
            raise ValueError("Type must be a string or an instance of EVENT_TYPES.")

    def set_type(self, type: str or EVENT_TYPES) -> None:
        if isinstance(type, EVENT_TYPES):
            self._event_type = type
        elif isinstance(type, str):
            self._event_type = EVENT_TYPES.enum_convert(type)
        else:
            raise ValueError("Type must be a string or an instance of EVENT_TYPES.")

    def set_time(self, timestamp: any):
        try:
            self._timestamp = datetime_normalize(timestamp)
        except Exception as e:
            raise ValueError(f"Invalid timestamp: {timestamp}. Error: {e}")

    def set_source(self, source: SOURCE_TYPES):
        if not isinstance(source, SOURCE_TYPES):
            raise ValueError("Source must be an instance of SOURCE_TYPES.")
        self._source = source

    def __repr__(self):
        return base_repr(self, EventBase.__name__, 16, 60)
