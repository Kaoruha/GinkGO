"""
EventBase 模块

该模块定义了一个事件基类，用于表示系统中的各种事件。
事件包含名称、时间戳、UUID、事件类型和来源等属性。
"""

import uuid
import datetime
from abc import abstractmethod, ABCMeta
from typing import Optional
from ginkgo.enums import EVENT_TYPES, SOURCE_TYPES
from ginkgo.libs import base_repr, datetime_normalize
from ginkgo.trading.core.backtest_base import BacktestBase
from ginkgo.trading.time.interfaces import ITimeProvider


class EventBase(BacktestBase, metaclass=ABCMeta):
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
        # Extract EventBase-specific parameters before calling super()
        self._time_provider: Optional[ITimeProvider] = kwargs.pop("time_provider", None)
        event_uuid = kwargs.pop("uuid", None)
        engine_id = kwargs.pop("engine_id", None)
        portfolio_id = kwargs.pop("portfolio_id", None)
        run_id = kwargs.pop("run_id", None)
        
        super(EventBase, self).__init__(*args, **kwargs)
        self._name = ""
        self.set_name(name)
        
        # Time provider integration - use provided time_provider or fallback to system time
        if self._time_provider is not None:
            self._timestamp = self._time_provider.now()
        else:
            # Fallback use global clock adapter (tz-aware)
            try:
                from ginkgo.trading.time.clock import now as clock_now
                self._timestamp = clock_now()
            except Exception:
                self._timestamp = datetime.datetime.now(datetime.timezone.utc)
        
        # Set Event UUID（事件自身唯一标识）
        if event_uuid is not None:
            self._uuid = event_uuid
        else:
            self._uuid = uuid.uuid4().hex
            
        # Set engine_id / portfolio_id / run_id
        # 说明：不再为 engine_id/portfolio_id/run_id 生成随机值，统一由引擎/组合在注入时设置，确保关联到真实运行上下文。
        self._engine_id = engine_id if engine_id is not None else None
        self._portfolio_id = portfolio_id if portfolio_id is not None else None
        self._run_id = run_id if run_id is not None else None
            
        self._event_type = None
        self._source = SOURCE_TYPES.SIM
        self._value = None  # 事件载荷数据
        self.context = {}  # 事件元数据容器，用于存储额外信息

    @property
    def portfolio_id(self) -> str:
        return self._portfolio_id

    @portfolio_id.setter
    def portfolio_id(self, value) -> str:
        self._portfolio_id = value

    @property
    def run_id(self) -> str:
        """获取运行ID"""
        return self._run_id

    @run_id.setter
    def run_id(self, value: str) -> None:
        """设置运行ID"""
        if not isinstance(value, str):
            raise ValueError("run_id must be a string.")
        self._run_id = value

    @property
    def engine_id(self) -> str:
        """获取引擎ID"""
        return self._engine_id

    @engine_id.setter
    def engine_id(self, value: str) -> None:
        """设置引擎ID"""
        if not isinstance(value, str):
            raise ValueError("engine_id must be a string.")
        self._engine_id = value

    def set_time_provider(self, time_provider: ITimeProvider) -> None:
        """设置时间提供者并更新时间戳"""
        self._time_provider = time_provider
        self._timestamp = time_provider.now()

    def refresh_timestamp(self) -> None:
        """刷新时间戳（如果有时间提供者）"""
        if self._time_provider is not None:
            self._timestamp = self._time_provider.now()
        else:
            try:
                from ginkgo.trading.time.clock import now as clock_now
                self._timestamp = clock_now()
            except Exception:
                self._timestamp = datetime.datetime.now(datetime.timezone.utc)

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

    @property
    def value(self):
        """获取事件载荷数据"""
        return self._value

    @value.setter
    def value(self, value):
        """设置事件载荷数据"""
        self._value = value

    @property
    def payload(self):
        """获取事件载荷数据（value字段的别名，提供更直观的API）"""
        return self._value

    @payload.setter
    def payload(self, value):
        """设置事件载荷数据（value字段的别名，提供更直观的API）"""
        self._value = value

    def set_value(self, value):
        """设置事件载荷数据（便捷方法）"""
        self._value = value
        return self

    def set_payload(self, value):
        """设置事件载荷数据（便捷方法，payload别名）"""
        self._value = value
        return self

    def __repr__(self):
        return base_repr(self, EventBase.__name__, 16, 60)
