"""BarMapper 契约 roundtrip 测试（ADR-029 Task 1）。

作为 Task 2-5（其余 4 活域）契约测试的模板：纯函数、不依赖 DB session，
覆盖 Entity↔ORM 全字段映射保真，重点锁 source/uuid（旧 _convert_input_item
override 字段集，mapper 此前缺失）。

契约不变量：
- entity_to_model 写 source/uuid（对齐 bar_crud override:81-106 字段集）
- model_to_entity 还原 source/uuid（roundtrip 双向保真）
- 枚举经 __table__ 反射语义不丢（source/frequency int↔enum）
- 默认值链路：Base._source=VOID → model.source=-1 → 还原 VOID
"""
from datetime import datetime
from decimal import Decimal

import pytest

from ginkgo.enums import FREQUENCY_TYPES, SOURCE_TYPES
from ginkgo.entities import Bar
from ginkgo.data.mappers.bar_mapper import BarMapper


def _make_bar(source: SOURCE_TYPES = SOURCE_TYPES.TUSHARE, uuid: str = "") -> Bar:
    """构造测试 Bar entity。uuid 留空让 Base 自动生成（测自动 uuid 保真）。"""
    bar = Bar(
        code="000001.SZ",
        open=10,
        high=11,
        low=9,
        close=10.5,
        volume=1000,
        amount=10500,
        frequency=FREQUENCY_TYPES.DAY,
        timestamp="2025-01-02",
        uuid=uuid,
    )
    bar.set_source(source)
    return bar


# ----------------------------------------------------------------------
# source 字段契约
# ----------------------------------------------------------------------
def test_entity_to_model_writes_source():
    """entity_to_model 写 source（override 现状字段，mapper 修复点）。"""
    bar = _make_bar(source=SOURCE_TYPES.TUSHARE)
    model = BarMapper.entity_to_model(bar)
    assert model.source == SOURCE_TYPES.TUSHARE.value


def test_entity_to_model_source_default_void():
    """未 set_source 时 Base 默认 VOID → model.source == VOID.value(-1)。"""
    bar = Bar(
        code="000001.SZ",
        open=10, high=11, low=9, close=10.5,
        volume=1000, amount=10500,
        frequency=FREQUENCY_TYPES.DAY,
        timestamp="2025-01-02",
    )
    model = BarMapper.entity_to_model(bar)
    assert model.source == SOURCE_TYPES.VOID.value


def test_model_to_entity_restores_source():
    """model_to_entity 还原 source（roundtrip 双向，mapper 修复点）。"""
    model = BarMapper.entity_to_model(_make_bar(source=SOURCE_TYPES.BAOSTOCK))
    back = BarMapper.model_to_entity(model)
    assert back.source == SOURCE_TYPES.BAOSTOCK


# ----------------------------------------------------------------------
# uuid 字段契约
# ----------------------------------------------------------------------
def test_entity_to_model_writes_uuid_explicit():
    """entity_to_model 写 uuid（显式注入值，mapper 修复点）。"""
    bar = _make_bar(uuid="test-uuid-1234")
    model = BarMapper.entity_to_model(bar)
    assert model.uuid == "test-uuid-1234"


def test_entity_to_model_writes_uuid_auto_generated():
    """entity_to_model 写 uuid（Base 自动生成非空，mapper 修复点）。"""
    bar = _make_bar()  # uuid=""，Base 自动生成
    assert bar.uuid  # 前置：Base 确实生成了 uuid
    model = BarMapper.entity_to_model(bar)
    assert model.uuid == bar.uuid
    assert model.uuid  # 非空


def test_model_to_entity_restores_uuid():
    """model_to_entity 还原 uuid（roundtrip 双向，mapper 修复点）。"""
    bar = _make_bar(uuid="roundtrip-uuid-abc")
    model = BarMapper.entity_to_model(bar)
    back = BarMapper.model_to_entity(model)
    assert back.uuid == "roundtrip-uuid-abc"


# ----------------------------------------------------------------------
# 全字段 roundtrip 契约（source/uuid + 业务字段 + 枚举）
# ----------------------------------------------------------------------
def test_full_roundtrip_preserves_all_fields():
    """entity → model → entity 全字段保真（含 source/uuid/枚举）。"""
    original = _make_bar(source=SOURCE_TYPES.AKSHARE, uuid="full-rt-uuid")
    model = BarMapper.entity_to_model(original)
    back = BarMapper.model_to_entity(model)

    # 业务键
    assert back.code == original.code
    assert back.timestamp == original.timestamp
    assert back.frequency == original.frequency
    # OHLCV+amount
    assert back.open == original.open
    assert back.high == original.high
    assert back.low == original.low
    assert back.close == original.close
    assert back.volume == original.volume
    assert back.amount == original.amount
    # 修复点：source/uuid
    assert back.source == original.source
    assert back.uuid == original.uuid


def test_batch_roundtrip_preserves_source_uuid():
    """批量 roundtrip（models_to_entities）source/uuid 不丢。"""
    bars = [
        _make_bar(source=SOURCE_TYPES.TUSHARE, uuid="batch-1"),
        _make_bar(source=SOURCE_TYPES.SINA, uuid="batch-2"),
    ]
    models = [BarMapper.entity_to_model(b) for b in bars]
    restored = BarMapper.models_to_entities(models)
    assert len(restored) == 2
    assert restored[0].source == SOURCE_TYPES.TUSHARE
    assert restored[0].uuid == "batch-1"
    assert restored[1].source == SOURCE_TYPES.SINA
    assert restored[1].uuid == "batch-2"


# ----------------------------------------------------------------------
# 频率枚举契约（既有行为回归保护，不应被 source/uuid 修复破坏）
# ----------------------------------------------------------------------
def test_roundtrip_preserves_frequency_enum():
    """frequency 枚举经 __table__ 反射 int↔enum 保真（回归保护）。"""
    model = BarMapper.entity_to_model(_make_bar())  # _make_bar 默认 DAY
    assert model.frequency == FREQUENCY_TYPES.DAY.value
    back = BarMapper.model_to_entity(model)
    assert back.frequency == FREQUENCY_TYPES.DAY
