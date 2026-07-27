"""c5 多字段 enum 下沉反射测试(ADR-031)。

验证 4 个多字段 CRUD 的 ``_get_enum_mappings`` override 删除后,BaseCRUD 默认
反射返回的映射与原 override **完全相等**(精确等值)。多字段模型反射集合 =
source(经 c1 继承)+ 各非 source 字段 info 下沉后的 key。
"""

import pytest

from ginkgo.data.crud.mixins._conversion import _Conversion
from ginkgo.data.models import MPortfolio, MStockInfo, MTransfer, MSignalTracker
from ginkgo.enums import (
    SOURCE_TYPES,
    PORTFOLIO_MODE_TYPES,
    PORTFOLIO_RUNSTATE_TYPES,
    MARKET_TYPES,
    CURRENCY_TYPES,
    TRANSFERDIRECTION_TYPES,
    TRANSFERSTATUS_TYPES,
    EXECUTION_MODE,
    ACCOUNT_TYPE,
    DIRECTION_TYPES,
    TRACKINGSTATUS_TYPES,
)


def _reflect(model_cls):
    class Stub(_Conversion):
        pass

    stub = Stub()
    stub.model_class = model_cls
    return stub._get_enum_mappings()


CASES = [
    (
        MPortfolio,
        {"mode": PORTFOLIO_MODE_TYPES, "state": PORTFOLIO_RUNSTATE_TYPES, "source": SOURCE_TYPES},
    ),
    (
        MStockInfo,
        {"market": MARKET_TYPES, "currency": CURRENCY_TYPES, "source": SOURCE_TYPES},
    ),
    (
        MTransfer,
        {
            "direction": TRANSFERDIRECTION_TYPES,
            "status": TRANSFERSTATUS_TYPES,
            "market": MARKET_TYPES,
            "source": SOURCE_TYPES,
        },
    ),
    (
        MSignalTracker,
        {
            "execution_mode": EXECUTION_MODE,
            "account_type": ACCOUNT_TYPE,
            "expected_direction": DIRECTION_TYPES,
            "tracking_status": TRACKINGSTATUS_TYPES,
            "source": SOURCE_TYPES,
        },
    ),
]


@pytest.mark.parametrize("model_cls,expected", CASES)
def test_reflection_exactly_matches_old_override(model_cls, expected):
    """反射映射必须精确等于旧 override 集合(== 非 >=)。

    多余 key = 某 override 曾抑制的 info-enum 列被激活(行为变更);
    缺失 key = 某字段 info 未下沉到位。两种都判红。
    """
    mappings = _reflect(model_cls)
    assert mappings == expected, (
        f"{model_cls.__name__} 反射映射 {mappings!r} != 旧 override {expected!r}"
    )
