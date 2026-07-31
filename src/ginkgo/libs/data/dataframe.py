# Upstream: Base / ValueObject / MBase 三根类(转发调用)
# Downstream: pandas(DataFrame)
# Role: 单一 to_dataframe(obj) helper —— 将任意对象的公开属性序列化为单行 DataFrame。
#       替代三根类各自抄写的 __dir__() 迭代版 (#6861)。

"""to_dataframe(obj) —— 对象公开属性 → 单行 DataFrame 的单一实现 (#6861)。

此前 Base / ValueObject / MBase 各抄一份近乎相同的 __dir__() 迭代逻辑，
跳过名单 (delete/query/registry/metadata/to_dataframe) 三处重复。本模块收敛为单一
helper，三根类退化为单行转发；跳过名单单点归属。

行为契约：
- 排除私有属性 (``_`` 前缀)、方法 (MethodType/FunctionType)、跳过名单内的同名属性；
- Enum 属性取 ``.value``；
- str 属性 strip 尾随 NUL (``\\x00``，防 DB 返回的空字节填充)；对无 NUL 的正常串为 no-op。
"""

import pandas as pd
from types import FunctionType, MethodType
from enum import Enum

# 跳过名单单点归属：与 ORM/SQLAlchemy 框架方法及本 helper 同名属性冲突，统一排除。
_TO_DATAFRAME_SKIP = frozenset(
    {"delete", "query", "registry", "metadata", "to_dataframe"}
)


def to_dataframe(obj) -> pd.DataFrame:
    """将 ``obj`` 的公开属性序列化为单行 DataFrame。

    Args:
        obj: 任意对象（典型为 Base / ValueObject / MBase 子类实例）。

    Returns:
        pandas.DataFrame: 单行，列 = 公开属性名，值按 Enum→value / str→strip NUL 规整。
    """
    item = {}
    for param in obj.__dir__():
        if param in _TO_DATAFRAME_SKIP or param.startswith("_"):
            continue
        attr = obj.__getattribute__(param)
        if isinstance(attr, (MethodType, FunctionType)):
            continue
        if isinstance(attr, Enum):
            item[param] = attr.value
        elif isinstance(attr, str):
            item[param] = attr.strip("\x00")
        else:
            item[param] = attr
    return pd.DataFrame.from_dict(item, orient="index").transpose()
