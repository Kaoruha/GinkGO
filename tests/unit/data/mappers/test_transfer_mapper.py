# Upstream: tests/unit/data/mappers/（ADR-010 Mapper TDD）
# Downstream: ginkgo.data.mappers.TransferMapper
# Role: TransferMapper to_model（按 from_model 反向实现）+ from_model（原码 bug）+ 批量

import datetime
from decimal import Decimal

import pytest

from ginkgo.data.mappers import TransferMapper
from ginkgo.data.models import MTransfer
from ginkgo.entities import Transfer
from ginkgo.enums import (
    MARKET_TYPES,
    TRANSFERDIRECTION_TYPES,
    TRANSFERSTATUS_TYPES,
)


def _make_transfer(**overrides) -> Transfer:
    defaults = dict(
        portfolio_id="p-1",
        engine_id="e-1",
        task_id="t-1",
        direction=TRANSFERDIRECTION_TYPES.IN,
        market=MARKET_TYPES.CHINA,
        money=10000,
        status=TRANSFERSTATUS_TYPES.PENDING,
        timestamp="2026-06-14 10:00:00",
    )
    defaults.update(overrides)
    return Transfer(**defaults)


class TestTransferMapperToModel:
    def test_to_model_returns_mtransfer(self):
        """to_model 按 from_model 反向实现（写路径经 CRUD _convert_input_item 旁证）。"""
        entity = _make_transfer()
        model = TransferMapper.to_model(entity)
        assert isinstance(model, MTransfer)

    def test_to_model_preserves_core_fields(self):
        entity = _make_transfer()
        model = TransferMapper.to_model(entity)
        assert model.portfolio_id == "p-1"
        assert model.engine_id == "e-1"
        assert model.task_id == "t-1"
        assert model.money == Decimal("10000")

    def test_to_model_enums_validated_to_int(self):
        """enum 经 validate_input 转 int（ORM 存 int）。"""
        entity = _make_transfer()
        model = TransferMapper.to_model(entity)
        assert model.direction == TRANSFERDIRECTION_TYPES.IN.value
        assert model.market == MARKET_TYPES.CHINA.value
        assert model.status == TRANSFERSTATUS_TYPES.PENDING.value

    def test_to_model_restores_uuid(self):
        """uuid 还原（原码惯例）。"""
        entity = _make_transfer()
        model = TransferMapper.to_model(entity)
        assert model.uuid == entity.uuid


class TestTransferMapperFromModel:
    def test_from_model_missing_task_id_raises_typeerror(self):
        """已知 bug：原码 from_model 构造不传 task_id，触发 __init__ TypeError
        （Transfer.__init__ 强制 task_id 非空 str，line 30）。
        忠实搬运保留，留后续 issue。
        """
        model = MTransfer()
        model.portfolio_id = "p-1"
        model.engine_id = "e-1"
        model.direction = TRANSFERDIRECTION_TYPES.IN.value
        model.market = MARKET_TYPES.CHINA.value
        model.money = Decimal("10000")
        model.status = TRANSFERSTATUS_TYPES.PENDING.value
        model.timestamp = datetime.datetime(2026, 6, 14, 10, 0, 0)

        with pytest.raises(TypeError):
            TransferMapper.from_model(model)


class TestTransferMapperFromModels:
    def test_from_models_batch_propagates_task_id_bug(self):
        """批量 from_model 同样受 task_id bug 影响（逐个调用 from_model）。"""
        model = MTransfer()
        model.portfolio_id = "p-1"
        with pytest.raises(TypeError):
            TransferMapper.from_models([model])
