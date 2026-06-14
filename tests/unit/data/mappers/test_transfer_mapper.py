# Upstream: tests/unit/data/mappers/（ADR-010 Mapper TDD）
# Downstream: ginkgo.data.mappers.TransferMapper
# Role: TransferMapper to_model（按 from_model 反向实现）+ from_model（对齐原码 transfer.py:218-239）+ 批量

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


def _make_mtransfer(**overrides) -> MTransfer:
    """构造 MTransfer ORM 实例（含 task_id，对齐原 from_model 活代码路径）。

    真实路径：CRUD _convert_models_to_business_objects 调 from_model 前，
    enum 字段已被 _get_enum_mappings 修复为枚举对象（非 int）。
    故这里 direction/market/status 直接赋枚举对象（对齐原码注释
    "此时已经是枚举对象"）。
    """
    model = MTransfer()
    model.portfolio_id = overrides.get("portfolio_id", "p-1")
    model.engine_id = overrides.get("engine_id", "e-1")
    model.task_id = overrides.get("task_id", "t-1")
    model.direction = overrides.get("direction", TRANSFERDIRECTION_TYPES.IN)
    model.market = overrides.get("market", MARKET_TYPES.CHINA)
    model.money = overrides.get("money", Decimal("10000"))
    model.status = overrides.get("status", TRANSFERSTATUS_TYPES.PENDING)
    model.timestamp = overrides.get("timestamp", datetime.datetime(2026, 6, 14, 10, 0, 0))
    return model


class TestTransferMapperFromModel:
    def test_from_model_preserves_task_id(self):
        """from_model 对齐原码 transfer.py:218-239（含 task_id）。
        原 entity from_model 本传 task_id，TransferMapper 搬运时一度漏传，
        本测试锁定 task_id 保真（修正搬运退化，#6117）。
        """
        model = _make_mtransfer(task_id="task-xyz")
        back = TransferMapper.from_model(model)
        assert back.task_id == "task-xyz"

    def test_from_model_returns_transfer(self):
        model = _make_mtransfer()
        back = TransferMapper.from_model(model)
        assert isinstance(back, Transfer)

    def test_from_model_preserves_core_fields(self):
        model = _make_mtransfer()
        back = TransferMapper.from_model(model)
        assert back.portfolio_id == "p-1"
        assert back.engine_id == "e-1"
        assert back.task_id == "t-1"
        assert back.money == Decimal("10000")


class TestTransferMapperFromModels:
    def test_from_models_batch_preserves_task_id(self):
        """批量 from_model 逐个调用 from_model，task_id 同样保真。"""
        model = _make_mtransfer(task_id="batch-1")
        back = TransferMapper.from_models([model])
        assert len(back) == 1
        assert back[0].task_id == "batch-1"
