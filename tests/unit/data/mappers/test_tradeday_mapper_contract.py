"""TradeDayMapper 契约 roundtrip 测试（ADR-029 Task 4）。

参照 test_tick_mapper_contract.py 模板，覆盖 TradeDay Entity↔MTradeDay ORM 全字段
映射保真。TradeDay 是 ValueObject（uuid 自留，无 source 业务字段），故契约聚焦
market/is_open/timestamp/uuid 四字段 + market 枚举往返 + source 默认 TUSHARE
（对齐原 _convert_input_item 行为：entity 无 source 属性 → mapper 不写 →
MTradeDay.__init__ 默认 TUSHARE）。

契约不变量：
- entity_to_model 经 model_class 形参构造（VO 动态表选择，§Decision 8 保留 adapter）
- entity_to_model 写 market（经 validate_input 转 int）/is_open/timestamp/uuid
- model_to_entity 还原上述全部字段（roundtrip 双向保真）
- market 枚举经 validate_input→int→MARKET_TYPES(int)→enum 来回无损
- source 默认契约：entity 无 source → model.source == TUSHARE.value（语义对齐原 override）
- is_open True/False 均无损往返（DB TINYINT/Boolean 边界）
- TypeError 守卫：model_to_entity 拒绝非 MTradeDay 实例
"""
import datetime

import pytest

from ginkgo.entities import TradeDay
from ginkgo.data.mappers import TradeDayMapper
from ginkgo.data.models import MTradeDay
from ginkgo.enums import MARKET_TYPES, SOURCE_TYPES


def _make_tradeday(
    market: MARKET_TYPES = MARKET_TYPES.CHINA,
    is_open: bool = True,
    timestamp: str = "2024-01-15",
    uuid: str = "",
) -> TradeDay:
    """构造测试 TradeDay entity（按 __init__ 真实参数）。"""
    return TradeDay(market=market, is_open=is_open, timestamp=timestamp, uuid=uuid)


# ----------------------------------------------------------------------
# 全字段写入契约（entity_to_model）
# ----------------------------------------------------------------------
def test_entity_to_model_returns_mtradeday():
    entity = _make_tradeday()
    model = TradeDayMapper.entity_to_model(entity)
    assert isinstance(model, MTradeDay)


def test_entity_to_model_writes_market_as_int():
    """market enum 经 MTradeDay.__init__ validate_input 转 int 存（CHINA.value=1）。"""
    entity = _make_tradeday(market=MARKET_TYPES.CHINA)
    model = TradeDayMapper.entity_to_model(entity)
    assert model.market == MARKET_TYPES.CHINA.value


def test_entity_to_model_writes_is_open():
    entity = _make_tradeday(is_open=False)
    model = TradeDayMapper.entity_to_model(entity)
    assert model.is_open is False


def test_entity_to_model_writes_timestamp():
    entity = _make_tradeday(timestamp="2024-06-01 10:00:00")
    model = TradeDayMapper.entity_to_model(entity)
    assert model.timestamp == datetime.datetime(2024, 6, 1, 10, 0, 0)


def test_entity_to_model_writes_uuid():
    entity = _make_tradeday(uuid="td-uuid-123")
    model = TradeDayMapper.entity_to_model(entity)
    assert model.uuid == "td-uuid-123"


def test_entity_to_model_default_model_class_is_mtradeday():
    """签名默认 model_class=MTradeDay（VO 动态表保留 model_class 形参）。"""
    import inspect

    sig = inspect.signature(TradeDayMapper.entity_to_model)
    assert sig.parameters["model_class"].default is MTradeDay


# ----------------------------------------------------------------------
# source 默认契约（entity 无 source → model 默认 TUSHARE，对齐原 override 语义）
# ----------------------------------------------------------------------
def test_entity_to_model_source_defaults_to_tushare():
    """TradeDay entity 无 source 字段；mapper 不写 source → MTradeDay.__init__
    默认 SOURCE_TYPES.TUSHARE。对齐原 _convert_input_item 的
    `getattr(item, 'source', TUSHARE)` 行为（entity 无 source 永远走默认）。"""
    entity = _make_tradeday()
    model = TradeDayMapper.entity_to_model(entity)
    assert model.source == SOURCE_TYPES.TUSHARE.value


# ----------------------------------------------------------------------
# 还原契约（model_to_entity）
# ----------------------------------------------------------------------
def test_model_to_entity_returns_tradeday():
    model = TradeDayMapper.entity_to_model(_make_tradeday())
    restored = TradeDayMapper.model_to_entity(model)
    assert isinstance(restored, TradeDay)


def test_model_to_entity_restores_all_fields():
    original = _make_tradeday(
        market=MARKET_TYPES.NASDAQ,
        is_open=False,
        timestamp="2024-07-15 09:30:00",
        uuid="restore-uuid",
    )
    model = TradeDayMapper.entity_to_model(original)
    back = TradeDayMapper.model_to_entity(model)

    assert back.market == MARKET_TYPES.NASDAQ
    assert back.is_open is False
    assert back.timestamp == datetime.datetime(2024, 7, 15, 9, 30, 0)
    assert back.uuid == "restore-uuid"


def test_model_to_entity_typeerror_on_non_mtradeday():
    """model_to_entity 拒绝非 MTradeDay 实例（响亮失败，#4652 教训）。"""
    with pytest.raises(TypeError):
        TradeDayMapper.model_to_entity(object())


# ----------------------------------------------------------------------
# 全字段 roundtrip 双向保真（核心契约）
# ----------------------------------------------------------------------
@pytest.mark.parametrize("market", [MARKET_TYPES.CHINA, MARKET_TYPES.NASDAQ])
def test_roundtrip_preserves_market_enum(market):
    """market 枚举 validate_input→int→MARKET_TYPES(int)→enum 来回无损。
    （OTHER value=0 经 entity 严格 isinstance 校验后正常，但 model_to_entity
    兜底 OTHER 分支；此处聚焦 CHINA/NASDAQ 主路径。）"""
    entity = _make_tradeday(market=market)
    model = TradeDayMapper.entity_to_model(entity)
    back = TradeDayMapper.model_to_entity(model)
    assert back.market == market


@pytest.mark.parametrize("is_open", [True, False])
def test_roundtrip_preserves_is_open_bool(is_open):
    """is_open True/False 均 roundtrip 无损（DB Boolean 边界）。"""
    entity = _make_tradeday(is_open=is_open)
    model = TradeDayMapper.entity_to_model(entity)
    back = TradeDayMapper.model_to_entity(model)
    assert back.is_open is is_open


def test_full_roundtrip_preserves_all_business_fields():
    """entity → model → entity 全业务字段保真（含 uuid VO 自留）。"""
    original = _make_tradeday(
        market=MARKET_TYPES.CHINA,
        is_open=False,
        timestamp="2024-01-15 14:30:00",
        uuid="full-roundtrip-uuid",
    )
    model = TradeDayMapper.entity_to_model(original)
    back = TradeDayMapper.model_to_entity(model)

    assert back.market == original.market
    assert back.is_open == original.is_open
    assert back.timestamp == original.timestamp
    assert back.uuid == original.uuid


# ----------------------------------------------------------------------
# 批量 roundtrip 契约
# ----------------------------------------------------------------------
def test_batch_roundtrip_preserves_fields():
    """models_to_entities 批量还原字段不丢。"""
    entities = [
        _make_tradeday(market=MARKET_TYPES.CHINA, is_open=True),
        _make_tradeday(market=MARKET_TYPES.NASDAQ, is_open=False),
    ]
    models = [TradeDayMapper.entity_to_model(e) for e in entities]
    restored = TradeDayMapper.models_to_entities(models)
    assert len(restored) == 2
    assert restored[0].market == MARKET_TYPES.CHINA
    assert restored[0].is_open is True
    assert restored[1].market == MARKET_TYPES.NASDAQ
    assert restored[1].is_open is False
