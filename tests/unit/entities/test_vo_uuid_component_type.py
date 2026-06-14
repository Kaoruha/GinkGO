"""Task 2.2 Batch A：4 VO 迁 ValueObject 后契约（uuid 保留、component_type 已删）。"""
import pytest
from ginkgo.entities import Adjustfactor, TradeDay, StockInfo, Transfer
from ginkgo.entities.value_object import ValueObject
from ginkgo.entities.base import Base
from ginkgo.enums import SOURCE_TYPES

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


# ---------- Task 2.2 Batch B ----------
from ginkgo.entities import Mapping, Tick, CapitalAdjustment, FileInfo

VO_CLASSES_B = [Mapping, Tick, CapitalAdjustment, FileInfo]


@pytest.mark.parametrize("cls", VO_CLASSES_B)
def test_vob_inherits_valueobject_not_base(cls):
    assert issubclass(cls, ValueObject)
    assert not issubclass(cls, Base)


@pytest.mark.parametrize("cls", VO_CLASSES_B)
def test_vob_has_no_component_type(cls):
    assert not hasattr(cls.__new__(cls), "_component_type")


def test_vob_uuid_roundtrip_mapping():
    m = Mapping(left_key="e1", right_key="h1", uuid="m-1")
    assert m.uuid == "m-1"


def test_vob_uuid_roundtrip_tick():
    from ginkgo.enums import TICKDIRECTION_TYPES

    t = Tick(
        code="000001.SZ",
        price=1.0,
        volume=1,
        direction=TICKDIRECTION_TYPES.ACTIVEBUY,
        timestamp="2024-01-02",
        uuid="t-1",
    )
    assert t.uuid == "t-1"


def test_vob_uuid_roundtrip_capital_adjustment():
    ca = CapitalAdjustment(
        portfolio_id="p1",
        amount=100,
        timestamp="2024-01-02",
        uuid="ca-1",
    )
    assert ca.uuid == "ca-1"


def test_vob_uuid_roundtrip_fileinfo():
    f = FileInfo(name="f1", uuid="f-1")
    assert f.uuid == "f-1"


def test_tick_source_roundtrip():
    """Tick 保留 source property（tick_mapper.to_model 读 entity.source）。"""
    from ginkgo.enums import TICKDIRECTION_TYPES

    t = Tick(
        code="000001.SZ",
        price=1.0,
        volume=1,
        direction=TICKDIRECTION_TYPES.ACTIVEBUY,
        timestamp="2024-01-02",
        source=SOURCE_TYPES.TDX,
    )
    assert t.source == SOURCE_TYPES.TDX


def test_capital_adjustment_source_accessible():
    """CapitalAdjustment 保留 source property（mapper 读 entity.source）。"""
    ca = CapitalAdjustment(
        portfolio_id="p1",
        amount=100,
        timestamp="2024-01-02",
        source=SOURCE_TYPES.SIM,
    )
    assert ca.source == SOURCE_TYPES.SIM


def test_tick_from_series_source_path():
    """Tick.set(Series) 路径不再调 set_source（迁后无该方法），改 _source 直接赋值。"""
    import pandas as pd
    from ginkgo.enums import TICKDIRECTION_TYPES

    df = pd.Series({
        "code": "000001.SZ",
        "price": 1.0,
        "volume": 1,
        "direction": TICKDIRECTION_TYPES.ACTIVEBUY,
        "timestamp": "2024-01-02",
        "source": SOURCE_TYPES.TDX.value,
    })
    t = Tick(
        code="000001.SZ",
        price=1.0,
        volume=1,
        direction=TICKDIRECTION_TYPES.ACTIVEBUY,
        timestamp="2024-01-02",
    )
    t.set(df)
    assert t.source == SOURCE_TYPES.TDX


def test_mapping_to_dict_reads_uuid():
    """Mapping.to_dict 读 self.uuid（迁移后仍可读）。"""
    m = Mapping(left_key="e1", right_key="h1", uuid="m-9")
    d = m.to_dict()
    assert d["uuid"] == "m-9"
