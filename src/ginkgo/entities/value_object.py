"""ValueObject — 无领域身份的值载体基类（ADR-010）。

与 Entity(Base) 区别：无 uuid / 无 component_type / 无 source。
VO 由字段值描述，不持有状态机；持久化时 uuid 由 ORM default 生成，不污染领域。
"""
import pandas as pd
from types import FunctionType, MethodType
from enum import Enum

from ginkgo.libs.data.number import convert_to_float as _f
from ginkgo.libs.data.number import convert_to_int as _i
from ginkgo.libs.data.number import convert_to_bool as _b


class ValueObject:
    """无身份的领域值载体。"""

    def to_dataframe(self) -> pd.DataFrame:
        item = {}
        skip = {"delete", "query", "registry", "metadata", "to_dataframe"}
        for param in self.__dir__():
            if param in skip or param.startswith("_"):
                continue
            attr = self.__getattribute__(param)
            if isinstance(attr, (MethodType, FunctionType)):
                continue
            if isinstance(attr, Enum):
                item[param] = attr.value
            elif isinstance(attr, str):
                item[param] = attr.strip(b"\x00".decode())
            else:
                item[param] = attr
        return pd.DataFrame.from_dict(item, orient="index").transpose()

    _convert_to_float = staticmethod(_f)
    _convert_to_int = staticmethod(_i)
    _convert_to_bool = staticmethod(_b)
