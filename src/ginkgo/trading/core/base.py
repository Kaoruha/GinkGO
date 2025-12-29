# Upstream: 所有Ginkgo组件实体(Signal/Order/Position/Strategy/Portfolio/Engine/Risk等)
# Downstream: IdentityUtils(UUID生成工具)、pandas(DataFrame转换)、SOURCE_TYPES/COMPONENT_TYPES枚举(数据源和组件类型)
# Role: Base抽象基类为所有Ginkgo组件提供统一的基础标识功能支持UUID管理/组件类型标识/数据源管理/DataFrame转换






import pandas as pd

from types import FunctionType, MethodType
from enum import Enum

from ginkgo.enums import SOURCE_TYPES, COMPONENT_TYPES


class Base(object):
    """
    Enhanced Base Class with Component Type Support
    
    为所有Ginkgo组件提供统一的基础标识功能，支持：
    - UUID管理（实例唯一标识）
    - 组件类型标识
    - 数据源管理
    - DataFrame转换功能
    """

    def __init__(self, uuid: str = "", component_type: COMPONENT_TYPES = COMPONENT_TYPES.VOID, *args, **kwargs):
        from .identity import IdentityUtils
        
        self._source = SOURCE_TYPES.VOID
        self._component_type = component_type
        
        # 自动生成UUID如果未提供
        if uuid:
            self._uuid = uuid
        else:
            # 将枚举转换为友好的前缀
            prefix = self._get_component_prefix(component_type)
            self._uuid = IdentityUtils.generate_component_uuid(prefix)

    @property
    def uuid(self, *args, **kwargs) -> str:
        return self._uuid

    @uuid.setter
    def uuid(self, uuid: str, *args, **kwargs) -> str:
        if not isinstance(uuid, str):
            raise ValueError("UUID must be a string.")
        self._uuid = uuid
        return self._uuid

    def set_uuid(self, uuid: str, *args, **kwargs) -> str:
        if not isinstance(uuid, str):
            raise ValueError("UUID must be a string.")
        self._uuid = uuid
        return self._uuid

    def _get_component_prefix(self, component_type: COMPONENT_TYPES) -> str:
        """
        将组件类型枚举转换为友好的UUID前缀

        Args:
            component_type (COMPONENT_TYPES): 组件类型枚举

        Returns:
            str: 友好的前缀字符串
        """
        # 定义枚举到前缀的映射
        prefix_map = {
            COMPONENT_TYPES.VOID: "void",
            COMPONENT_TYPES.SIGNAL: "signal",
            COMPONENT_TYPES.ORDER: "order",
            COMPONENT_TYPES.POSITION: "position",
            COMPONENT_TYPES.BAR: "bar",
            COMPONENT_TYPES.TICK: "tick",
            COMPONENT_TYPES.STRATEGY: "strategy",
            COMPONENT_TYPES.PORTFOLIO: "portfolio",
            COMPONENT_TYPES.ENGINE: "engine",
            COMPONENT_TYPES.RISK: "risk",
            COMPONENT_TYPES.STOCKINFO: "stockinfo",
            COMPONENT_TYPES.ADJUSTFACTOR: "adjustfactor",
            COMPONENT_TYPES.TRADEDAY: "tradeday",
            COMPONENT_TYPES.TRANSFER: "transfer"
        }

        return prefix_map.get(component_type, "component")

    @property
    def component_type(self) -> COMPONENT_TYPES:
        """组件类型标识"""
        return self._component_type

    @property
    def source(self):
        return self._source

    @source.setter
    def source(self, value):
        if not isinstance(value, SOURCE_TYPES):
            raise ValueError("Source must be a valid SOURCE_TYPES enum.")
        self._source = value

    def set_source(self, source: SOURCE_TYPES):
        self._source = source

    def to_dataframe(self) -> pd.DataFrame:
        """
        Convert Object's parameters to DataFrame.
        Args:
            None
        Returns:
            A dataframe convert from this.
        """
        item = {}
        methods = ["delete", "query", "registry", "metadata", "to_dataframe"]
        for param in self.__dir__():
            if param in methods:
                continue
            if param.startswith("_"):
                continue
            if isinstance(self.__getattribute__(param), MethodType):
                continue
            if isinstance(self.__getattribute__(param), FunctionType):
                continue

            if isinstance(self.__getattribute__(param), Enum):
                item[param] = self.__getattribute__(param).value
            elif isinstance(self.__getattribute__(param), str):
                item[param] = self.__getattribute__(param).strip(b"\x00".decode())
            else:
                item[param] = self.__getattribute__(param)

        df = pd.DataFrame.from_dict(item, orient="index").transpose()
        return df

    def _convert_to_float(self, value, default: float = 0.0) -> float:
        """
        将值转换为浮点数，处理从数据库传来的字符串参数

        Args:
            value: 需要转换的值
            default: 转换失败时的默认值

        Returns:
            float: 转换后的浮点数
        """
        if value is None:
            return default

        if isinstance(value, float):
            return value

        if isinstance(value, int):
            return float(value)

        if isinstance(value, str):
            try:
                return float(value)
            except (ValueError, TypeError):
                return default

        return default

    def _convert_to_int(self, value, default: int = 0) -> int:
        """
        将值转换为整数，处理从数据库传来的字符串参数

        Args:
            value: 需要转换的值
            default: 转换失败时的默认值

        Returns:
            int: 转换后的整数
        """
        if value is None:
            return default

        if isinstance(value, int):
            return value

        if isinstance(value, float):
            return int(value)

        if isinstance(value, str):
            try:
                return int(float(value))  # 支持"3.0"这样的字符串
            except (ValueError, TypeError):
                return default

        return default

    def _convert_to_bool(self, value, default: bool = False) -> bool:
        """
        将值转换为布尔值，处理从数据库传来的字符串参数

        Args:
            value: 需要转换的值
            default: 转换失败时的默认值

        Returns:
            bool: 转换后的布尔值
        """
        if value is None:
            return default

        if isinstance(value, bool):
            return value

        if isinstance(value, (int, float)):
            return bool(value)

        if isinstance(value, str):
            lower_val = value.lower().strip()
            if lower_val in ('true', '1', 'yes', 'on'):
                return True
            elif lower_val in ('false', '0', 'no', 'off'):
                return False
            else:
                return default

        return default
