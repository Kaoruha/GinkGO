"""c4 单非 source 字段 enum 下沉反射测试(ADR-031)。

验证 7 个 CRUD 的 ``_get_enum_mappings`` override 删除后，BaseCRUD 默认反射
返回的映射与原 override **完全相等**(精确等值，非子集)——既证明非 source
字段 info 已下沉到 model，又证明未被 override 抑制的多余 info-enum 列被激活
(若有，精确等值会红)。

source 经 c1 由 MClickBase/MMysqlBase 继承(已带 info)，本批 7 model 仅新增 1
个非 source 字段 info，反射集合 = {<field>: <ENUM>, 'source': SOURCE_TYPES}。
"""

import pytest

from ginkgo.data.crud.mixins._conversion import _Conversion
from ginkgo.data.models import (
    MBar,
    MEngine,
    MFactor,
    MTradeDay,
    MUser,
    MUserContact,
)
from ginkgo.enums import (
    SOURCE_TYPES,
    FREQUENCY_TYPES,
    ENGINESTATUS_TYPES,
    ENTITY_TYPES,
    MARKET_TYPES,
    USER_TYPES,
    CONTACT_TYPES,
)


def _reflect(model_cls):
    """用裸 _Conversion 反射 model_class 的 enum 映射(绕过 CRUD 业务层)。"""

    class Stub(_Conversion):
        pass

    stub = Stub()
    stub.model_class = model_cls
    return stub._get_enum_mappings()


CASES = [
    (MBar, "frequency", FREQUENCY_TYPES),
    (MEngine, "status", ENGINESTATUS_TYPES),
    (MFactor, "entity_type", ENTITY_TYPES),
    (MTradeDay, "market", MARKET_TYPES),
    (MUser, "user_type", USER_TYPES),
    (MUserContact, "contact_type", CONTACT_TYPES),
]


@pytest.mark.parametrize("model_cls,field,enum_cls", CASES)
def test_reflection_exactly_matches_old_override(model_cls, field, enum_cls):
    """反射映射必须精确等于 {field: enum, source: SOURCE_TYPES}。

    精确等值(== 非 >=)防两类回归:
    - field 的 info 未下沉 → 缺该 key → 红;
    - 某 override 曾抑制的其它 info-enum 列被激活 → 多 key → 红。
    """
    mappings = _reflect(model_cls)
    expected = {field: enum_cls, "source": SOURCE_TYPES}
    assert mappings == expected, (
        f"{model_cls.__name__} 反射映射 {mappings!r} != 旧 override {expected!r};"
        f" 多余 key 意味曾抑制的 info-enum 列被激活(行为变更),缺失 key 意味 info 未下沉"
    )


@pytest.mark.parametrize("model_cls,field,enum_cls", CASES)
def test_field_info_present_on_column(model_cls, field, enum_cls):
    """非 source 字段 info 直接挂在 model 列声明上(下沉到位)。"""
    col = model_cls.__table__.columns[field]
    assert (col.info or {}).get("enum") is enum_cls, (
        f"{model_cls.__name__}.{field} 列未带 info['enum']={enum_cls.__name__}"
    )
