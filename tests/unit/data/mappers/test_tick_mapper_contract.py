"""TickMapper 契约 roundtrip 测试（ADR-029 Task 2）。

参照 test_bar_mapper_contract.py 模板，覆盖 Tick Entity↔MTick ORM 全字段映射保真。
tick 是 ValueObject（无 uuid 业务语义）：uuid 由 MClickBase 默认自生成，mapper 不
还原 uuid；source/direction/price/volume/code/timestamp 全程参与 roundtrip。

契约不变量：
- entity_to_model 经 model_class 形参构造（动态 per-code 子类，§Decision 8 保留 adapter）
- entity_to_model 写 code/price/volume/direction/timestamp/source（对齐 MTick 业务字段集）
- model_to_entity 还原上述全部字段（roundtrip 双向保真）
- direction/source 枚举经 validate_input→int→from_int→enum 来回无损
- 默认值：Tick(source 默认 OTHER) → model.source == OTHER.value；direction 默认无（必填）
- TypeError 守卫：model_to_entity 拒绝非 MTick 实例
- 动态表契约：传 model_class=_ConcreteTick 时返回 _ConcreteTick 实例（per-code 分区核心）
"""
import datetime

import pytest

from ginkgo.entities import Tick
from ginkgo.data.mappers import TickMapper
from ginkgo.data.models import MTick
from ginkgo.enums import SOURCE_TYPES, TICKDIRECTION_TYPES


class _ConcreteTick(MTick):
    """MTick 是 __abstract__，需具体子类才能实例化（模拟 get_tick_model 动态类）。"""

    __abstract__ = False
    __tablename__ = "_test_tick_contract_concrete"


def _make_tick(
    source: SOURCE_TYPES = SOURCE_TYPES.SIM,
    direction: TICKDIRECTION_TYPES = TICKDIRECTION_TYPES.ACTIVESELL,
    code: str = "SH600000",
) -> Tick:
    """构造测试 Tick entity（显式 source/direction，避开默认值以测枚举往返）。"""
    return Tick(
        code=code,
        price=10.50,
        volume=100,
        direction=direction,
        timestamp="2026-06-14 10:30:00",
        source=source,
    )


# ----------------------------------------------------------------------
# 动态表 model_class 契约（§Decision 8：mapper 不 lift，调用方传 per-code 子类）
# ----------------------------------------------------------------------
def test_entity_to_model_returns_concrete_subclass_via_model_class():
    """to_model 经 model_class 形参构造动态子类实例（per-code 分区核心行为）。"""
    entity = _make_tick()
    model = TickMapper.entity_to_model(entity, _ConcreteTick)
    assert isinstance(model, _ConcreteTick)
    assert isinstance(model, MTick)  # 子类亦是 MTick


def test_entity_to_model_default_model_class_signature_is_mtick():
    """签名默认 model_class=MTick（抽象，调用方须传具体子类，契约前置告知）。"""
    import inspect

    sig = inspect.signature(TickMapper.entity_to_model)
    assert sig.parameters["model_class"].default is MTick


# ----------------------------------------------------------------------
# 全字段写入契约（entity_to_model）
# ----------------------------------------------------------------------
def test_entity_to_model_writes_code():
    entity = _make_tick(code="SZ000001")
    model = TickMapper.entity_to_model(entity, _ConcreteTick)
    assert model.code == "SZ000001"


def test_entity_to_model_writes_price():
    entity = _make_tick()
    entity._price = 10.50
    model = TickMapper.entity_to_model(entity, _ConcreteTick)
    assert float(model.price) == 10.50


def test_entity_to_model_writes_volume():
    entity = _make_tick()
    model = TickMapper.entity_to_model(entity, _ConcreteTick)
    assert model.volume == 100


def test_entity_to_model_writes_direction_as_int():
    """direction 经 validate_input 存 int（TICKDIRECTION_TYPES.ACTIVEBUY.value=1）。"""
    entity = _make_tick(direction=TICKDIRECTION_TYPES.ACTIVEBUY)
    model = TickMapper.entity_to_model(entity, _ConcreteTick)
    assert model.direction == TICKDIRECTION_TYPES.ACTIVEBUY.value


def test_entity_to_model_writes_source_as_int():
    """source 经 validate_input 存 int。"""
    entity = _make_tick(source=SOURCE_TYPES.TDX)
    model = TickMapper.entity_to_model(entity, _ConcreteTick)
    assert model.source == SOURCE_TYPES.TDX.value


def test_entity_to_model_writes_timestamp():
    entity = _make_tick()
    model = TickMapper.entity_to_model(entity, _ConcreteTick)
    assert model.timestamp == datetime.datetime(2026, 6, 14, 10, 30, 0)


# ----------------------------------------------------------------------
# 默认值契约（source 默认 OTHER）
# ----------------------------------------------------------------------
def test_entity_to_model_source_default_other():
    """Tick 构造不传 source 时默认 OTHER → model.source == OTHER.value(0)。"""
    tick = Tick(
        code="SH600000",
        price=10.50,
        volume=100,
        direction=TICKDIRECTION_TYPES.NEUTRAL,
        timestamp="2026-06-14 10:30:00",
    )
    assert tick.source == SOURCE_TYPES.OTHER  # 前置：Tick 默认
    model = TickMapper.entity_to_model(tick, _ConcreteTick)
    assert model.source == SOURCE_TYPES.OTHER.value


# ----------------------------------------------------------------------
# 还原契约（model_to_entity）
# ----------------------------------------------------------------------
def test_model_to_entity_returns_tick():
    model = TickMapper.entity_to_model(_make_tick(), _ConcreteTick)
    restored = TickMapper.model_to_entity(model)
    assert isinstance(restored, Tick)


def test_model_to_entity_restores_all_fields():
    """model_to_entity 还原 code/price/volume/direction/timestamp/source。"""
    original = _make_tick(
        source=SOURCE_TYPES.AKSHARE,
        direction=TICKDIRECTION_TYPES.ACTIVEBUY,
        code="BJ430090",
    )
    model = TickMapper.entity_to_model(original, _ConcreteTick)
    back = TickMapper.model_to_entity(model)

    assert back.code == "BJ430090"
    assert float(back.price) == 10.50
    assert back.volume == 100
    assert back.direction == TICKDIRECTION_TYPES.ACTIVEBUY
    assert back.timestamp == datetime.datetime(2026, 6, 14, 10, 30, 0)
    assert back.source == SOURCE_TYPES.AKSHARE


def test_model_to_entity_typeerror_on_non_mtick():
    """model_to_entity 拒绝非 MTick 实例（响亮失败，#4652 教训）。"""
    with pytest.raises(TypeError):
        TickMapper.model_to_entity(object())


# ----------------------------------------------------------------------
# 全字段 roundtrip 双向保真（核心契约）
# ----------------------------------------------------------------------
@pytest.mark.parametrize(
    "direction",
    [
        TICKDIRECTION_TYPES.NEUTRAL,
        TICKDIRECTION_TYPES.ACTIVEBUY,
        TICKDIRECTION_TYPES.ACTIVESELL,
        TICKDIRECTION_TYPES.CANCEL,
        TICKDIRECTION_TYPES.FOKIOC,
    ],
)
def test_roundtrip_preserves_direction_enum(direction):
    """direction 枚举 validate_input→int→from_int→enum 来回无损。"""
    entity = _make_tick(direction=direction)
    model = TickMapper.entity_to_model(entity, _ConcreteTick)
    back = TickMapper.model_to_entity(model)
    assert back.direction == direction


@pytest.mark.parametrize(
    "source",
    [
        SOURCE_TYPES.TDX,
        SOURCE_TYPES.SIM,
        SOURCE_TYPES.AKSHARE,
        SOURCE_TYPES.TUSHARE,
        SOURCE_TYPES.TEST,
    ],
)
def test_roundtrip_preserves_source_enum(source):
    """source 枚举 validate_input→int→from_int→enum 来回无损。"""
    entity = _make_tick(source=source)
    model = TickMapper.entity_to_model(entity, _ConcreteTick)
    back = TickMapper.model_to_entity(model)
    assert back.source == source


def test_full_roundtrip_preserves_all_business_fields():
    """entity → model → entity 全业务字段保真（tick VO：uuid 不参与）。"""
    original = _make_tick(
        source=SOURCE_TYPES.BAOSTOCK,
        direction=TICKDIRECTION_TYPES.CANCEL,
        code="SH688999",
    )
    model = TickMapper.entity_to_model(original, _ConcreteTick)
    back = TickMapper.model_to_entity(model)

    assert back.code == original.code
    assert back.price == original.price
    assert back.volume == original.volume
    assert back.direction == original.direction
    assert back.timestamp == original.timestamp
    assert back.source == original.source


# ----------------------------------------------------------------------
# 批量 roundtrip 契约
# ----------------------------------------------------------------------
def test_batch_roundtrip_preserves_fields():
    """models_to_entities 批量还原字段不丢。"""
    entities = [
        _make_tick(source=SOURCE_TYPES.TDX, direction=TICKDIRECTION_TYPES.ACTIVEBUY),
        _make_tick(source=SOURCE_TYPES.SIM, direction=TICKDIRECTION_TYPES.ACTIVESELL),
    ]
    models = [TickMapper.entity_to_model(e, _ConcreteTick) for e in entities]
    restored = TickMapper.models_to_entities(models)
    assert len(restored) == 2
    assert restored[0].source == SOURCE_TYPES.TDX
    assert restored[0].direction == TICKDIRECTION_TYPES.ACTIVEBUY
    assert restored[1].source == SOURCE_TYPES.SIM
    assert restored[1].direction == TICKDIRECTION_TYPES.ACTIVESELL
