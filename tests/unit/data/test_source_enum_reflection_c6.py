"""c6 异常模型 enum 下沉反射测试(ADR-031)。

c6 处理 4 个 ``_get_enum_mappings`` override 含 **dead key**(键名不匹配任何真实列,
``hasattr(item, field)`` 恒 False → 从未生效)的异常模型。本测试覆盖其中 **可下沉** 的
3 个;``file`` / ``tick`` 因故保留 override(见模块底部例外说明)。

下沉口径 = **行为保持**:只 sink override 中 *真正生效* 的映射(真实列名),dead key
维持不 sink。理由:dead key 是 pre-existing bug(作者意图映射但键名拼错,如 ``order``→
实为 ``order_type``、``transferdirection``→实为 ``direction``),修复它会激活这些列的
int→enum 实例转换(EnumBase 非 IntEnum,下游 int 比较会断)= 行为变更,应单独 PR 带下游
核对,不在纯下沉重构中混入(#4652 纪律)。
"""

import pytest

from ginkgo.data.crud.mixins._conversion import _Conversion
from ginkgo.data.models import MOrderRecord, MTransferRecord, MPortfolioFileMapping
from ginkgo.enums import DIRECTION_TYPES, SOURCE_TYPES, MARKET_TYPES


def _reflect(model_cls):
    class Stub(_Conversion):
        pass

    stub = Stub()
    stub.model_class = model_cls
    return stub._get_enum_mappings()


# 期望 = 旧 override 的 *有效* 部分(dead key 已剔除,因它们从未生效):
# - MOrderRecord 旧 {'direction','order','orderstatus','source'} → 'order'/'orderstatus' dead → 有效 {'direction','source'}
# - MTransferRecord 旧 {'capitaladjustment','market','source','transferdirection','transferstatus'} → 3 个 dead → 有效 {'market','source'}
# - MPortfolioFileMapping 旧 {'source','file'} → 'file' dead → 有效 {'source'}
CASES = [
    (MOrderRecord, {"direction": DIRECTION_TYPES, "source": SOURCE_TYPES}),
    (MTransferRecord, {"market": MARKET_TYPES, "source": SOURCE_TYPES}),
    (MPortfolioFileMapping, {"source": SOURCE_TYPES}),
]


@pytest.mark.parametrize("model_cls,expected", CASES)
def test_reflection_exactly_matches_effective_old_override(model_cls, expected):
    """反射映射必须精确等于旧 override 的 *有效* 集合(== 非 >=)。

    多余 key = 某 dead key 被意外 sink(行为变更,违背纯重构);
    缺失 key = 某有效字段 info 未下沉到位。两种都判红。
    """
    mappings = _reflect(model_cls)
    assert mappings == expected, (
        f"{model_cls.__name__} 反射映射 {mappings!r} != 有效旧 override {expected!r}"
    )


# ---------------------------------------------------------------------------
# 例外:以下 2 模型 *保留* override,不参与反射下沉(非反射迁移候选)
# ---------------------------------------------------------------------------
# - MTick:__abstract__=True 的 SA 抽象模型无 __table__,BaseCRUD 默认反射走
#   __table__.columns 对抽象模型返 {},故 Tick 保留 override 作真值源。
# - MFile:override 有意只含 {'type': FILE_TYPES}、不含 source;若删 override,source 经
#   c1 继承会被激活(int→SOURCE_TYPES 实例),这是 file 独有的 source-unmapped 行为变更。
#   统一 source 需先核下游 file.source 消费者,故本 PR 保留 override。
