"""ValueObject — 无领域身份的值载体基类（ADR-010）。

与 Entity(Base) 区别：无 uuid / 无 component_type / 无 source。
VO 由字段值描述，不持有状态机；持久化时 uuid 由 ORM default 生成，不污染领域。
"""
import pandas as pd

from ginkgo.libs.data.dataframe import to_dataframe as _to_dataframe
from ginkgo.libs.data.number import convert_to_float as _f
from ginkgo.libs.data.number import convert_to_int as _i
from ginkgo.libs.data.number import convert_to_bool as _b


class ValueObject:
    """无身份的领域值载体。"""

    def to_dataframe(self) -> pd.DataFrame:
        return _to_dataframe(self)

    _convert_to_float = staticmethod(_f)
    _convert_to_int = staticmethod(_i)
    _convert_to_bool = staticmethod(_b)
