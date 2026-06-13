# Upstream: tests/unit/data/mappers/（ADR-010 Mapper TDD）
# Downstream: ginkgo.data.mappers.TradeDayMapper
# Role: TradeDayMapper roundtrip + TypeError 守卫 + market int→enum 测试

import pytest

from ginkgo.data.mappers import TradeDayMapper
from ginkgo.data.models import MTradeDay
from ginkgo.entities import TradeDay
from ginkgo.enums import MARKET_TYPES


def _make_tradeday(**overrides) -> TradeDay:
    """按 TradeDay.__init__ 真实参数构造。"""
    defaults = dict(
        market=MARKET_TYPES.CHINA,
        is_open=True,
        timestamp="2024-01-15",
    )
    defaults.update(overrides)
    return TradeDay(**defaults)


class TestTradeDayMapperRoundtrip:
    def test_to_model_returns_mtradeday(self):
        entity = _make_tradeday()
        model = TradeDayMapper.to_model(entity, MTradeDay)
        assert isinstance(model, MTradeDay)

    def test_to_model_preserves_market_and_uuid(self):
        entity = _make_tradeday(market=MARKET_TYPES.CHINA)
        model = TradeDayMapper.to_model(entity, MTradeDay)
        # market 经 validate_input 转 int 存
        assert model.market == MARKET_TYPES.CHINA.value
        assert model.uuid == entity.uuid

    def test_roundtrip_preserves_core_fields(self):
        """roundtrip 还原 market(is_open)/timestamp/uuid。

        from_model market int→enum；is_open 经原码 bool 转换保留。
        """
        entity = _make_tradeday(
            market=MARKET_TYPES.CHINA,
            is_open=False,
            timestamp="2024-06-01 10:00:00",
        )
        model = TradeDayMapper.to_model(entity, MTradeDay)
        restored = TradeDayMapper.from_model(model)

        assert restored.market == MARKET_TYPES.CHINA
        assert restored.is_open is False
        assert restored.uuid == entity.uuid

    def test_from_model_market_int_to_enum(self):
        """ORM market 存 int，from_model 转 enum。"""
        model = MTradeDay()
        model.market = MARKET_TYPES.NASDAQ.value  # 直接设 int 模拟 DB 读出
        restored = TradeDayMapper.from_model(model)
        assert restored.market == MARKET_TYPES.NASDAQ


class TestTradeDayMapperTypeError:
    def test_from_model_rejects_non_mtradeday(self):
        with pytest.raises(TypeError) as exc:
            TradeDayMapper.from_model(123)
        assert "MTradeDay" in str(exc.value)


class TestTradeDayMapperFromModels:
    def test_from_models_maps_list(self):
        entity = _make_tradeday()
        model = TradeDayMapper.to_model(entity, MTradeDay)
        results = TradeDayMapper.from_models([model, model])
        assert len(results) == 2
        assert all(isinstance(r, TradeDay) for r in results)
