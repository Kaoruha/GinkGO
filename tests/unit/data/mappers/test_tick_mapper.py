# Upstream: tests/unit/data/mappers/（ADR-010 Mapper TDD）
# Downstream: ginkgo.data.mappers.TickMapper
# Role: TickMapper roundtrip + model_class 动态表 + direction/source int→enum + TypeError 守卫

import datetime
import pytest

from ginkgo.data.mappers import TickMapper
from ginkgo.data.models import MTick
from ginkgo.entities import Tick
from ginkgo.enums import SOURCE_TYPES, TICKDIRECTION_TYPES


class _ConcreteTick(MTick):
    """MTick 是 __abstract__，需具体子类才能实例化（模拟 get_tick_model 动态类）。"""

    __abstract__ = False
    __tablename__ = "_test_tick_concrete"


def _make_tick(**overrides) -> Tick:
    defaults = dict(
        code="SH600000",
        price=10.50,
        volume=100,
        direction=TICKDIRECTION_TYPES.ACTIVESELL,
        timestamp="2026-06-14 10:30:00",
        source=SOURCE_TYPES.SIM,
    )
    defaults.update(overrides)
    return Tick(**defaults)


class TestTickMapperToModel:
    def test_to_model_returns_mtick_via_model_class(self):
        """to_model 经 model_class 形参构造（动态表机制）。"""
        entity = _make_tick()
        model = TickMapper.to_model(entity, _ConcreteTick)
        assert isinstance(model, _ConcreteTick)

    def test_to_model_preserves_core_fields(self):
        entity = _make_tick()
        model = TickMapper.to_model(entity, _ConcreteTick)
        assert model.code == "SH600000"
        assert model.volume == 100
        assert model.price == 10.50

    def test_to_model_default_model_class_is_mtick(self):
        """默认 model_class=MTick（与原码一致，调用方传动态子类）。"""
        # 调用方未传 model_class 时签名默认 MTick；MTick 抽象不可直接实例化，
        # 故仅校验签名默认值存在，不实例化。
        import inspect
        sig = inspect.signature(TickMapper.to_model)
        assert sig.parameters["model_class"].default is MTick


class TestTickMapperFromModel:
    def test_from_model_returns_tick(self):
        entity = _make_tick()
        model = TickMapper.to_model(entity, _ConcreteTick)
        restored = TickMapper.from_model(model)
        assert isinstance(restored, Tick)

    def test_from_model_direction_source_int_to_enum(self):
        """ORM direction/source 存 int，from_model 用 from_int 转回 enum。"""
        model = _ConcreteTick()
        model.code = "SZ000001"
        model.price = 20.0
        model.volume = 200
        model.direction = TICKDIRECTION_TYPES.ACTIVEBUY.value
        model.source = SOURCE_TYPES.SIM.value
        model.timestamp = datetime.datetime(2026, 6, 14, 10, 0, 0)

        restored = TickMapper.from_model(model)
        assert restored.direction == TICKDIRECTION_TYPES.ACTIVEBUY
        assert restored.source == SOURCE_TYPES.SIM

    def test_from_model_typeerror_on_non_mtick(self):
        """原码 from_model 有 isinstance(model, MTick) 守卫。

        动态子类也是 MTick 子类，守卫成立。传非 MTick 实例应 TypeError。
        """
        with pytest.raises(TypeError):
            TickMapper.from_model(object())


class TestTickMapperRoundtrip:
    def test_roundtrip_preserves_core_fields(self):
        """roundtrip code/price/volume/direction/source/timestamp。

        忠实原码：direction 经 validate_input→int→from_int→enum 来回转换无损
        （枚举值对称）。
        """
        entity = _make_tick(direction=TICKDIRECTION_TYPES.ACTIVEBUY)
        model = TickMapper.to_model(entity, _ConcreteTick)
        restored = TickMapper.from_model(model)

        assert restored.code == "SH600000"
        assert restored.volume == 100
        assert restored.price == 10.50
        assert restored.direction == TICKDIRECTION_TYPES.ACTIVEBUY
        assert restored.source == SOURCE_TYPES.SIM

    def test_from_models_batch(self):
        entity = _make_tick()
        model = TickMapper.to_model(entity, _ConcreteTick)
        restored_list = TickMapper.from_models([model, model])
        assert len(restored_list) == 2
        assert all(isinstance(t, Tick) for t in restored_list)
