"""MTick / MSignal / MStockInfo enum ``if not None`` 分支覆盖（ADR-029 Task 2/3/6）。

``validate_input(x) or -1`` 在 x=OTHER(0)/NEUTRAL(0) 时被 falsy 吞，
改为 ``_v if _v is not None else -1``。本测覆盖三 model 的 ``update(str)`` /
``update(pd.Series)`` enum 字段分支：
- 合法 enum → 保真 ``.value``
- 非法值 → validate 返 None → -1
- 0（NEUTRAL/OTHER）→ 保真 0（核心 fix，不被 ``or`` 吞）
"""
import pandas as pd

from ginkgo.data.models.model_tick import MTick
from ginkgo.data.models.model_signal import MSignal
from ginkgo.data.models.model_stock_info import MStockInfo
from ginkgo.enums import (
    TICKDIRECTION_TYPES,
    DIRECTION_TYPES,
    SOURCE_TYPES,
    CURRENCY_TYPES,
    MARKET_TYPES,
)


# ---------------- MTick ----------------
def test_tick_update_str_enum_branches():
    """update(str)：合法保真；非法 str→-1；NEUTRAL(0) 保真不被吞。"""
    t = MTick()
    t.update(
        "000001",
        price=10,
        volume=100,
        direction=TICKDIRECTION_TYPES.ACTIVEBUY,   # 合法
        source="bogus_source",               # 非法 str → -1
    )
    assert t.direction == TICKDIRECTION_TYPES.ACTIVEBUY.value
    assert t.source == -1


def test_tick_update_str_other_zero_not_swallowed():
    """direction=NEUTRAL(0) 保真（旧 ``or -1`` 会吞成 -1）。"""
    t = MTick()
    t.update("000001", direction=0, source=0)  # 0 是合法值
    assert t.direction == 0
    assert t.source == 0


def test_tick_update_series_enum_branches():
    """update(pd.Series)：direction 必填分支 + source 可选分支。"""
    t = MTick()
    s = pd.Series(
        {
            "code": "000001",
            "price": 10,
            "volume": 100,
            "direction": TICKDIRECTION_TYPES.ACTIVESELL.value,
            "timestamp": "2025-01-02",
            "source": SOURCE_TYPES.MANUAL.value,
        }
    )
    t.update(s)
    assert t.direction == TICKDIRECTION_TYPES.ACTIVESELL.value
    assert t.source == SOURCE_TYPES.MANUAL.value


# ---------------- MSignal ----------------
def test_signal_update_str_enum_branches():
    """update(str)：合法保真；非法 str→-1；OTHER(0) 保真不被吞。"""
    s = MSignal()
    s.update(
        "p",
        "e",
        direction=DIRECTION_TYPES.LONG,   # 合法
        source="bogus_source",            # 非法 → -1
    )
    assert s.direction == DIRECTION_TYPES.LONG.value
    assert s.source == -1


def test_signal_update_str_other_zero_not_swallowed():
    """direction=OTHER(0) 保真（旧 ``or -1`` 会吞成 -1）。"""
    s = MSignal()
    s.update("p", "e", direction=0, source=0)
    assert s.direction == 0
    assert s.source == 0


def test_signal_update_series_enum_branches():
    """update(pd.Series)：direction 必填 + source 可选分支。"""
    s = MSignal()
    df = pd.Series(
        {
            "portfolio_id": "p",
            "engine_id": "e",
            "timestamp": "2025-01-02",
            "code": "000001",
            "direction": DIRECTION_TYPES.SHORT.value,
            "reason": "r",
            "source": SOURCE_TYPES.TUSHARE.value,
        }
    )
    s.update(df)
    assert s.direction == DIRECTION_TYPES.SHORT.value
    assert s.source == SOURCE_TYPES.TUSHARE.value


# ---------------- MStockInfo ----------------
def test_stock_info_update_str_enum_branches():
    """update(str)：currency/market/source 合法保真 + 非法→-1。"""
    si = MStockInfo("000001")
    si.update(
        "000001",
        currency="bogus_currency",          # 非法 → -1
        market=MARKET_TYPES.CHINA,          # 合法
        source=SOURCE_TYPES.MANUAL,         # 合法
    )
    assert si.currency == -1
    assert si.market == MARKET_TYPES.CHINA.value
    assert si.source == SOURCE_TYPES.MANUAL.value


def test_stock_info_update_series_enum_branches():
    """update(pd.Series)：currency/market 必填 + source 可选分支。"""
    si = MStockInfo("000001")
    df = pd.Series(
        {
            "code": "000001",
            "code_name": "test",
            "industry": "tech",
            "currency": CURRENCY_TYPES.CNY.value,
            "market": MARKET_TYPES.CHINA.value,
            "list_date": "2025-01-02",
            "delist_date": None,
            "source": SOURCE_TYPES.TUSHARE.value,
        }
    )
    si.update(df)
    assert si.currency == CURRENCY_TYPES.CNY.value
    assert si.market == MARKET_TYPES.CHINA.value
    assert si.source == SOURCE_TYPES.TUSHARE.value
