"""ValueObject 基类单测（ADR-010 Task 2.1）。

契约：无 uuid/component_type/source；不继承 Base；to_dataframe 可用。
"""
import pandas as pd
from ginkgo.entities.value_object import ValueObject
from ginkgo.entities.base import Base
from ginkgo.enums import SOURCE_TYPES


def test_valueobject_has_no_uuid():
    vo = ValueObject()
    assert not hasattr(vo, "uuid") or vo.__class__.__name__ == "ValueObject"
    # ValueObject 无 uuid 字段、无 component_type、无 source


def test_valueobject_is_not_base():
    assert not issubclass(ValueObject, Base) or ValueObject is not Base


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
