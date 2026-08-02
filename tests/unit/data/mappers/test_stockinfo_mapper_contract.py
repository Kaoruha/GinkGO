"""StockInfoMapper 契约 roundtrip 测试（ADR-029 Task 3）。

参照 test_tick_mapper_contract.py / test_bar_mapper_contract.py 模板，
覆盖 StockInfo Entity↔MStockInfo ORM 全字段映射保真。

**核心修复点（market 不丢）**:
原 StockInfoMapper.entity_to_model 未传 market（自承丢失 bug，
stockinfo_mapper:35-37）。非 CHINA entity roundtrip 时 market 被静默
回退到 CHINA。本契约测试锁此修复：market 全枚举 roundtrip 双向保真。

契约不变量：
- entity_to_model 写 market（修复点，对齐 stock_info_crud._convert_input_item:159-169 override 字段集）
- entity_to_model 写 source（_source side-channel，service 经 `entity._source=...` 写入，对齐 override 行为）
- entity_to_model 写 code/code_name/industry/currency/list_date/delist_date/uuid
- model_to_entity 还原上述全部字段（roundtrip 双向保真）
- market/currency/source 枚举经 validate_input→int→from_int→enum 来回无损
- 默认值：StockInfo 默认 CHINA/CNY → model.market==CHINA.value, currency==CNY.value
- TypeError 守卫：model_to_entity 拒绝非 MStockInfo 实例（#4652 教训）
"""
import datetime

import pytest

from ginkgo.entities import StockInfo
from ginkgo.data.mappers import StockInfoMapper
from ginkgo.data.models import MStockInfo
from ginkgo.enums import MARKET_TYPES, CURRENCY_TYPES, SOURCE_TYPES


def _make_stockinfo(
    market: MARKET_TYPES = MARKET_TYPES.CHINA,
    currency: CURRENCY_TYPES = CURRENCY_TYPES.CNY,
    source: SOURCE_TYPES = SOURCE_TYPES.TUSHARE,
    code: str = "SH600000",
    uuid: str = "",
) -> StockInfo:
    """构造测试 StockInfo entity（显式 market/currency/source，避开默认值以测枚举往返）。

    StockInfo 是 ValueObject（非 Base 子类），无 source property/set_source；
    service 经 `_source` side-channel 写入（stockinfo_service:166），mapper 对齐
    `getattr(entity, '_source', ...)` 读取。测试直接设 `_source` 复刻 service 契约。
    """
    entity = StockInfo(
        code=code,
        code_name="浦发银行",
        industry="银行",
        market=market,
        currency=currency,
        list_date="1999-11-10",
        delist_date="2099-12-31",
        uuid=uuid,
    )
    entity._source = source  # service side-channel（stockinfo_service:166 同款）
    return entity


# ----------------------------------------------------------------------
# 全字段写入契约（entity_to_model）
# ----------------------------------------------------------------------
def test_entity_to_model_returns_mstockinfo():
    entity = _make_stockinfo()
    model = StockInfoMapper.entity_to_model(entity, MStockInfo)
    assert isinstance(model, MStockInfo)


def test_entity_to_model_writes_code():
    entity = _make_stockinfo(code="SZ000001")
    model = StockInfoMapper.entity_to_model(entity, MStockInfo)
    assert model.code == "SZ000001"


def test_entity_to_model_writes_code_name():
    entity = _make_stockinfo()
    model = StockInfoMapper.entity_to_model(entity, MStockInfo)
    assert model.code_name == "浦发银行"


def test_entity_to_model_writes_industry():
    entity = _make_stockinfo()
    model = StockInfoMapper.entity_to_model(entity, MStockInfo)
    assert model.industry == "银行"


def test_entity_to_model_writes_market_as_int():
    """market 经 validate_input 存 int（MARKET_TYPES.NASDAQ.value=2）。

    核心修复点：原 mapper 未传 market，model.market 走 MStockInfo.__init__
    默认 CHINA.value。修复后 model.market == entity.market.value。
    """
    entity = _make_stockinfo(market=MARKET_TYPES.NASDAQ)
    model = StockInfoMapper.entity_to_model(entity, MStockInfo)
    assert model.market == MARKET_TYPES.NASDAQ.value


def test_entity_to_model_writes_currency_as_int():
    """currency 经 validate_input 存 int（CURRENCY_TYPES.USD.value=2）。"""
    entity = _make_stockinfo(currency=CURRENCY_TYPES.USD)
    model = StockInfoMapper.entity_to_model(entity, MStockInfo)
    assert model.currency == CURRENCY_TYPES.USD.value


def test_entity_to_model_writes_source_as_int():
    """source 经 validate_input 存 int（_source side-channel，对齐 CRUD override）。"""
    entity = _make_stockinfo(source=SOURCE_TYPES.AKSHARE)
    model = StockInfoMapper.entity_to_model(entity, MStockInfo)
    assert model.source == SOURCE_TYPES.AKSHARE.value


def test_entity_to_model_writes_list_date():
    entity = _make_stockinfo()
    model = StockInfoMapper.entity_to_model(entity, MStockInfo)
    assert model.list_date == datetime.datetime(1999, 11, 10)


def test_entity_to_model_writes_delist_date():
    entity = _make_stockinfo()
    model = StockInfoMapper.entity_to_model(entity, MStockInfo)
    assert model.delist_date == datetime.datetime(2099, 12, 31)


def test_entity_to_model_writes_uuid():
    entity = _make_stockinfo(uuid="abc123hex")
    model = StockInfoMapper.entity_to_model(entity, MStockInfo)
    assert model.uuid == "abc123hex"


# ----------------------------------------------------------------------
# 默认值契约（CHINA/CNY/VOID）
# ----------------------------------------------------------------------
def test_entity_to_model_market_default_china():
    """StockInfo 构造不传 market 时默认 CHINA → model.market == CHINA.value(1)。"""
    entity = StockInfo(
        code="SH600000",
        code_name="浦发银行",
        industry="银行",
        currency=CURRENCY_TYPES.CNY,
        list_date="1999-11-10",
        delist_date="2099-12-31",
    )
    assert entity.market == MARKET_TYPES.CHINA  # 前置
    model = StockInfoMapper.entity_to_model(entity, MStockInfo)
    assert model.market == MARKET_TYPES.CHINA.value


# ----------------------------------------------------------------------
# 还原契约（model_to_entity）
# ----------------------------------------------------------------------
def test_model_to_entity_returns_stockinfo():
    model = StockInfoMapper.entity_to_model(_make_stockinfo(), MStockInfo)
    restored = StockInfoMapper.model_to_entity(model)
    assert isinstance(restored, StockInfo)


def test_model_to_entity_typeerror_on_non_mstockinfo():
    """model_to_entity 拒绝非 MStockInfo 实例（响亮失败，#4652 教训）。"""
    with pytest.raises(TypeError):
        StockInfoMapper.model_to_entity(object())


# ----------------------------------------------------------------------
# 全字段 roundtrip 双向保真（核心契约）
# ----------------------------------------------------------------------
@pytest.mark.parametrize(
    "market",
    [
        MARKET_TYPES.OTHER,    # value=0，曾因 `or -1` falsy 吞 0 bug 被吞成 -1
        MARKET_TYPES.CHINA,    # value=1
        MARKET_TYPES.NASDAQ,   # value=2
    ],
)
def test_roundtrip_preserves_market_enum(market):
    """market 枚举 validate_input→int→from_int→enum 来回无损（核心修复点）。"""
    entity = _make_stockinfo(market=market)
    model = StockInfoMapper.entity_to_model(entity, MStockInfo)
    back = StockInfoMapper.model_to_entity(model)
    assert back.market == market


@pytest.mark.parametrize(
    "currency",
    [
        CURRENCY_TYPES.OTHER,  # value=0，同款 `or -1` falsy 吞 0 风险
        CURRENCY_TYPES.CNY,    # value=1
        CURRENCY_TYPES.USD,    # value=2
    ],
)
def test_roundtrip_preserves_currency_enum(currency):
    """currency 枚举 validate_input→int→from_int→enum 来回无损。"""
    entity = _make_stockinfo(currency=currency)
    model = StockInfoMapper.entity_to_model(entity, MStockInfo)
    back = StockInfoMapper.model_to_entity(model)
    assert back.currency == currency


def test_full_roundtrip_preserves_all_business_fields():
    """entity → model → entity 全业务字段保真（含 market 修复 + source side-channel）。"""
    original = _make_stockinfo(
        market=MARKET_TYPES.NASDAQ,
        currency=CURRENCY_TYPES.USD,
        source=SOURCE_TYPES.AKSHARE,
        code="AAPL",
        uuid="fixeduuid123",
    )
    model = StockInfoMapper.entity_to_model(original, MStockInfo)
    back = StockInfoMapper.model_to_entity(model)

    assert back.code == original.code
    assert back.code_name == original.code_name
    assert back.industry == original.industry
    assert back.market == original.market  # 修复点：曾丢
    assert back.currency == original.currency
    assert back.list_date == original.list_date
    assert back.delist_date == original.delist_date
    assert back.uuid == original.uuid


# ----------------------------------------------------------------------
# 批量 roundtrip 契约
# ----------------------------------------------------------------------
def test_batch_roundtrip_preserves_fields():
    """models_to_entities 批量还原字段不丢（含 market）。"""
    entities = [
        _make_stockinfo(market=MARKET_TYPES.NASDAQ, currency=CURRENCY_TYPES.USD),
        _make_stockinfo(market=MARKET_TYPES.CHINA, currency=CURRENCY_TYPES.CNY),
    ]
    models = [StockInfoMapper.entity_to_model(e, MStockInfo) for e in entities]
    restored = StockInfoMapper.models_to_entities(models)
    assert len(restored) == 2
    assert restored[0].market == MARKET_TYPES.NASDAQ
    assert restored[0].currency == CURRENCY_TYPES.USD
    assert restored[1].market == MARKET_TYPES.CHINA
    assert restored[1].currency == CURRENCY_TYPES.CNY
