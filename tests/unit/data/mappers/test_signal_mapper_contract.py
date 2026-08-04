"""SignalMapper 契约 roundtrip 测试 (ADR-029 Task 6)。

锁定 Signal Entity ↔ MSignal ORM 全字段映射保真,重点断言:
- **business_timestamp 不丢**:Entity business_timestamp → model.business_timestamp → Entity 还原
- **source 不丢**:Entity source(SOURCE_TYPES 枚举)→ model.source(int)→ Entity source 还原无损
- **uuid 不丢**:Entity uuid → model.uuid → Entity uuid 还原(原 mapper 自承丢失 bug)

契约不变量:
- entity_to_model 写全部业务字段(portfolio_id/engine_id/task_id/code/direction/reason/
  volume/weight/strength/confidence)+ source(经 set_source→validate_input 存 int)
  + business_timestamp(datetime_normalize)+ uuid(赋值保留)
- model_to_entity 还原上述全部字段(uuid 还原 + source/business_timestamp 双向保真)
- source 枚举经 validate_input→int→from_int→enum 来回无损(VOID/-1、OTHER/0、SIM/1、
  STRATEGY/12、RISK/22、LIVE/16 等)
- direction 同理(DIRECTION_TYPES.LONG/SHORT/OTHER/VOID)
- 默认值:Signal(source 默认 OTHER)→ model.source == OTHER.value(0);business_timestamp
  默认 None → model.business_timestamp is None
- **OTHER=0 不被 falsy 吞**:守护 MSignal.update `validate_input(...) or -1` bug
  (Task 2/3 同款 I-2 系统性先例,本 task 顺修)
- TypeError 守卫:model_to_entity 拒绝非 MSignal 实例(#4652 响亮失败教训)
- batch roundtrip 批量还原字段不丢
"""
import datetime

import pytest

from ginkgo.data.mappers import SignalMapper
from ginkgo.data.models import MSignal
from ginkgo.entities import Signal
from ginkgo.enums import DIRECTION_TYPES, SOURCE_TYPES


def _make_signal(
    source: SOURCE_TYPES = SOURCE_TYPES.SIM,
    direction: DIRECTION_TYPES = DIRECTION_TYPES.LONG,
    business_timestamp=None,
    code: str = "SH600000",
    uuid: str = "",
) -> Signal:
    """构造测试 Signal entity。

    `source`/`direction` 经构造器 kwarg 注入(Signal 构造器接受枚举)。
    `business_timestamp` 经 TimeMixin kwag 接受。`uuid` 经 Base kwarg 注入(空则自动生成)。
    """
    return Signal(
        portfolio_id="port-1",
        engine_id="engine-1",
        task_id="task-1",
        code=code,
        direction=direction,
        reason="test reason",
        source=source,
        volume=1000,
        weight=0.5,
        strength=0.7,
        confidence=0.8,
        uuid=uuid,
        business_timestamp=business_timestamp,
    )


# ----------------------------------------------------------------------
# 全字段写入契约 (entity_to_model)
# ----------------------------------------------------------------------
def test_entity_to_model_returns_msignal():
    entity = _make_signal()
    model = SignalMapper.entity_to_model(entity)
    assert isinstance(model, MSignal)


def test_entity_to_model_writes_core_business_fields():
    entity = _make_signal(code="SZ000001", direction=DIRECTION_TYPES.SHORT)
    model = SignalMapper.entity_to_model(entity)
    assert model.portfolio_id == "port-1"
    assert model.engine_id == "engine-1"
    assert model.task_id == "task-1"
    assert model.code == "SZ000001"
    assert model.direction == DIRECTION_TYPES.SHORT.value
    assert model.reason == "test reason"
    assert int(model.volume) == 1000
    assert float(model.weight) == 0.5
    assert float(model.strength) == 0.7
    assert float(model.confidence) == 0.8


def test_entity_to_model_writes_source_as_int():
    """source 经 set_source→validate_input 存 int(SOURCE_TYPES.SIM.value=1)。"""
    entity = _make_signal(source=SOURCE_TYPES.SIM)
    model = SignalMapper.entity_to_model(entity)
    assert model.source == SOURCE_TYPES.SIM.value


def test_entity_to_model_writes_business_timestamp():
    """business_timestamp 经 datetime_normalize 存 datetime(原 mapper 漏写,Task 6 补)。"""
    ts = datetime.datetime(2026, 8, 2, 10, 30, 0)
    entity = _make_signal(business_timestamp=ts)
    model = SignalMapper.entity_to_model(entity)
    assert model.business_timestamp == ts


def test_entity_to_model_preserves_uuid():
    """entity_to_model 给 ORM 赋 entity.uuid(原码行为保留)。"""
    entity = _make_signal(uuid="abc123ff")
    model = SignalMapper.entity_to_model(entity)
    assert model.uuid == "abc123ff"


# ----------------------------------------------------------------------
# 默认值契约 (source 默认 OTHER; business_timestamp 默认 None)
# ----------------------------------------------------------------------
def test_entity_to_model_source_default_other_not_swallowed():
    """Signal 构造不传 source 时默认 OTHER(value=0)→ model.source == 0(不被 or 吞成 -1)。

    守护 Task 2/3 系统性发现「`validate_input(...) or -1` 吞 0」模式:signal 路径
    MSignal.update line 79 同款 bug。0 是 SOURCE_TYPES.OTHER 合法值,falsy `or` 误判为
    缺失。Task 6 修为 `validated if validated is not None else -1`。
    """
    sig = Signal(
        portfolio_id="port-1",
        engine_id="engine-1",
        task_id="task-1",
        code="SH600000",
        direction=DIRECTION_TYPES.LONG,
        reason="test",
    )
    assert sig.source == SOURCE_TYPES.OTHER  # 前置:Signal 默认 source
    model = SignalMapper.entity_to_model(sig)
    assert model.source == 0  # 不被吞成 -1


def test_entity_to_model_direction_other_value_zero_not_swallowed():
    """DIRECTION_TYPES.OTHER.value=0(合法值)经 update 不被 falsy 吞成 -1。

    同上 I-2 守护:MSignal.update line 75 同款 bug。
    """
    sig = _make_signal(direction=DIRECTION_TYPES.OTHER)
    model = SignalMapper.entity_to_model(sig)
    assert model.direction == 0  # 不被吞成 -1


def test_entity_to_model_business_timestamp_none_default():
    """Signal 不传 business_timestamp 时默认 None → model.business_timestamp is None。"""
    sig = Signal(
        portfolio_id="port-1",
        engine_id="engine-1",
        task_id="task-1",
        code="SH600000",
        direction=DIRECTION_TYPES.LONG,
        reason="test",
    )
    assert sig.business_timestamp is None  # 前置
    model = SignalMapper.entity_to_model(sig)
    assert model.business_timestamp is None


# ----------------------------------------------------------------------
# 还原契约 (model_to_entity)
# ----------------------------------------------------------------------
def test_model_to_entity_returns_signal():
    model = SignalMapper.entity_to_model(_make_signal())
    restored = SignalMapper.model_to_entity(model)
    assert isinstance(restored, Signal)


def test_model_to_entity_restores_core_fields():
    original = _make_signal(code="BJ430090", direction=DIRECTION_TYPES.SHORT)
    model = SignalMapper.entity_to_model(original)
    back = SignalMapper.model_to_entity(model)
    assert back.portfolio_id == "port-1"
    assert back.engine_id == "engine-1"
    assert back.task_id == "task-1"
    assert back.code == "BJ430090"
    assert back.direction == DIRECTION_TYPES.SHORT
    assert back.reason == "test reason"
    assert int(back.volume) == 1000
    assert float(back.weight) == 0.5
    assert float(back.strength) == 0.7
    assert float(back.confidence) == 0.8


def test_model_to_entity_restores_source():
    """model_to_entity 还原 source(int → SOURCE_TYPES 枚举)。"""
    original = _make_signal(source=SOURCE_TYPES.AKSHARE)
    model = SignalMapper.entity_to_model(original)
    back = SignalMapper.model_to_entity(model)
    assert back.source == SOURCE_TYPES.AKSHARE


def test_model_to_entity_restores_business_timestamp():
    """model_to_entity 还原 business_timestamp(datetime 保真,Task 6 补)。"""
    ts = datetime.datetime(2026, 8, 2, 10, 30, 0)
    original = _make_signal(business_timestamp=ts)
    model = SignalMapper.entity_to_model(original)
    back = SignalMapper.model_to_entity(model)
    assert back.business_timestamp == ts


def test_model_to_entity_restores_uuid():
    """model_to_entity 还原 uuid(原 mapper 自承丢失,Task 6 补)。"""
    original = _make_signal(uuid="deadbeef1234")
    model = SignalMapper.entity_to_model(original)
    back = SignalMapper.model_to_entity(model)
    assert back.uuid == "deadbeef1234"


def test_model_to_entity_typeerror_on_non_msignal():
    """model_to_entity 拒绝非 MSignal 实例(响亮失败,#4652 教训)。"""
    with pytest.raises(TypeError):
        SignalMapper.model_to_entity(object())


# ----------------------------------------------------------------------
# source 全枚举 roundtrip 双向保真(核心契约)
# ----------------------------------------------------------------------
@pytest.mark.parametrize(
    "source",
    [
        SOURCE_TYPES.VOID,    # -1 边界值
        SOURCE_TYPES.OTHER,   # 0 falsy 陷阱守护
        SOURCE_TYPES.SIM,     # 1 常用默认
        SOURCE_TYPES.TUSHARE,
        SOURCE_TYPES.AKSHARE,
        SOURCE_TYPES.STRATEGY,  # 12 策略信号(回测主路径)
        SOURCE_TYPES.RISK,      # 22 风控信号(ADR-011 seam)
        SOURCE_TYPES.LIVE,      # 16 实盘
        SOURCE_TYPES.BACKTEST,
    ],
)
def test_roundtrip_preserves_source_enum(source):
    """source 枚举 set_source→int→from_int→enum 来回无损(含 -1/0 边界)。"""
    entity = _make_signal(source=source)
    model = SignalMapper.entity_to_model(entity)
    back = SignalMapper.model_to_entity(model)
    assert back.source == source


# ----------------------------------------------------------------------
# direction 全枚举 roundtrip 双向保真
# ----------------------------------------------------------------------
@pytest.mark.parametrize(
    "direction",
    [
        DIRECTION_TYPES.VOID,   # -1
        DIRECTION_TYPES.OTHER,  # 0 falsy 陷阱守护
        DIRECTION_TYPES.LONG,   # 1
        DIRECTION_TYPES.SHORT,  # 2
    ],
)
def test_roundtrip_preserves_direction_enum(direction):
    """direction 枚举 update→int→from_int→enum 来回无损(含 -1/0 边界)。"""
    entity = _make_signal(direction=direction)
    model = SignalMapper.entity_to_model(entity)
    back = SignalMapper.model_to_entity(model)
    assert back.direction == direction


# ----------------------------------------------------------------------
# business_timestamp roundtrip 双向保真
# ----------------------------------------------------------------------
def test_roundtrip_preserves_business_timestamp():
    """business_timestamp 全链路保真:Entity → Model → Entity。"""
    ts = datetime.datetime(2026, 8, 2, 10, 30, 0)
    original = _make_signal(business_timestamp=ts)
    model = SignalMapper.entity_to_model(original)
    back = SignalMapper.model_to_entity(model)
    assert back.business_timestamp == ts


def test_roundtrip_preserves_business_timestamp_none():
    """business_timestamp=None 时 roundtrip 仍 None(不被默认值污染)。"""
    original = _make_signal(business_timestamp=None)
    model = SignalMapper.entity_to_model(original)
    back = SignalMapper.model_to_entity(model)
    assert back.business_timestamp is None


# ----------------------------------------------------------------------
# uuid roundtrip 双向保真(核心契约,原 mapper 自承丢失)
# ----------------------------------------------------------------------
def test_roundtrip_preserves_uuid():
    """uuid 全链路保真:Entity → Model → Entity(原 mapper 漏还原,Task 6 补)。"""
    original = _make_signal(uuid="cafe1234abcd")
    model = SignalMapper.entity_to_model(original)
    back = SignalMapper.model_to_entity(model)
    assert back.uuid == "cafe1234abcd"


# ----------------------------------------------------------------------
# 全字段 roundtrip 双向保真
# ----------------------------------------------------------------------
def test_full_roundtrip_preserves_all_business_fields():
    """entity → model → entity 全业务字段保真(含 source + business_timestamp + uuid)。"""
    ts = datetime.datetime(2026, 8, 2, 10, 30, 0)
    original = _make_signal(
        source=SOURCE_TYPES.STRATEGY,
        direction=DIRECTION_TYPES.LONG,
        business_timestamp=ts,
        code="SH688999",
        uuid="ff0099aabb",
    )
    model = SignalMapper.entity_to_model(original)
    back = SignalMapper.model_to_entity(model)

    assert back.portfolio_id == original.portfolio_id
    assert back.engine_id == original.engine_id
    assert back.task_id == original.task_id
    assert back.code == original.code
    assert back.direction == original.direction
    assert back.reason == original.reason
    assert int(back.volume) == int(original.volume)
    assert float(back.weight) == float(original.weight)
    assert float(back.strength) == float(original.strength)
    assert float(back.confidence) == float(original.confidence)
    # 关键:source + business_timestamp + uuid 不丢(本 ADR Task 6 核心断言)
    assert back.source == original.source
    assert back.business_timestamp == original.business_timestamp
    assert back.uuid == original.uuid


# ----------------------------------------------------------------------
# batch roundtrip 契约
# ----------------------------------------------------------------------
def test_batch_roundtrip_preserves_source_business_timestamp_uuid():
    """models_to_entities 批量还原 source/business_timestamp/uuid 不丢。"""
    ts1 = datetime.datetime(2026, 8, 2, 10, 30, 0)
    ts2 = datetime.datetime(2026, 8, 3, 14, 0, 0)
    entities = [
        _make_signal(source=SOURCE_TYPES.SIM, business_timestamp=ts1, code="A", uuid="u1"),
        _make_signal(source=SOURCE_TYPES.RISK, business_timestamp=ts2, code="B", uuid="u2"),
    ]
    models = [SignalMapper.entity_to_model(e) for e in entities]
    restored = SignalMapper.models_to_entities(models)
    assert len(restored) == 2
    assert restored[0].source == SOURCE_TYPES.SIM
    assert restored[0].business_timestamp == ts1
    assert restored[0].uuid == "u1"
    assert restored[1].source == SOURCE_TYPES.RISK
    assert restored[1].business_timestamp == ts2
    assert restored[1].uuid == "u2"
