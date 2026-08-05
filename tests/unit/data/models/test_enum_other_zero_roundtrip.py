"""回归:M2 — `validate_input(x) or -1` 吞掉 value-0 枚举成员。

`EnumBase.validate_input` 对 value-0 成员(多为 OTHER=0;TICKDIRECTION.NEUTRAL=0;
ENGINESTATUS.IDLE=0)返回 0。旧代码 `validate_input(x) or -1` 因 `0 or -1 == -1`
把合法的 0 吞成 VOID(-1),DB 存 −1、读回变 VOID → roundtrip 断裂。

修复(`validated = validate_input(x); x = validated if validated is not None else -1`)
保留 0、仅对 None(无效输入)兜底 -1。本测试锁住该语义,防再被简化回 `or -1`。
"""
import pytest

from ginkgo.enums import (
    SOURCE_TYPES,
    DIRECTION_TYPES,
    FREQUENCY_TYPES,
    MARKET_TYPES,
    TICKDIRECTION_TYPES,
    ORDER_TYPES,
    ORDERSTATUS_TYPES,
    ENGINESTATUS_TYPES,
)
from ginkgo.data.models import MBar, MSignal

# 受影响 enum 及其 value-0 成员名(均会被旧 `or -1` 误吞)
VALUE_ZERO = [
    (SOURCE_TYPES, "OTHER"),
    (DIRECTION_TYPES, "OTHER"),
    (FREQUENCY_TYPES, "OTHER"),
    (MARKET_TYPES, "OTHER"),
    (TICKDIRECTION_TYPES, "NEUTRAL"),
    (ORDER_TYPES, "OTHER"),
    (ORDERSTATUS_TYPES, "OTHER"),
    (ENGINESTATUS_TYPES, "IDLE"),
]


@pytest.mark.parametrize("enum_cls,member", VALUE_ZERO)
def test_validate_input_preserves_value_zero(enum_cls, member):
    """validate_input 对 value-0 成员必须返回 0(非 None,非被吞)。"""
    assert enum_cls[member].value == 0
    assert enum_cls.validate_input(enum_cls[member]) == 0
    assert enum_cls.validate_input(0) == 0


def test_old_or_idiom_swallowed_zero():
    """锁证旧 idiom 的 bug:`0 or -1 == -1`(回归动机)。"""
    v = SOURCE_TYPES.validate_input(SOURCE_TYPES.OTHER)
    assert v == 0
    assert (v or -1) == -1  # 旧:吞 0


def test_new_idiom_keeps_zero():
    """新 idiom 保留 0。"""
    v = SOURCE_TYPES.validate_input(SOURCE_TYPES.OTHER)
    assert (v if v is not None else -1) == 0


def test_invalid_input_falls_back_to_minus_one():
    """无效输入(validate_input 返 None)仍兜底 -1,不破坏既有契约。"""
    v = SOURCE_TYPES.validate_input("not_a_valid_source")
    assert v is None
    assert (v if v is not None else -1) == -1


def test_mbar_source_other_roundtrips():
    """模型层:MBar(source=OTHER).source == 0(非 −1)。"""
    m = MBar(code="000001.SZ", frequency=FREQUENCY_TYPES.DAY, source=SOURCE_TYPES.OTHER)
    assert m.source == 0


def test_msignal_direction_other_roundtrips():
    """模型层:MSignal(direction=OTHER).direction == 0。"""
    s = MSignal(code="000001.SZ", direction=DIRECTION_TYPES.OTHER)
    assert s.direction == 0
