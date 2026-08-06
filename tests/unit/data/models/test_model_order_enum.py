"""MOrder enum ``if not None`` 分支覆盖（ADR-029 Task 7 I-2 fix）。

``validate_input(x) or DEFAULT`` 在 x=OTHER(0) 时被 falsy 吞（0 or 7 → 7），
改为 ``_v if _v is not None else DEFAULT``。本测覆盖 ``__init__`` /
``update(str)`` / ``update(pd.Series)`` 三方法的 enum 字段：
- 合法 enum → 保真 ``.value``
- 非法值（str / 越界 int）→ validate 返 None → DEFAULT（__init__ 用类型默认；update 用 -1）
- OTHER(0) → 保真 0（核心 fix，不被 ``or`` 吞）
"""
import pandas as pd

from ginkgo.data.models.model_order import MOrder
from ginkgo.enums import (
    DIRECTION_TYPES,
    ORDER_TYPES,
    ORDERSTATUS_TYPES,
    SOURCE_TYPES,
)


def test_init_valid_invalid_and_other_zero():
    """__init__：合法 enum 保真；非法 str→DEFAULT；OTHER(0) 保真不被吞。"""
    o = MOrder(
        portfolio_id="p",
        engine_id="e",
        direction=DIRECTION_TYPES.LONG,   # 合法 → LONG.value
        order_type="bogus_order_type",    # 非法 str → DEFAULT(LIMITORDER)
        status=ORDERSTATUS_TYPES.NEW,     # 合法 → NEW.value
        source=0,                          # OTHER(0) → 保真 0（旧 `or TUSHARE` 会吞成 7）
    )
    assert o.direction == DIRECTION_TYPES.LONG.value
    assert o.order_type == ORDER_TYPES.LIMITORDER.value
    assert o.status == ORDERSTATUS_TYPES.NEW.value
    assert o.source == 0


def test_init_other_zero_direction_not_swallowed():
    """direction=OTHER(0) 保真（不被 ``or LONG`` 吞成 1）。"""
    o = MOrder(portfolio_id="p", engine_id="e", direction=0)
    assert o.direction == 0


def test_init_invalid_int_falls_back_default():
    """越界 int（validate ValueError→None）→ DEFAULT。"""
    o = MOrder(portfolio_id="p", engine_id="e", status=9999)
    assert o.status == ORDERSTATUS_TYPES.NEW.value


def test_update_str_enum_branches():
    """update(str)：合法保真；非法 str→-1（update 的 DEFAULT）。"""
    o = MOrder(portfolio_id="p", engine_id="e")
    o.update(
        "p2",
        "e2",
        direction=DIRECTION_TYPES.SHORT,  # 合法 → SHORT.value
        status="bogus_status",             # 非法 → -1
        source=SOURCE_TYPES.MANUAL,        # 合法 → MANUAL.value
    )
    assert o.direction == DIRECTION_TYPES.SHORT.value
    assert o.status == -1
    assert o.source == SOURCE_TYPES.MANUAL.value


def test_update_str_order_type_branch():
    """update(str)：order_type 分支（L156-157）。合法保真；非法 str→-1。"""
    o = MOrder(portfolio_id="p", engine_id="e")
    o.update("p2", "e2", order_type=ORDER_TYPES.MARKETORDER)  # 合法 → MARKETORDER.value
    assert o.order_type == ORDER_TYPES.MARKETORDER.value
    o.update("p2", "e2", order_type="bogus_order_type")  # 非法 → -1
    assert o.order_type == -1


def test_update_series_enum_branches():
    """update(pd.Series)：合法保真；source 可选分支（``if "source" in df``）。"""
    o = MOrder(portfolio_id="p", engine_id="e")
    s = pd.Series(
        {
            "code": "000001",
            "direction": DIRECTION_TYPES.LONG.value,
            "order_type": ORDER_TYPES.LIMITORDER.value,
            "status": ORDERSTATUS_TYPES.NEW.value,
            "volume": 100,
            "limit_price": 10,
            "frozen_money": 0,
            "frozen_volume": 0,
            "transaction_price": 0,
            "transaction_volume": 0,
            "remain": 0,
            "fee": 0,
            "timestamp": "2025-01-02",
            "uuid": "u",
            "portfolio_id": "p",
            "engine_id": "e",
            "source": SOURCE_TYPES.TUSHARE.value,
        }
    )
    o.update(s)
    assert o.direction == DIRECTION_TYPES.LONG.value
    assert o.order_type == ORDER_TYPES.LIMITORDER.value
    assert o.status == ORDERSTATUS_TYPES.NEW.value
    assert o.source == SOURCE_TYPES.TUSHARE.value
