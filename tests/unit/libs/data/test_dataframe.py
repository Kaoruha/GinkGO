# Upstream: 三根类 Base/ValueObject/MBase 转发调用
# Downstream: None (helper 单测)
# Role: 锁定单一 to_dataframe(obj) helper 契约 (#6861)，替代三份重复实现

"""to_dataframe(obj) 通用序列化 helper 契约测试 (#6861)。

三根类 Base / ValueObject / MBase 原各抄一份 __dir__() 迭代版 to_dataframe；
本测试锁定单一 helper 的契约，供三根类单行转发复用。
"""
import pandas as pd
from enum import Enum

from ginkgo.libs.data.dataframe import to_dataframe


class _Color(Enum):
    RED = 1
    GREEN = 2


class _FakeObj:
    """模拟根类实例：公开/私有/方法/枚举/字符串(含 NUL)属性混合。"""

    def __init__(self):
        self.code = "000001.SZ"           # 普通字符串
        self.dirty = "ab\x00\x00"          # 含尾随 NUL，须 strip
        self.volume = 100
        self.color = _Color.GREEN
        self._private = "hidden"           # 私有，排除
        self.delete = "skip-name"          # 命中跳过名单
        self.to_dataframe = "self-skip"    # 命中跳过名单(同名)

    def calc(self):
        return 1                           # 方法，排除


def test_to_dataframe_serializes_public_attrs_to_single_row():
    """单行 DataFrame；私有/方法/跳过名单排除；Enum→value；str→strip NUL。"""
    df = to_dataframe(_FakeObj())

    assert isinstance(df, pd.DataFrame)
    assert len(df) == 1                       # 单行
    row = df.iloc[0]

    assert row["code"] == "000001.SZ"         # 普通串原样
    assert row["dirty"] == "ab"               # NUL 被 strip（统一契约）
    assert row["volume"] == 100
    assert row["color"] == 2                  # Enum → .value

    # 排除项
    assert "_private" not in df.columns       # 私有
    assert "delete" not in df.columns         # 跳过名单
    assert "to_dataframe" not in df.columns   # 跳过名单(同名)
    assert "calc" not in df.columns           # 方法
