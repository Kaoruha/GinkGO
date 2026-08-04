# Upstream: tests/unit/data/mappers/（ADR-010 Mapper TDD）
# Downstream: ginkgo.data.mappers.StockInfoMapper
# Role: StockInfoMapper roundtrip + TypeError 守卫 + market/currency int→enum 测试
# 注：market 全枚举/默认值/source side-channel 等核心契约见
#     test_stockinfo_mapper_contract.py（ADR-029 Task 3）。本文件保留基本 smoke。

import pytest

from ginkgo.data.mappers import StockInfoMapper
from ginkgo.data.models import MStockInfo
from ginkgo.entities import StockInfo
from ginkgo.enums import MARKET_TYPES, CURRENCY_TYPES


def _make_stockinfo(**overrides) -> StockInfo:
    """按 StockInfo.__init__ 真实参数构造。默认带显式 uuid 便于 roundtrip 比对。"""
    defaults = dict(
        code="SH600000",
        code_name="浦发银行",
        industry="银行",
        market=MARKET_TYPES.CHINA,
        currency=CURRENCY_TYPES.CNY,
        list_date="1999-11-10",
        delist_date="2099-12-31",
        uuid="fixed-uuid-abc123",
    )
    defaults.update(overrides)
    return StockInfo(**defaults)


class TestStockInfoMapperRoundtrip:
    def test_to_model_returns_mstockinfo(self):
        entity = _make_stockinfo()
        model = StockInfoMapper.entity_to_model(entity, MStockInfo)
        assert isinstance(model, MStockInfo)

    def test_to_model_preserves_code_currency_uuid(self):
        """全字段直传（含 market 修复 + uuid 显式值保真）。

        ADR-029 Task 3：原 mapper 漏 market 已修；空 uuid→None 让 ORM default
        生成（对齐 stock_info_crud._convert_input_item override）。本测试用显式
        uuid 验证非空 roundtrip 保真；空 uuid 行为由契约测试覆盖。
        """
        entity = _make_stockinfo()
        model = StockInfoMapper.entity_to_model(entity, MStockInfo)
        assert model.code == "SH600000"
        assert model.code_name == "浦发银行"
        assert model.industry == "银行"
        assert model.uuid == entity.uuid
        assert model.market == MARKET_TYPES.CHINA.value  # 修复点：market 不丢

    def test_roundtrip_preserves_core_fields(self):
        """roundtrip 还原 code/code_name/industry/market/currency/list_date/delist_date/uuid。"""
        entity = _make_stockinfo(market=MARKET_TYPES.CHINA)
        model = StockInfoMapper.entity_to_model(entity, MStockInfo)
        restored = StockInfoMapper.model_to_entity(model)

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
        restored = StockInfoMapper.model_to_entity(model)
        assert restored.market == MARKET_TYPES.NASDAQ
        assert restored.currency == CURRENCY_TYPES.USD


class TestStockInfoMapperTypeError:
    def test_from_model_rejects_non_mstockinfo(self):
        with pytest.raises(TypeError) as exc:
            StockInfoMapper.model_to_entity("nope")
        assert "MStockInfo" in str(exc.value)


class TestStockInfoMapperFromModels:
    def test_from_models_maps_list(self):
        entity = _make_stockinfo()
        model = StockInfoMapper.entity_to_model(entity, MStockInfo)
        results = StockInfoMapper.models_to_entities([model, model])
        assert len(results) == 2
        assert all(isinstance(r, StockInfo) for r in results)
