"""PositionMapper 契约 roundtrip 测试(ADR-029 Task 5)。

锁定 Position Entity ↔ MPosition ORM 全字段映射保真,重点断言:
- **source 不丢**:Entity source(SOURCE_TYPES 枚举)→ model.source(int)→ Entity source 还原无损
- **business_timestamp 不丢**:Entity business_timestamp → model.business_timestamp → Entity 还原

契约不变量:
- entity_to_model 写全部业务字段(code/cost/volume/frozen_*/settlement_*/fee/price/portfolio_id/engine_id/task_id)
  + source(经 set_source→validate_input 存 int)+ business_timestamp(datetime_normalize)
- model_to_entity 还原上述全部字段(uuid 保留 + source/business_timestamp 双向保真)
- source 枚举经 validate_input→int→from_int→enum 来回无损(VOID/-1、OTHER/0、SIM/1、LIVE/16 等)
- 默认值:Position(source 默认 VOID)→ model.source == VOID.value(-1);business_timestamp 默认 None → model.business_timestamp is None
- TypeError 守卫:model_to_entity 拒绝非 MPosition 实例(#4652 响亮失败教训)
- batch roundtrip 批量还原字段不丢
"""
import datetime

import pytest

from ginkgo.data.mappers import PositionMapper
from ginkgo.data.models import MPosition
from ginkgo.entities import Position
from ginkgo.enums import SOURCE_TYPES


def _make_position(
    source: SOURCE_TYPES = SOURCE_TYPES.SIM,
    business_timestamp=None,
    code: str = "SH600000",
) -> Position:
    """构造测试 Position entity。

    `source` 经 setter 注入(Position 构造器 source kwarg 经实测被 Base 静默吞,
    走 setter 才生效)。`business_timestamp` 经 TimeMixin 接受 kwarg。
    显式 source 避开默认 VOID 以测非默认枚举往返。
    business_timestamp 默认 None(若传值则验证往返保真)。
    """
    pos = Position(
        portfolio_id="port-1",
        engine_id="engine-1",
        task_id="task-1",
        code=code,
        cost=10.5,
        volume=1000,
        frozen_volume=200,
        settlement_frozen_volume=50,
        settlement_days=1,
        frozen_money=2100,
        price=10.8,
        fee=5.25,
        business_timestamp=business_timestamp,
    )
    pos.source = source  # 构造后 setter 注入(Base source kwarg 被吞,实测)
    return pos


# ----------------------------------------------------------------------
# 全字段写入契约(entity_to_model)
# ----------------------------------------------------------------------
def test_entity_to_model_returns_mposition():
    entity = _make_position()
    model = PositionMapper.entity_to_model(entity)
    assert isinstance(model, MPosition)


def test_entity_to_model_writes_core_business_fields():
    entity = _make_position(code="SZ000001")
    model = PositionMapper.entity_to_model(entity)
    assert model.portfolio_id == "port-1"
    assert model.engine_id == "engine-1"
    assert model.task_id == "task-1"
    assert model.code == "SZ000001"
    assert int(model.volume) == 1000
    assert int(model.frozen_volume) == 200
    assert int(model.settlement_frozen_volume) == 50
    assert int(model.settlement_days) == 1
    assert float(model.cost) == 10.5
    assert float(model.frozen_money) == 2100
    assert float(model.price) == 10.8
    assert float(model.fee) == 5.25


def test_entity_to_model_writes_source_as_int():
    """source 经 set_source→validate_input 存 int(SOURCE_TYPES.SIM.value=1)。"""
    entity = _make_position(source=SOURCE_TYPES.SIM)
    model = PositionMapper.entity_to_model(entity)
    assert model.source == SOURCE_TYPES.SIM.value


def test_entity_to_model_writes_business_timestamp():
    """business_timestamp 经 datetime_normalize 存 datetime。"""
    ts = datetime.datetime(2026, 6, 14, 10, 30, 0)
    entity = _make_position(business_timestamp=ts)
    model = PositionMapper.entity_to_model(entity)
    assert model.business_timestamp == ts


# ----------------------------------------------------------------------
# 默认值契约(source 默认 VOID;business_timestamp 默认 None)
# ----------------------------------------------------------------------
def test_entity_to_model_source_default_void():
    """Position 构造不传 source 时默认 VOID → model.source == VOID.value(-1)。

    VOID.value=-1 经 validate_input 返回 -1(`result if result is not None else -1`),
    不被 falsy 吞(VOID 非 0,但本测同时守护 SOURCE_TYPES.OTHER=0 路径:OTHER 测下条)。
    """
    pos = Position(
        portfolio_id="port-1", engine_id="engine-1", task_id="task-1",
        code="SH600000",
    )
    assert pos.source == SOURCE_TYPES.VOID  # 前置:Position 默认
    model = PositionMapper.entity_to_model(pos)
    assert model.source == SOURCE_TYPES.VOID.value


def test_entity_to_model_source_other_value_zero_not_swallowed():
    """SOURCE_TYPES.OTHER.value=0(合法值)经 set_source 不被 falsy 吞成 -1。

    守护 Task 2 tick 系统性发现「`validate_input(...) or -1` 吞 0」模式:position 路径
    用 `result if result is not None else -1`(MMysqlBase.set_source),正确区分 None 与 0。
    """
    pos = Position(
        portfolio_id="port-1", engine_id="engine-1", task_id="task-1",
        code="SH600000",
    )
    pos.source = SOURCE_TYPES.OTHER  # setter 注入(Base kwarg 被吞)
    model = PositionMapper.entity_to_model(pos)
    assert model.source == 0  # 不被吞成 -1


def test_entity_to_model_business_timestamp_none_default():
    """Position 不传 business_timestamp 时默认 None → model.business_timestamp is None。"""
    pos = Position(
        portfolio_id="port-1", engine_id="engine-1", task_id="task-1",
        code="SH600000",
    )
    assert pos.business_timestamp is None  # 前置
    model = PositionMapper.entity_to_model(pos)
    assert model.business_timestamp is None


# ----------------------------------------------------------------------
# 还原契约(model_to_entity)
# ----------------------------------------------------------------------
def test_model_to_entity_returns_position():
    model = PositionMapper.entity_to_model(_make_position())
    restored = PositionMapper.model_to_entity(model)
    assert isinstance(restored, Position)


def test_model_to_entity_restores_core_fields():
    original = _make_position(code="BJ430090")
    model = PositionMapper.entity_to_model(original)
    back = PositionMapper.model_to_entity(model)
    assert back.portfolio_id == "port-1"
    assert back.code == "BJ430090"
    assert int(back.volume) == 1000
    assert float(back.cost) == 10.5


def test_model_to_entity_restores_source():
    """model_to_entity 还原 source(int → SOURCE_TYPES 枚举)。"""
    original = _make_position(source=SOURCE_TYPES.AKSHARE)
    model = PositionMapper.entity_to_model(original)
    back = PositionMapper.model_to_entity(model)
    assert back.source == SOURCE_TYPES.AKSHARE


def test_model_to_entity_restores_business_timestamp():
    """model_to_entity 还原 business_timestamp(datetime 保真)。"""
    ts = datetime.datetime(2026, 6, 14, 10, 30, 0)
    original = _make_position(business_timestamp=ts)
    model = PositionMapper.entity_to_model(original)
    back = PositionMapper.model_to_entity(model)
    assert back.business_timestamp == ts


def test_model_to_entity_typeerror_on_non_mposition():
    """model_to_entity 拒绝非 MPosition 实例(响亮失败,#4652 教训)。"""
    with pytest.raises(TypeError):
        PositionMapper.model_to_entity(object())


# ----------------------------------------------------------------------
# source 全枚举 roundtrip 双向保真(核心契约)
# ----------------------------------------------------------------------
@pytest.mark.parametrize(
    "source",
    [
        SOURCE_TYPES.VOID,    # -1 边界值
        SOURCE_TYPES.OTHER,   # 0 falsy 陷阱守护
        SOURCE_TYPES.SIM,     # 1 常用默认
        SOURCE_TYPES.TDX,
        SOURCE_TYPES.AKSHARE,
        SOURCE_TYPES.TUSHARE,
        SOURCE_TYPES.LIVE,    # 16 实盘
        SOURCE_TYPES.BACKTEST,
    ],
)
def test_roundtrip_preserves_source_enum(source):
    """source 枚举 set_source→int→from_int→enum 来回无损(含 -1/0 边界)。"""
    entity = _make_position(source=source)
    model = PositionMapper.entity_to_model(entity)
    back = PositionMapper.model_to_entity(model)
    assert back.source == source


# ----------------------------------------------------------------------
# business_timestamp roundtrip 双向保真
# ----------------------------------------------------------------------
def test_roundtrip_preserves_business_timestamp():
    """business_timestamp 全链路保真:Entity → Model → Entity。"""
    ts = datetime.datetime(2026, 6, 14, 10, 30, 0)
    original = _make_position(business_timestamp=ts)
    model = PositionMapper.entity_to_model(original)
    back = PositionMapper.model_to_entity(model)
    assert back.business_timestamp == ts


def test_roundtrip_preserves_business_timestamp_none():
    """business_timestamp=None 时 roundtrip 仍 None(不被默认值污染)。"""
    original = _make_position(business_timestamp=None)
    model = PositionMapper.entity_to_model(original)
    back = PositionMapper.model_to_entity(model)
    assert back.business_timestamp is None


# ----------------------------------------------------------------------
# 全字段 roundtrip 双向保真
# ----------------------------------------------------------------------
def test_full_roundtrip_preserves_all_business_fields():
    """entity → model → entity 全业务字段保真(含 source + business_timestamp)。"""
    ts = datetime.datetime(2026, 6, 14, 10, 30, 0)
    original = _make_position(
        source=SOURCE_TYPES.LIVE,
        business_timestamp=ts,
        code="SH688999",
    )
    model = PositionMapper.entity_to_model(original)
    back = PositionMapper.model_to_entity(model)

    assert back.portfolio_id == original.portfolio_id
    assert back.engine_id == original.engine_id
    assert back.task_id == original.task_id
    assert back.code == original.code
    assert int(back.volume) == int(original.volume)
    assert int(back.frozen_volume) == int(original.frozen_volume)
    assert float(back.cost) == float(original.cost)
    assert float(back.price) == float(original.price)
    assert float(back.fee) == float(original.fee)
    # 关键:source + business_timestamp 不丢(本 ADR Task 5 核心断言)
    assert back.source == original.source
    assert back.business_timestamp == original.business_timestamp


# ----------------------------------------------------------------------
# batch roundtrip 契约
# ----------------------------------------------------------------------
def test_batch_roundtrip_preserves_source_and_business_timestamp():
    """models_to_entities 批量还原 source/business_timestamp 不丢。"""
    ts1 = datetime.datetime(2026, 6, 14, 10, 30, 0)
    ts2 = datetime.datetime(2026, 6, 15, 14, 0, 0)
    entities = [
        _make_position(source=SOURCE_TYPES.SIM, business_timestamp=ts1, code="A"),
        _make_position(source=SOURCE_TYPES.LIVE, business_timestamp=ts2, code="B"),
    ]
    models = [PositionMapper.entity_to_model(e) for e in entities]
    restored = PositionMapper.models_to_entities(models)
    assert len(restored) == 2
    assert restored[0].source == SOURCE_TYPES.SIM
    assert restored[0].business_timestamp == ts1
    assert restored[1].source == SOURCE_TYPES.LIVE
    assert restored[1].business_timestamp == ts2
