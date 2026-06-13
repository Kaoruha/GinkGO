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
from ginkgo.enums import FREQUENCY_TYPES


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
