# Upstream: tests/unit/data/mappers/（ADR-010 Mapper TDD）
# Downstream: ginkgo.data.mappers.AdjustfactorMapper
# Role: AdjustfactorMapper roundtrip + TypeError 守卫测试

import datetime

import pytest

from ginkgo.data.mappers import AdjustfactorMapper
from ginkgo.data.models import MAdjustfactor
from ginkgo.entities import Adjustfactor


def _make_adjustfactor(**overrides) -> Adjustfactor:
    """按 Adjustfactor.__init__ 真实参数构造。"""
    defaults = dict(
        code="SH600000",
        timestamp="2024-01-15",
        fore_adjustfactor=1.23,
        back_adjustfactor=0.81,
        adjustfactor=1.0,
    )
    defaults.update(overrides)
    return Adjustfactor(**defaults)


class TestAdjustfactorMapperRoundtrip:
    def test_to_model_returns_madjustfactor(self):
        entity = _make_adjustfactor()
        model = AdjustfactorMapper.to_model(entity, MAdjustfactor)
        assert isinstance(model, MAdjustfactor)

    def test_to_model_preserves_code_and_uuid(self):
        entity = _make_adjustfactor()
        model = AdjustfactorMapper.to_model(entity, MAdjustfactor)
        # code/uuid 字段名匹配 MAdjustfactor，正确 setattr
        assert model.code == "SH600000"
        assert model.uuid == entity.uuid

    def test_roundtrip_preserves_code_timestamp_uuid(self):
        """roundtrip 还原 code/timestamp/uuid（from_model 还原 uuid）。

        注意：原码 to_model 用 fore_adjustfactor（带下划线）传 MAdjustfactor，
        但 ORM 字段名是 foreadjustfactor（无下划线），无自定义 __init__，
        MClickBase.__init__ 的 hasattr setattr 会静默丢弃——故 adjustfactor
        三字段在 ORM 侧为默认值，roundtrip 不可保真。这是原码已知问题，留 Task 1.6
        抹内嵌方法时统一评估，本测试不断言 adjustfactor 字段保真。
        """
        entity = _make_adjustfactor(
            code="SZ000001",
            timestamp="2024-06-01 10:00:00",
        )
        model = AdjustfactorMapper.to_model(entity, MAdjustfactor)
        restored = AdjustfactorMapper.from_model(model)

        assert restored.code == "SZ000001"
        assert restored.uuid == entity.uuid


class TestAdjustfactorMapperTypeError:
    def test_from_model_rejects_non_madjustfactor(self):
        with pytest.raises(TypeError) as exc:
            AdjustfactorMapper.from_model("not a model")
        assert "MAdjustfactor" in str(exc.value)


class TestAdjustfactorMapperFromModels:
    def test_from_models_maps_list(self):
        entity = _make_adjustfactor()
        model = AdjustfactorMapper.to_model(entity, MAdjustfactor)
        results = AdjustfactorMapper.from_models([model, model])
        assert len(results) == 2
        assert all(isinstance(r, Adjustfactor) for r in results)
