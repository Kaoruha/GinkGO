# Upstream: tests/unit/data/mappers/（ADR-010 Mapper TDD）
# Downstream: ginkgo.data.mappers.StockInfoMapper
# Role: StockInfoMapper roundtrip + TypeError 守卫 + market/currency int→enum 测试

import pytest

from ginkgo.data.mappers import StockInfoMapper
from ginkgo.data.models import MStockInfo
from ginkgo.entities import StockInfo
from ginkgo.enums import MARKET_TYPES, CURRENCY_TYPES


def _make_stockinfo(**overrides) -> StockInfo:
    """按 StockInfo.__init__ 真实参数构造。"""
    defaults = dict(
        code="SH600000",
        code_name="浦发银行",
        industry="银行",
        market=MARKET_TYPES.CHINA,
        currency=CURRENCY_TYPES.CNY,
        list_date="1999-11-10",
        delist_date="2099-12-31",
    )
    defaults.update(overrides)
    return StockInfo(**defaults)


class TestStockInfoMapperRoundtrip:
    def test_to_model_returns_mstockinfo(self):
        entity = _make_stockinfo()
        model = StockInfoMapper.to_model(entity, MStockInfo)
        assert isinstance(model, MStockInfo)

    def test_to_model_preserves_code_currency_uuid(self):
        entity = _make_stockinfo()
        model = StockInfoMapper.to_model(entity, MStockInfo)
        assert model.code == "SH600000"
        assert model.code_name == "浦发银行"
        assert model.industry == "银行"
        assert model.uuid == entity.uuid

    def test_to_model_does_not_pass_market(self):
        """已知 bug：原码 to_model 未传 market（stockinfo.py:215-227）。

        model.market 走 MStockInfo.__init__ 默认 CHINA.value，而非 entity.market。
        忠实搬运保留，留 Task 1.6 统一评估。本测试断言此 bug 行为：
        非 CHINA entity → model.market 仍 CHINA.value。
        """
        entity = _make_stockinfo(market=MARKET_TYPES.NASDAQ)
        model = StockInfoMapper.to_model(entity, MStockInfo)
        # market 未传，走默认
        assert model.market == MARKET_TYPES.CHINA.value

    def test_roundtrip_preserves_core_fields_default_market(self):
        """roundtrip 还原 code/code_name/industry/currency/list_date/delist_date/uuid。

        market 走默认 CHINA（entity 即 CHINA 时不暴露 to_model 漏传 bug）。
        from_model market/currency int→enum 转换正确。
        """
        entity = _make_stockinfo(market=MARKET_TYPES.CHINA)
        model = StockInfoMapper.to_model(entity, MStockInfo)
        restored = StockInfoMapper.from_model(model)

        assert restored.code == "SH600000"
        assert restored.code_name == "浦发银行"
        assert restored.industry == "银行"
        assert restored.market == MARKET_TYPES.CHINA
        assert restored.currency == CURRENCY_TYPES.CNY
        assert restored.uuid == entity.uuid

    def test_from_model_market_currency_int_to_enum(self):
        """ORM market/currency 存 int，from_model 转 enum。"""
        model = MStockInfo()
        model.market = MARKET_TYPES.NASDAQ.value
        model.currency = CURRENCY_TYPES.USD.value
        restored = StockInfoMapper.from_model(model)
        assert restored.market == MARKET_TYPES.NASDAQ
        assert restored.currency == CURRENCY_TYPES.USD


class TestStockInfoMapperTypeError:
    def test_from_model_rejects_non_mstockinfo(self):
        with pytest.raises(TypeError) as exc:
            StockInfoMapper.from_model("nope")
        assert "MStockInfo" in str(exc.value)


class TestStockInfoMapperFromModels:
    def test_from_models_maps_list(self):
        entity = _make_stockinfo()
        model = StockInfoMapper.to_model(entity, MStockInfo)
        results = StockInfoMapper.from_models([model, model])
        assert len(results) == 2
        assert all(isinstance(r, StockInfo) for r in results)
