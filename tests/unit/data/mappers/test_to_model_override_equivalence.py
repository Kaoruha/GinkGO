"""ADR-029 阶段1 契约:Mapper.to_model ↔ CRUD override 逐字段等价(DB-free)。

每对 entity 喂两条路径:
  A) Mapper.to_model(entity)            [Tick 传 model_class=MTick]
  B) CRUD._convert_input_item(entity)   [Tick 为 _convert_to_model(entity, MTick)]
断言两路径产出 ORM __dict__ 严格相等(剥 _sa_* SQLAlchemy 内部态 + uuid)。

uuid 排除:MClickBase.uuid default 非确定生成;两路径或同款 pass-through(entity.uuid
if uuid else None)或均不塞走 default,代码路径相同即视为镜像保真(非字段转换关注点)。

Position skip:to_model 唯一活跃调用方 portfolio_base.snapshot_state 依赖 settlement
三件套 + uuid,strict mirror 会静默损坏该路径(见 plan §Position 特例),留阶段3另立
ADR 以 Mapper 为单一真相源修。本契约覆盖 9 对,Position 标 skip。

CRUD 侧 object.__new__(CrudClass) 跳 __init__(避 DB 连接);entity 分支(isinstance/
hasattr 命中)不触 self,纯转换。
"""
from decimal import Decimal

import pytest

from ginkgo.entities import (
    Order,
    Signal,
    CapitalAdjustment,
    Bar,
    Tick,
    StockInfo,
    TradeDay,
    Transfer,
    Adjustfactor,
)
from ginkgo.enums import (
    DIRECTION_TYPES,
    ORDER_TYPES,
    ORDERSTATUS_TYPES,
    SOURCE_TYPES,
    FREQUENCY_TYPES,
    TICKDIRECTION_TYPES,
    MARKET_TYPES,
    CURRENCY_TYPES,
    TRANSFERDIRECTION_TYPES,
    TRANSFERSTATUS_TYPES,
)
from ginkgo.data.mappers import (
    OrderMapper,
    SignalMapper,
    CapitalAdjustmentMapper,
    BarMapper,
    TickMapper,
    StockInfoMapper,
    TradeDayMapper,
    TransferMapper,
    AdjustfactorMapper,
)
from ginkgo.data.crud.order_crud import OrderCRUD
from ginkgo.data.crud.signal_crud import SignalCRUD
from ginkgo.data.crud.capital_adjustment_crud import CapitalAdjustmentCRUD
from ginkgo.data.crud.bar_crud import BarCRUD
from ginkgo.data.crud.tick_crud import TickCRUD
from ginkgo.data.crud.stock_info_crud import StockInfoCRUD
from ginkgo.data.crud.trade_day_crud import TradeDayCRUD
from ginkgo.data.crud.transfer_crud import TransferCRUD
from ginkgo.data.crud.adjustfactor_crud import AdjustfactorCRUD
from ginkgo.data.models import MTick


def _orm_dict(model):
    """剥 SQLAlchemy 内部态(_sa_*)与 ORM 自动列(uuid/create_at/update_at)。

    自动列:MClickBase 构造时 datetime.now()/uuid4() 独立生成,两路径各跑一次必有
    微秒/随机差异,非字段转换关注点。代码路径相同(同款 __init__)即视为镜像保真。
    """
    _AUTO = {"uuid", "create_at", "update_at"}
    return {
        k: v
        for k, v in model.__dict__.items()
        if not k.startswith("_sa_") and k not in _AUTO
    }


def _crud_invoke(crud_cls, method, entity, model_class=None):
    """object.__new__ 跳 __init__,避 DB;entity 分支不触 self。"""
    crud = object.__new__(crud_cls)
    if model_class is not None:
        return getattr(crud, method)(entity, model_class)
    return getattr(crud, method)(entity)


# ---- entity factories(复用现有 mapper 测试口径,确保 __init__ 参数正确)----
def _make_order():
    return Order(
        portfolio_id="p1",
        engine_id="e1",
        task_id="t1",
        code="000001.SZ",
        direction=DIRECTION_TYPES.LONG,
        order_type=ORDER_TYPES.MARKETORDER,
        status=ORDERSTATUS_TYPES.NEW,
        volume=100,
        limit_price=10.5,
    )


def _make_signal():
    return Signal(
        portfolio_id="port-1",
        engine_id="engine-1",
        task_id="task-1",
        code="SH600000",
        direction=DIRECTION_TYPES.LONG,
        reason="test reason",
        source=SOURCE_TYPES.OTHER,
        volume=1000,
        weight=0.5,
        strength=0.7,
        confidence=0.8,
    )


def _make_capital():
    return CapitalAdjustment(
        portfolio_id="port-1",
        amount=Decimal("10000.5"),
        timestamp="2024-01-15 10:00:00",
        reason="deposit",
        source=SOURCE_TYPES.SIM,
    )


def _make_bar():
    return Bar(
        code="000001.SZ",
        open=10,
        high=11,
        low=9,
        close=10.5,
        volume=1000,
        amount=10500,
        frequency=FREQUENCY_TYPES.DAY,
        timestamp="2025-01-02",
    )


def _make_tick():
    return Tick(
        code="SH600000",
        price=10.50,
        volume=100,
        direction=TICKDIRECTION_TYPES.ACTIVESELL,
        timestamp="2026-06-14 10:30:00",
        source=SOURCE_TYPES.SIM,
    )


def _make_stockinfo():
    return StockInfo(
        code="SH600000",
        code_name="浦发银行",
        industry="银行",
        market=MARKET_TYPES.CHINA,
        currency=CURRENCY_TYPES.CNY,
        list_date="1999-11-10",
        delist_date="2099-12-31",
    )


def _make_tradeday():
    return TradeDay(
        market=MARKET_TYPES.CHINA,
        is_open=True,
        timestamp="2024-01-15",
    )


def _make_transfer():
    return Transfer(
        portfolio_id="p-1",
        engine_id="e-1",
        task_id="t-1",
        direction=TRANSFERDIRECTION_TYPES.IN,
        market=MARKET_TYPES.CHINA,
        money=10000,
        status=TRANSFERSTATUS_TYPES.PENDING,
        timestamp="2026-06-14 10:00:00",
    )


def _make_adjustfactor():
    return Adjustfactor(
        code="SH600000",
        timestamp="2024-01-15",
        fore_adjustfactor=1.23,
        back_adjustfactor=0.81,
        adjustfactor=1.0,
    )


# ---- pair table(Mapper 路径 / CRUD 路径)----
PAIRS = [
    pytest.param(
        _make_order,
        lambda e: OrderMapper.to_model(e),
        lambda e: _crud_invoke(OrderCRUD, "_convert_input_item", e),
        id="order",
    ),
    pytest.param(
        _make_signal,
        lambda e: SignalMapper.to_model(e),
        lambda e: _crud_invoke(SignalCRUD, "_convert_input_item", e),
        id="signal",
    ),
    pytest.param(
        _make_capital,
        lambda e: CapitalAdjustmentMapper.to_model(e),
        lambda e: _crud_invoke(CapitalAdjustmentCRUD, "_convert_input_item", e),
        id="capital_adjustment",
    ),
    pytest.param(
        _make_bar,
        lambda e: BarMapper.to_model(e),
        lambda e: _crud_invoke(BarCRUD, "_convert_input_item", e),
        id="bar",
    ),
    pytest.param(
        _make_tick,
        lambda e: TickMapper.to_model(e, MTick),
        lambda e: _crud_invoke(TickCRUD, "_convert_to_model", e, MTick),
        id="tick",
    ),
    pytest.param(
        _make_stockinfo,
        lambda e: StockInfoMapper.to_model(e),
        lambda e: _crud_invoke(StockInfoCRUD, "_convert_input_item", e),
        id="stockinfo",
    ),
    pytest.param(
        _make_tradeday,
        lambda e: TradeDayMapper.to_model(e),
        lambda e: _crud_invoke(TradeDayCRUD, "_convert_input_item", e),
        id="tradeday",
    ),
    pytest.param(
        _make_transfer,
        lambda e: TransferMapper.to_model(e),
        lambda e: _crud_invoke(TransferCRUD, "_convert_input_item", e),
        id="transfer",
    ),
    pytest.param(
        _make_adjustfactor,
        lambda e: AdjustfactorMapper.to_model(e),
        lambda e: _crud_invoke(AdjustfactorCRUD, "_convert_input_item", e),
        id="adjustfactor",
    ),
]


@pytest.mark.parametrize("make_entity, mapper_fn, crud_fn", PAIRS)
def test_to_model_mirrors_crud_override(make_entity, mapper_fn, crud_fn):
    """Mapper.to_model 与 CRUD override 产出 ORM __dict__ 严格相等(strict mirror 契约)。

    阶段1 门禁:任一字段分歧=Mapper 未忠实镜像 CRUD override 入库现状,需修正 Mapper
    (不修 CRUD,阶段1 零迁移)。阶段2 override 迁移后本契约必须保持绿(零行为变更门禁)。
    """
    entity = make_entity()
    mapper_model = mapper_fn(entity)
    crud_model = crud_fn(entity)
    md, cd = _orm_dict(mapper_model), _orm_dict(crud_model)
    only_mapper = {k: md[k] for k in md.keys() - cd.keys()}
    only_crud = {k: cd[k] for k in cd.keys() - md.keys()}
    diff = {k: (md[k], cd[k]) for k in md.keys() & cd.keys() if md[k] != cd[k]}
    assert md == cd, (
        "strict mirror 契约破坏:Mapper 与 CRUD override ORM 状态分歧\n"
        f"  仅 Mapper 有: {only_mapper}\n"
        f"  仅 CRUD  有: {only_crud}\n"
        f"  值分歧   : {diff}"
    )


@pytest.mark.skip(reason="ADR-029 阶段1 Position 特例:to_model 唯一活跃调用方 "
                  "portfolio_base.snapshot_state 依赖 settlement 三件套+uuid,strict mirror "
                  "会静默损坏。留阶段3另立 ADR 以 Mapper 为单一真相源修。")
def test_to_model_mirrors_crud_override_position():
    """Position strict mirror 占位(见 skip reason)。"""
