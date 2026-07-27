"""c3 批：12 个 source-only CRUD 删 override 前的安全前置探针。

c1 给 MClickBase.source / MMysqlBase.source 加 info。本批 12 个 CRUD 的
override 仅映射 source，其 model 皆继承自两基类之一且不重声明 source。
删 override 前须证：反射返回【恰好】{'source': SOURCE_TYPES}——

- 含 source：继承基类 info 命中；
- 不含其他：确认无被 override 抑制的额外 info-enum 列（否则删 override
  会激活该列的 enum 校验=行为变更）。

精确等式（==）是安全闸：任一 model 反射出多余键 → 测试红 → 该 model
不进本批，转多字段批单独处理。

Run: pytest tests/unit/data/test_source_enum_reflection_c3.py -v -o addopts=""
"""

import pytest

from ginkgo.data.models import (
    MBrokerInstance,
    MEngineHandlerMapping,
    MEnginePortfolioMapping,
    MHandler,
    MLiveAccount,
    MMarketSubscription,
    MParam,
    MPositionRecord,
    MTickSummary,
    MUserCredential,
    MUserGroup,
    MUserGroupMapping,
)
from ginkgo.enums import SOURCE_TYPES
from ginkgo.data.crud.mixins._conversion import _Conversion


def _reflect(model_cls):
    class Stub(_Conversion):
        pass

    Stub.model_class = model_cls
    return Stub()._get_enum_mappings()


SOURCE_ONLY_MODELS = [
    MBrokerInstance,
    MEngineHandlerMapping,
    MEnginePortfolioMapping,
    MHandler,
    MLiveAccount,
    MMarketSubscription,
    MParam,
    MPositionRecord,
    MTickSummary,
    MUserCredential,
    MUserGroup,
    MUserGroupMapping,
]


@pytest.mark.unit
class TestSourceOnlyReflectionC3:
    """12 个 source-only model 反射须恰好返回 {'source': SOURCE_TYPES}。"""

    @pytest.mark.parametrize("model_cls", SOURCE_ONLY_MODELS)
    def test_reflection_exactly_source_only(self, model_cls):
        """精确等式：反射 == {'source': SOURCE_TYPES}，无多余 info-enum 列。"""
        mappings = _reflect(model_cls)
        assert mappings == {"source": SOURCE_TYPES}, (
            f"{model_cls.__name__} 反射 {mappings!r} 非 source-only —— "
            f"有多余 info-enum 列被 override 抑制，删 override 会激活=行为变更，须转多字段批"
        )
