# Upstream: tests/unit/data/mappers/（ADR-010 Mapper TDD）
# Downstream: ginkgo.data.mappers.SignalMapper
# Role: SignalMapper roundtrip + TypeError 守卫测试

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


class TestSignalMapperRoundtrip:
    def test_to_model_returns_msignal(self):
        entity = _make_signal()
        model = SignalMapper.to_model(entity)
        assert isinstance(model, MSignal)

    def test_to_model_preserves_core_fields(self):
        entity = _make_signal()
        model = SignalMapper.to_model(entity)
        assert model.code == "SH600000"
        assert model.direction == DIRECTION_TYPES.LONG.value
        assert model.volume == 1000
        assert model.weight == 0.5
        assert model.strength == 0.7
        assert model.confidence == 0.8

    def test_to_model_preserves_uuid(self):
        """原码 to_model 给 ORM 赋 entity.uuid（保留此行为）。"""
        entity = _make_signal()
        model = SignalMapper.to_model(entity)
        assert model.uuid == entity.uuid

    def test_roundtrip_code_direction(self):
        entity = _make_signal(code="SZ000001", direction=DIRECTION_TYPES.SHORT)
        model = SignalMapper.to_model(entity)
        back = SignalMapper.from_model(model)
        assert back.code == "SZ000001"
        assert back.direction == DIRECTION_TYPES.SHORT

    def test_roundtrip_optional_fields(self):
        entity = _make_signal(volume=2000, weight=0.9, strength=0.3, confidence=0.6)
        model = SignalMapper.to_model(entity)
        back = SignalMapper.from_model(model)
        assert back.volume == 2000
        assert back.weight == 0.9
        assert back.strength == 0.3
        assert back.confidence == 0.6

    def test_roundtrip_reason_source(self):
        entity = _make_signal(reason="momentum breakout", source=SOURCE_TYPES.SIM)
        model = SignalMapper.to_model(entity)
        back = SignalMapper.from_model(model)
        assert back.reason == "momentum breakout"


class TestSignalMapperFromModelGuard:
    def test_from_model_rejects_non_msignal(self):
        with pytest.raises(TypeError):
            SignalMapper.from_model(object())


class TestSignalMapperFromModels:
    def test_from_models_maps_all(self):
        entities = [_make_signal(code="A"), _make_signal(code="B")]
        models = [SignalMapper.to_model(e) for e in entities]
        back = SignalMapper.from_models(models)
        assert len(back) == 2
        assert {b.code for b in back} == {"A", "B"}
