# Upstream: tests/unit/data/mappers/（ADR-010 Mapper TDD）
# Downstream: ginkgo.data.mappers.PositionMapper
# Role: PositionMapper roundtrip + TypeError 守卫测试

import datetime

import pytest

from ginkgo.data.mappers import PositionMapper
from ginkgo.data.models import MPosition
from ginkgo.entities import Position


def _make_position(**overrides) -> Position:
    """按 Position.__init__ 真实参数构造。"""
    defaults = dict(
        portfolio_id="port-1",
        engine_id="engine-1",
        task_id="task-1",
        code="SH600000",
        cost=10.5,
        volume=1000,
        frozen_volume=200,
        settlement_frozen_volume=50,
        settlement_days=1,
        frozen_money=2100,
        price=10.8,
        fee=5.25,
    )
    defaults.update(overrides)
    return Position(**defaults)


class TestPositionMapperRoundtrip:
    def test_to_model_returns_mposition(self):
        entity = _make_position()
        model = PositionMapper.to_model(entity)
        assert isinstance(model, MPosition)

    def test_to_model_preserves_core_fields(self):
        entity = _make_position()
        model = PositionMapper.to_model(entity)
        assert model.code == "SH600000"
        assert model.volume == 1000
        assert model.frozen_volume == 200
        assert model.settlement_frozen_volume == 50
        assert model.settlement_days == 1

    def test_to_model_preserves_uuid(self):
        entity = _make_position()
        model = PositionMapper.to_model(entity)
        # model.uuid 被赋为 entity.uuid（原码行为保留）
        assert model.uuid == entity.uuid

    def test_to_model_serializes_empty_settlement_queue(self):
        entity = _make_position()
        model = PositionMapper.to_model(entity)
        # 空队列序列化为 "[]"
        assert model.settlement_queue_json == "[]"

    def test_from_model_preserves_uuid(self):
        entity = _make_position()
        model = PositionMapper.to_model(entity)
        back = PositionMapper.from_model(model)
        assert back.uuid == entity.uuid

    def test_roundtrip_code_volume(self):
        entity = _make_position(code="SZ000001", volume=5000)
        model = PositionMapper.to_model(entity)
        back = PositionMapper.from_model(model)
        assert back.code == "SZ000001"
        assert back.volume == 5000

    def test_roundtrip_optional_fields(self):
        entity = _make_position(
            frozen_volume=300,
            settlement_frozen_volume=80,
            settlement_days=2,
            frozen_money=3000,
            fee=12.5,
        )
        model = PositionMapper.to_model(entity)
        back = PositionMapper.from_model(model)
        assert back.frozen_volume == 300
        assert back.settlement_frozen_volume == 80
        assert back.settlement_days == 2
        assert back.frozen_money == 3000
        assert back.fee == 12.5

    def test_roundtrip_non_empty_settlement_queue(self):
        """非空 settlement_queue roundtrip：volume 保真 + buy_date 还原为 datetime。"""
        entity = _make_position()
        # batch 结构与 Position._on_price_update 一致：volume/buy_date/settlement_date
        now = datetime.datetime(2026, 6, 13, 10, 30, 0)
        entity._settlement_queue = [{
            'volume': 500,
            'buy_date': now,
            'settlement_date': now + datetime.timedelta(days=1),
        }]
        model = PositionMapper.to_model(entity)
        back = PositionMapper.from_model(model)
        # mapper 直读/直写 _settlement_queue（无公开 property），测试忠实其访问方式
        assert len(back._settlement_queue) == 1
        assert back._settlement_queue[0]['volume'] == 500
        assert isinstance(back._settlement_queue[0]['buy_date'], datetime.datetime)

    def test_from_model_bad_json_fallback_empty(self):
        """settlement_queue_json 坏值时 from_model fallback []（验异常路径）。"""
        entity = _make_position()
        model = PositionMapper.to_model(entity)
        model.settlement_queue_json = "not-json"
        back = PositionMapper.from_model(model)
        assert back._settlement_queue == []


class TestPositionMapperFromModelGuard:
    def test_from_model_rejects_non_mposition(self):
        with pytest.raises(TypeError):
            PositionMapper.from_model(object())


class TestPositionMapperFromModels:
    def test_from_models_maps_all(self):
        entities = [_make_position(code="A"), _make_position(code="B")]
        models = [PositionMapper.to_model(e) for e in entities]
        back = PositionMapper.from_models(models)
        assert len(back) == 2
        assert {b.code for b in back} == {"A", "B"}
