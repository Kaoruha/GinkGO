"""ValueObject 基类单测（ADR-010 Task 2.1）。

契约：无 uuid/component_type/source；不继承 Base；to_dataframe 可用。
"""
import pandas as pd
from ginkgo.entities.value_object import ValueObject
from ginkgo.entities.base import Base
from ginkgo.enums import SOURCE_TYPES


def test_valueobject_has_no_uuid():
    vo = ValueObject()
    assert not hasattr(vo, "uuid")
    assert not hasattr(vo, "_uuid")
    assert not hasattr(vo, "_component_type")
    assert not hasattr(vo, "_source")


def test_valueobject_is_not_base():
    assert not issubclass(ValueObject, Base)


def test_valueobject_to_dataframe_works_on_subclass():
    """真契约：VO 子类继承 to_dataframe 仍能产出 DataFrame（Task 2.2 依赖此）。"""

    class FakeVO(ValueObject):
        def __init__(self):
            self.code = "000001.SZ"
            self.price = 10.5

    df = FakeVO().to_dataframe()
    assert isinstance(df, pd.DataFrame)
    assert df.iloc[0]["code"] == "000001.SZ"
    assert float(df.iloc[0]["price"]) == 10.5


def test_valueobject_convert_helpers_work_on_subclass():
    """_convert_* 静态方法对子类实例可用（Task 2.2 依赖）。"""

    class FakeVO(ValueObject):
        pass

    vo = FakeVO()
    assert vo._convert_to_float("3.14") == 3.14
    assert vo._convert_to_int("7") == 7
    assert vo._convert_to_bool(1) is True


def test_valueobject_to_dataframe_handles_enum_and_str():
    """to_dataframe 的 Enum→value 与 str 分支（与 Base 同源契约）。"""

    class FakeVO(ValueObject):
        def __init__(self):
            self.kind = SOURCE_TYPES.SIM  # Enum 分支
            self.code = "  000001.SZ"  # 普通字符串（无空字节，strip 不改）

    df = FakeVO().to_dataframe()
    assert int(df.iloc[0]["kind"]) == int(SOURCE_TYPES.SIM.value)
    assert df.iloc[0]["code"] == "  000001.SZ"
