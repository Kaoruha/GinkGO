# Upstream: tests/unit/data/mappers/（ADR-010 Mapper TDD）
# Downstream: ginkgo.data.mappers.SignalMapper
# Role: SignalMapper to_model（ADR-029 阶段1 strict mirror）+ from_model 守卫 + 批量

import pytest

from ginkgo.data.mappers import SignalMapper
from ginkgo.data.models import MSignal
from ginkgo.entities import Signal
from ginkgo.enums import DIRECTION_TYPES, SOURCE_TYPES


def _make_signal(**overrides) -> Signal:
    """按 Signal.__init__ 真实参数构造。"""
    defaults = dict(
        portfolio_id="port-1",
        engine_id="engine-1",
        task_id="task-1",
        code="SH600000",
        direction=DIRECTION_TYPES.LONG,
        reason="test reason",
        source=SOURCE_TYPES.OTHER,
        volume=1000,
        weight=0.5,
        strength=0.7,
        confidence=0.8,
    )
    defaults.update(overrides)
    return Signal(**defaults)


class TestSignalMapperToModel:
    """ADR-029 阶段1:to_model 逐字段对齐 SignalCRUD._convert_input_item(strict mirror)。

    CRUD 写路径不塞 volume/weight/strength/confidence(列存在但写时不填)、不塞 uuid
    (走 MClickBase default)。Mapper 镜像此入库现状——四可选字段不入 MSignal,uuid 自动
    生成 32-hex(非 entity.uuid)。既有 CRUD 写/读不对称(写丢 strength、读路径
    _convert_models_to_business_objects 读 strength)留阶段 3 另立 ADR 修。
    """

    def test_to_model_returns_msignal(self):
        entity = _make_signal()
        model = SignalMapper.to_model(entity)
        assert isinstance(model, MSignal)

    def test_to_model_preserves_core_fields(self):
        """code/direction 保真(CRUD 写路径塞这两字段)。"""
        entity = _make_signal()
        model = SignalMapper.to_model(entity)
        assert model.code == "SH600000"
        assert model.direction == DIRECTION_TYPES.LONG.value

    def test_to_model_drops_optional_signal_fields(self):
        """CRUD 写路径不塞 volume/weight/strength/confidence,Mapper 镜像——四字段为 None。"""
        entity = _make_signal(volume=2000, weight=0.9, strength=0.3, confidence=0.6)
        model = SignalMapper.to_model(entity)
        assert model.volume is None
        assert model.weight is None
        assert model.strength is None
        assert model.confidence is None

    def test_to_model_preserves_uuid_auto_generated(self):
        """去 uuid 透传(镜像 CRUD 不塞),走 MClickBase.uuid default 自动生成 32-hex。"""
        entity = _make_signal()
        model = SignalMapper.to_model(entity)
        assert model.uuid and len(model.uuid) == 32  # 32-hex,非 entity.uuid
        assert model.uuid != entity.uuid

    def test_to_model_preserves_code_direction(self):
        """CRUD 写路径塞 code/direction,Mapper 镜像保真。"""
        entity = _make_signal(code="SZ000001", direction=DIRECTION_TYPES.SHORT)
        model = SignalMapper.to_model(entity)
        assert model.code == "SZ000001"
        assert model.direction == DIRECTION_TYPES.SHORT.value

    def test_to_model_preserves_reason_source(self):
        """CRUD 写路径塞 reason/source,Mapper 镜像保真。source 经 validate_input 转 int。"""
        entity = _make_signal(reason="momentum breakout", source=SOURCE_TYPES.SIM)
        model = SignalMapper.to_model(entity)
        assert model.reason == "momentum breakout"
        assert model.source == SOURCE_TYPES.SIM.value


class TestSignalMapperFromModelGuard:
    def test_from_model_rejects_non_msignal(self):
        with pytest.raises(TypeError):
            SignalMapper.from_model(object())


def _make_msignal(**overrides) -> MSignal:
    """手构 MSignal(strength/confidence 已设),避开 to_model 去塞致 from_model 构造崩。

    真实 CRUD 读路径 _convert_models_to_business_objects 读 strength/confidence,故
    from_model 亦读之;to_model 镜像写路径不塞 → 内存 roundtrip 必崩。from_model 单测
    用手构 model(strength 已设)独立验证读路径。
    """
    m = MSignal()
    m.portfolio_id = overrides.get("portfolio_id", "port-1")
    m.engine_id = overrides.get("engine_id", "engine-1")
    m.task_id = overrides.get("task_id", "task-1")
    m.timestamp = overrides.get("timestamp", "2024-01-15")
    m.code = overrides.get("code", "SH600000")
    m.direction = overrides.get("direction", DIRECTION_TYPES.LONG)
    m.reason = overrides.get("reason", "r")
    m.source = overrides.get("source", SOURCE_TYPES.SIM)
    m.volume = overrides.get("volume", 1000)
    m.weight = overrides.get("weight", 0.5)
    m.strength = overrides.get("strength", 0.7)
    m.confidence = overrides.get("confidence", 0.8)
    return m


class TestSignalMapperFromModels:
    def test_from_models_maps_all(self):
        """from_models 逐个调 from_model,strength/confidence 已设可构造。"""
        models = [_make_msignal(code="A"), _make_msignal(code="B")]
        back = SignalMapper.from_models(models)
        assert len(back) == 2
        assert {b.code for b in back} == {"A", "B"}
