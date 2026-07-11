"""
ADR-010 Phase 4 Task 4.2：BarService 多出口方法契约测试（类型即契约）。

回测热路径走 DF，故 BarService 重点在 _df 出口。出口② Entity 同步补齐。

设计：Mock crud_repo.find 返真实 ModelList（带 mock crud_instance 支持
to_dataframe），断言 data 运行时类型。不复权（adjustment_type=NONE）以
隔离复权逻辑，专注多出口契约本身。
"""

import sys
import os
import inspect

import pytest
import pandas as pd
from datetime import datetime
from unittest.mock import patch, MagicMock

_path = os.path.join(os.path.dirname(__file__), "..", "..", "..")
if _path not in sys.path:
    sys.path.insert(0, _path)

from ginkgo.data.crud.model_conversion import ModelList
from ginkgo.data.services.bar_service import BarService
from ginkgo.entities import Bar
from ginkgo.enums import FREQUENCY_TYPES, ADJUSTMENT_TYPES


def _make_empty_modellist() -> ModelList:
    crud_stub = MagicMock()
    crud_stub._convert_models_to_dataframe.return_value = pd.DataFrame()
    return ModelList([], crud_stub)


def _make_bar_modellist() -> ModelList:
    from ginkgo.data.models import MBar

    model = MBar(code="000001", open=10.0, high=11.0, low=9.5, close=10.5,
                 volume=1000, amount=10500.0, frequency=1)
    crud_stub = MagicMock()
    crud_stub._convert_models_to_dataframe.return_value = pd.DataFrame(
        [{"code": "000001", "open": 10.0}]
    )
    return ModelList([model], crud_stub)


def _make_service(find_return) -> BarService:
    with patch("ginkgo.libs.GLOG"):
        crud_repo = MagicMock()
        crud_repo.find.return_value = find_return
        data_source = MagicMock()
        stockinfo_svc = MagicMock()
        svc = BarService(
            crud_repo=crud_repo, data_source=data_source,
            stockinfo_service=stockinfo_svc,
        )
    return svc


# ===== 出口① get_bars_df =====


@pytest.mark.unit
def test_get_bars_df_returns_dataframe_empty():
    """出口①：空结果 data 是 pd.DataFrame（不复权，隔离复权逻辑）。"""
    svc = _make_service(_make_empty_modellist())
    result = svc.get_bars_df(
        code="000001", start_date=datetime(2024, 1, 1),
        end_date=datetime(2024, 1, 2),
    )
    assert result.success is True
    assert isinstance(result.data, pd.DataFrame)
    assert not isinstance(result.data, ModelList)


@pytest.mark.unit
def test_get_bars_df_method_exists():
    assert hasattr(BarService, "get_bars_df")
    sig = inspect.signature(BarService.get_bars_df)
    assert "code" in sig.parameters
    assert "start_date" in sig.parameters


# ===== 出口② get_bars =====


@pytest.mark.unit
def test_get_bars_returns_empty_list():
    svc = _make_service(_make_empty_modellist())
    result = svc.get_bars(
        code="000001", start_date=datetime(2024, 1, 1),
        end_date=datetime(2024, 1, 2),
    )
    assert result.success is True
    assert result.data == []
    assert isinstance(result.data, list)
    assert not isinstance(result.data, ModelList)


@pytest.mark.unit
def test_get_bars_returns_entity_list():
    svc = _make_service(_make_bar_modellist())
    result = svc.get_bars(
        code="000001", start_date=datetime(2024, 1, 1),
        end_date=datetime(2024, 1, 2),
    )
    assert result.success is True
    assert isinstance(result.data, list)
    assert len(result.data) == 1
    assert isinstance(result.data[0], Bar)
    assert result.data[0].code == "000001"


# ===== 异常路径：find 抛异常 -> ServiceResult.error（error/message 分离） =====


@pytest.mark.unit
def test_get_bars_df_db_failure_returns_error():
    """出口① get_bars_df：crud_repo.find 抛异常时返 error，error 含异常信息。

    BarService 两出口用 ServiceResult.error(error=...)——error 字段携带
    "Database operation failed: {exc}"；message 未传时默认取 error（== error），
    与 StockinfoService 的 failure 语义不同（error 与 message 此处相等但来源不同）。
    """
    svc = _make_service(_make_empty_modellist())
    svc._crud_repo.find.side_effect = Exception("db down")
    result = svc.get_bars_df(
        code="000001", start_date=datetime(2024, 1, 1),
        end_date=datetime(2024, 1, 2),
    )
    assert result.success is False
    assert "db down" in result.error
    assert "Database operation failed" in result.error


@pytest.mark.unit
def test_get_bars_db_failure_returns_error():
    """出口② get_bars：crud_repo.find 抛异常时返 error，error 含异常信息。"""
    svc = _make_service(_make_empty_modellist())
    svc._crud_repo.find.side_effect = Exception("db down")
    result = svc.get_bars(
        code="000001", start_date=datetime(2024, 1, 1),
        end_date=datetime(2024, 1, 2),
    )
    assert result.success is False
    assert "db down" in result.error
    assert "Database operation failed" in result.error


# ===== 出口① get_bars_df 复权路径（#6624：DF 出口内化复权，消除 feeder ModelList 泄漏） =====
#
# ADR-010 例外：feeder/sizer 回测热路径依赖 get(FORE) 前复权（除权除息日 K 线不跳空、
# ATR/仓位拆股后不错算）。盲迁不复权的 get_bars_df() 会静默错算（编译过、测试可能过、
# 结果错——测试库无 adjustfactor，复权 no-op，掩盖回归）。故 DF 出口须能承载复权，
# feeder 传 FORE 保行为一致。


@pytest.mark.unit
def test_get_bars_df_fore_applies_single_stock_adjustment():
    """出口① 复权路径：get_bars_df(code, adjustment_type=FORE) 走单股复权分支。

    断言 _apply_price_adjustment_to_modellist 被调用（与 get(FORE) 同一复权入口），
    且返回 data 是 DataFrame（ModelList 不出 Service 边界）。
    """
    svc = _make_service(_make_bar_modellist())
    svc._apply_price_adjustment_to_modellist = MagicMock(
        side_effect=lambda ml, code, adj: ml
    )
    result = svc.get_bars_df(
        code="000001", start_date=datetime(2024, 1, 1),
        end_date=datetime(2024, 1, 2), adjustment_type=ADJUSTMENT_TYPES.FORE,
    )
    assert result.success is True
    assert isinstance(result.data, pd.DataFrame)
    assert not isinstance(result.data, ModelList)
    svc._apply_price_adjustment_to_modellist.assert_called_once()


@pytest.mark.unit
def test_get_bars_df_fore_multi_stock_uses_multi_adjustment():
    """出口① 复权路径：get_bars_df(code=None, adjustment_type=FORE) 走多股复权分支。"""
    svc = _make_service(_make_bar_modellist())
    svc._apply_price_adjustment_multi_stock = MagicMock(
        side_effect=lambda ml, adj: ml
    )
    result = svc.get_bars_df(
        start_date=datetime(2024, 1, 1), end_date=datetime(2024, 1, 2),
        adjustment_type=ADJUSTMENT_TYPES.FORE,
    )
    assert result.success is True
    assert isinstance(result.data, pd.DataFrame)
    svc._apply_price_adjustment_multi_stock.assert_called_once()


@pytest.mark.unit
def test_get_bars_df_fore_parity_with_get_fore_to_dataframe():
    """出口① 复权路径行为 parity：get_bars_df(FORE) == get(FORE) + 手动 .to_dataframe()。

    #6624 核心约束（AC「行为与现有回测热路径保持一致」）：DF 出口内化复权后，
    产出必须与旧热路径 (get() + .to_dataframe()) 完全一致，否则回测静默错算。
    隔离复权计算本身（mock 为透传），专注两条调用链的结构等价性。
    """
    svc = _make_service(_make_bar_modellist())
    svc._apply_price_adjustment_to_modellist = MagicMock(
        side_effect=lambda ml, code, adj: ml
    )

    df_new = svc.get_bars_df(
        code="000001", start_date=datetime(2024, 1, 1),
        end_date=datetime(2024, 1, 2), adjustment_type=ADJUSTMENT_TYPES.FORE,
    ).data

    # 旧热路径：get(FORE) 返 ModelList 后手动 .to_dataframe()
    df_old = svc.get(
        code="000001", start_date=datetime(2024, 1, 1),
        end_date=datetime(2024, 1, 2),
    ).data.to_dataframe()

    pd.testing.assert_frame_equal(df_new, df_old)


@pytest.mark.unit
def test_get_bars_df_default_skips_adjustment():
    """出口① 默认不复权：adjustment_type 未传时走 NONE 分支，不触发复权（保现有契约）。

    回归保护：扩展 adjustment_type 参数不得改变 get_bars_df() 既有「不复权」语义。
    """
    svc = _make_service(_make_bar_modellist())
    svc._apply_price_adjustment_to_modellist = MagicMock()
    svc._apply_price_adjustment_multi_stock = MagicMock()

    result = svc.get_bars_df(
        code="000001", start_date=datetime(2024, 1, 1),
        end_date=datetime(2024, 1, 2),
    )
    assert result.success is True
    assert isinstance(result.data, pd.DataFrame)
    svc._apply_price_adjustment_to_modellist.assert_not_called()
    svc._apply_price_adjustment_multi_stock.assert_not_called()


@pytest.mark.unit
def test_get_bars_df_fore_empty_returns_empty_dataframe():
    """出口① 复权路径空结果：find 返空时返空 DataFrame（feeder 空结果场景）。"""
    svc = _make_service(_make_empty_modellist())
    svc._apply_price_adjustment_to_modellist = MagicMock()
    result = svc.get_bars_df(
        code="000001", start_date=datetime(2024, 1, 1),
        end_date=datetime(2024, 1, 2), adjustment_type=ADJUSTMENT_TYPES.FORE,
    )
    assert result.success is True
    assert isinstance(result.data, pd.DataFrame)
    assert result.data.empty
    # 空 ModelList 不进入复权分支（短路返空 DF）
    svc._apply_price_adjustment_to_modellist.assert_not_called()
