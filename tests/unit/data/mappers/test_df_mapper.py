"""``_df.models_to_dataframe`` 单测（ADR-029 §Decision 9 DF 出口）。

覆盖 ``src/ginkgo/data/mappers/_df.py`` 全部可执行行：
- ``models_to_dataframe``：空列表 / 有 enum 的 model / 无 enum / ``_sa_instance_state``
  剔除 / 只读 enum 字段 setattr 跳过
- ``_get_enum_mappings_from_model``：反射 enum 映射 / 无 ``__table__`` 对象
- ``_safe_enum_convert``：None / 有效值 / 无效值
"""
from types import SimpleNamespace

import pandas as pd

from ginkgo.entities import Bar
from ginkgo.enums import FREQUENCY_TYPES
from ginkgo.data.mappers.bar_mapper import BarMapper
from ginkgo.data.mappers._df import (
    models_to_dataframe,
    _get_enum_mappings_from_model,
    _safe_enum_convert,
)


def _make_model():
    return BarMapper.entity_to_model(
        Bar(
            code="000001.SZ",
            open=10,
            high=11,
            low=9,
            close=10.5,
            volume=1000,
            amount=10500,
            frequency=FREQUENCY_TYPES.DAY,
            timestamp="2025-01-02",
        )
    )


def test_empty_list_returns_empty_dataframe():
    """空列表 → ``pd.DataFrame()``（L63-64）。"""
    result = models_to_dataframe([])
    assert result.empty


def test_basic_conversion_strips_sa_instance_state():
    """普通 model → DataFrame，``_sa_instance_state`` 必被 pop（L84-88）。"""
    df = models_to_dataframe([_make_model()])
    assert not df.empty
    assert "code" in df.columns
    assert df.iloc[0]["code"] == "000001.SZ"
    assert "_sa_instance_state" not in df.columns


def test_enum_reflection_converts_frequency():
    """``MBar.frequency`` 是 enum 字段；反射映射后 in-place 转 enum（L67-81）。"""
    model = _make_model()
    mappings = _get_enum_mappings_from_model(model)
    assert "frequency" in mappings
    df = models_to_dataframe([model])
    assert "frequency" in df.columns
    # 锁 in-place 转 enum(L70-81):删转换块则 frequency 列存 int64(非 enum),断言 FAIL。
    assert isinstance(df.iloc[0]["frequency"], FREQUENCY_TYPES)


def test_get_enum_mappings_object_without_table():
    """无 ``__table__`` 的普通对象 → ``{}``（L26-28）。"""
    class Plain:
        pass

    assert _get_enum_mappings_from_model(Plain()) == {}


def test_safe_enum_convert_none_valid_invalid():
    """None→None；有效值→enum；无效值→原样返回（except 分支 L43-44）。"""
    assert _safe_enum_convert(None, FREQUENCY_TYPES) is None
    assert _safe_enum_convert(FREQUENCY_TYPES.DAY.value, FREQUENCY_TYPES) == FREQUENCY_TYPES.DAY
    assert _safe_enum_convert(-9999, FREQUENCY_TYPES) == -9999


def test_readonly_enum_attribute_skipped():
    """只读 enum 字段 ``setattr`` 抛 ``AttributeError`` → 跳过（L77-81）。

    ``__table__.columns`` 反射到 frequency→enum 映射，但实例的 ``frequency`` 是
    只读 property（无 setter），in-place ``setattr`` 触发 ``AttributeError`` 被 except 吞掉。
    """
    table = SimpleNamespace(
        columns=[SimpleNamespace(name="frequency", info={"enum": FREQUENCY_TYPES})]
    )

    class ReadonlyEnumModel:
        __table__ = table

        def __init__(self):
            self.code = "x"
            self._sa_instance_state = object()

        @property
        def frequency(self):  # 只读 property（无 setter）→ setattr 抛 AttributeError
            return 1

    df = models_to_dataframe([ReadonlyEnumModel()])
    # 只读字段被跳过，不抛异常；code 仍在
    assert "code" in df.columns
    assert df.iloc[0]["code"] == "x"


def test_no_enum_mappings_short_circuits_loop():
    """``enum_mappings`` 为空 → 跳过 enum 循环（L70）。"""
    table = SimpleNamespace(columns=[SimpleNamespace(name="code", info=None)])

    class NoEnumModel:
        __table__ = table

        def __init__(self):
            self.code = "y"
            self._sa_instance_state = object()

    df = models_to_dataframe([NoEnumModel()])
    assert df.iloc[0]["code"] == "y"
