# Upstream: tests/unit/data/mappers/（ADR-010 Mapper TDD）
# Downstream: ginkgo.data.mappers.CapitalAdjustmentMapper
# Role: CapitalAdjustmentMapper roundtrip + TypeError 守卫 + source 转换测试

from decimal import Decimal

import pytest

from ginkgo.data.mappers import CapitalAdjustmentMapper
from ginkgo.data.models import MCapitalAdjustment
from ginkgo.entities import CapitalAdjustment
from ginkgo.enums import SOURCE_TYPES


def _make_capital(**overrides) -> CapitalAdjustment:
    """按 CapitalAdjustment.__init__ 真实参数构造。"""
    defaults = dict(
        portfolio_id="port-1",
        amount=Decimal("10000.5"),
        timestamp="2024-01-15 10:00:00",
        reason="deposit",
        source=SOURCE_TYPES.SIM,
    )
    defaults.update(overrides)
    return CapitalAdjustment(**defaults)


class TestCapitalAdjustmentMapperRoundtrip:
    def test_to_model_returns_mcapitaladjustment(self):
        entity = _make_capital()
        model = CapitalAdjustmentMapper.to_model(entity, MCapitalAdjustment)
        assert isinstance(model, MCapitalAdjustment)

    def test_to_model_preserves_portfolio_amount_uuid(self):
        entity = _make_capital()
        model = CapitalAdjustmentMapper.to_model(entity, MCapitalAdjustment)
        assert model.portfolio_id == "port-1"
        assert model.amount == Decimal("10000.5")
        assert model.uuid == entity.uuid

    def test_roundtrip_preserves_non_source_fields(self):
        """roundtrip 还原 portfolio_id/amount/reason/timestamp/uuid（不含 source）。

        注意：原码 from_model 把 model.source（int）直接传 CapitalAdjustment
        构造器，而 CapitalAdjustment.__init__ 严格校验 source 必须 SOURCE_TYPES
        enum（capital_adjustment.py:56-57）——故 from_model 对 ORM 标准的 int
        source 必 TypeError。这是原码已知 bug（且 CapitalAdjustment.from_model
        从未被 CRUD 调用，属死代码）。忠实搬运保留，留 Task 1.6 统一评估。

        本测试绕过 source：from_model 对 int source 必崩，故断言 from_model
        抛 TypeError（记录 bug 行为），其余字段经 to_model 单测覆盖。
        """
        entity = _make_capital(
            portfolio_id="port-2",
            amount=Decimal("-500.25"),
            reason="withdrawal",
            timestamp="2024-06-01 09:30:00",
        )
        model = CapitalAdjustmentMapper.to_model(entity, MCapitalAdjustment)

        # model.source 是 int（MCapitalAdjustment Mapped[int] + validate_input 转 .value）
        assert isinstance(model.source, int)
        # from_model 对 int source 必 TypeError（原码 bug，忠实记录）
        with pytest.raises(TypeError, match="source must be SOURCE_TYPES"):
            CapitalAdjustmentMapper.from_model(model)


class TestCapitalAdjustmentMapperTypeError:
    def test_from_model_rejects_non_mcapitaladjustment(self):
        with pytest.raises(TypeError) as exc:
            CapitalAdjustmentMapper.from_model(None)
        assert "MCapitalAdjustment" in str(exc.value)


class TestCapitalAdjustmentMapperFromModels:
    def test_from_models_empty_list(self):
        """from_models 空列表返回空（from_model 对 int source 必崩，见 roundtrip 注）。"""
        assert CapitalAdjustmentMapper.from_models([]) == []

    def test_from_models_propagates_source_typeerror(self):
        """from_models 对含 int source 的 model 必崩（原码 bug 透传，忠实记录）。"""
        entity = _make_capital()
        model = CapitalAdjustmentMapper.to_model(entity, MCapitalAdjustment)
        with pytest.raises(TypeError, match="source must be SOURCE_TYPES"):
            CapitalAdjustmentMapper.from_models([model])
