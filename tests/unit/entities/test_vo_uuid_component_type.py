"""Task 2.2 Batch A：4 VO 迁 ValueObject 后契约（uuid 保留、component_type 已删）。"""
import pytest
from ginkgo.entities import Adjustfactor, TradeDay, StockInfo, Transfer
from ginkgo.entities.value_object import ValueObject
from ginkgo.entities.base import Base

VO_CLASSES = [Adjustfactor, TradeDay, StockInfo, Transfer]


@pytest.mark.parametrize("cls", VO_CLASSES)
def test_vo_inherits_valueobject_not_base(cls):
    assert issubclass(cls, ValueObject)
    assert not issubclass(cls, Base)


@pytest.mark.parametrize("cls", VO_CLASSES)
def test_vo_has_no_component_type(cls):
    """component_type 已删（无 _component_type 字段）。"""
    assert not hasattr(cls.__new__(cls), "_component_type")


def test_vo_uuid_roundtrip_adjustfactor():
    obj = Adjustfactor(
        code="000001.SZ",
        timestamp="2024-01-02",
        fore_adjustfactor=1.0,
        back_adjustfactor=1.0,
        adjustfactor=1.0,
        uuid="abc-123",
    )
    assert obj.uuid == "abc-123"


def test_vo_uuid_roundtrip_tradeday():
    from ginkgo.enums import MARKET_TYPES

    obj = TradeDay(
        market=MARKET_TYPES.CHINA,
        is_open=True,
        timestamp="2024-01-02",
        uuid="abc-123",
    )
    assert obj.uuid == "abc-123"


def test_vo_uuid_roundtrip_stockinfo():
    obj = StockInfo(code="000001.SZ", code_name="平安银行", uuid="abc-123")
    assert obj.uuid == "abc-123"


def test_vo_uuid_roundtrip_transfer():
    from ginkgo.enums import (
        MARKET_TYPES,
        TRANSFERDIRECTION_TYPES,
        TRANSFERSTATUS_TYPES,
    )

    obj = Transfer(
        portfolio_id="p1",
        engine_id="e1",
        task_id="t1",
        direction=TRANSFERDIRECTION_TYPES.IN,
        market=MARKET_TYPES.CHINA,
        money=1000,
        status=TRANSFERSTATUS_TYPES.NEW,
        timestamp="2024-01-02",
        uuid="abc-123",
    )
    assert obj.uuid == "abc-123"
