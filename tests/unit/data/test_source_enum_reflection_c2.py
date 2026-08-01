"""c2 批：source-only CRUD override 删除后，反射 model info 须还原 {'source': SOURCE_TYPES}。

c1 已给 MClickBase.source / MMysqlBase.source 加 info={"enum": SOURCE_TYPES}。
本批四个 CRUD 的 _get_enum_mappings override 仅映射 source，删 override 后靠
_conversion._get_enum_mappings 默认反射还原。分两类：

- **继承型**(adjustfactor/analyzer_record/position)：model 不重声明 source，
  继承自 MClickBase(CH)或 MMysqlBase(MySQL)，反射 __table__.columns["source"]
  取基类 info——零 model 改动。
- **重声明型**(capital_adjustment)：model 重声明 source 列(覆盖继承)，
  须在该列补 info={"enum": SOURCE_TYPES}，反射才命中。

断言删 override 后四 model 反射皆返回 {'source': SOURCE_TYPES}，与原 override 同构。

Run: pytest tests/unit/data/test_source_enum_reflection_c2.py -v -o addopts=""
"""

import pytest

from ginkgo.data.models import (
    MAdjustfactor,
    MAnalyzerRecord,
    MPosition,
    MCapitalAdjustment,
)
from ginkgo.enums import SOURCE_TYPES
from ginkgo.data.crud.mixins._conversion import _Conversion


def _reflect(model_cls):
    """stub 仅给 model_class（避免实例化 CRUD 连库），复用反射默认实现。"""

    class Stub(_Conversion):
        pass

    Stub.model_class = model_cls
    return Stub()._get_enum_mappings()


@pytest.mark.unit
class TestSourceEnumReflectionC2:
    """c2：删 source-only override 后，反射须还原 {'source': SOURCE_TYPES}。"""

    @pytest.mark.parametrize(
        "model_cls,base",
        [
            (MAdjustfactor, "MClickBase"),
            (MAnalyzerRecord, "MClickBase"),
            (MPosition, "MMysqlBase"),
        ],
    )
    def test_inherited_source_info_present(self, model_cls, base):
        """继承型：source 列(继承自 base)携带 info={"enum": SOURCE_TYPES}。"""
        col = model_cls.__table__.columns["source"]
        assert col.info.get("enum") is SOURCE_TYPES, (
            f"{model_cls.__name__} 继承 {base}.source 须带 enum info"
        )

    def test_redeclared_source_info_present(self):
        """重声明型：capital_adjustment 重声明 source 列，须自带 info。"""
        col = MCapitalAdjustment.__table__.columns["source"]
        assert col.info.get("enum") is SOURCE_TYPES

    @pytest.mark.parametrize(
        "model_cls",
        [MAdjustfactor, MAnalyzerRecord, MPosition, MCapitalAdjustment],
    )
    def test_reflection_returns_source_mapping(self, model_cls):
        """反射还原 {'source': SOURCE_TYPES}，与原 override 同构。"""
        mappings = _reflect(model_cls)
        assert mappings.get("source") is SOURCE_TYPES
