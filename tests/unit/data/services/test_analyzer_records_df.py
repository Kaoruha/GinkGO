"""
ADR-010 Phase 4 Task R2b：AnalyzerService.get_records_df() 多出口契约测试。

补 get_records_df()：data 是 pandas.DataFrame（类型即契约），消除消费者
``result.data.to_dataframe()`` 反模式（record_cli.py:258）。

消费点（record_cli.py）：
- analyzer 消费 get_records(portfolio_id, engine_id, page_size) → 新出口 get_records_df

设计：Mock crud_repo.find 返真实 ModelList（带 mock crud 支持 to_dataframe），
断言 data 运行时类型契约（isinstance），参照 test_signal_order_position_multiexit.py 桩写法。
"""

import sys
import os
import inspect

import pytest
import pandas as pd
from unittest.mock import patch, MagicMock

_path = os.path.join(os.path.dirname(__file__), "..", "..", "..")
if _path not in sys.path:
    sys.path.insert(0, _path)

from ginkgo.data.crud.model_conversion import ModelList
from ginkgo.data.services.analyzer_service import AnalyzerService


# ===== 桩工厂 =====


def _make_empty_modellist() -> ModelList:
    crud_stub = MagicMock()
    crud_stub._convert_models_to_dataframe.return_value = pd.DataFrame()
    return ModelList([], crud_stub)


def _make_analyzer_modellist() -> ModelList:
    from ginkgo.data.models import MAnalyzerRecord

    model = MAnalyzerRecord()
    crud_stub = MagicMock()
    crud_stub._convert_models_to_dataframe.return_value = pd.DataFrame(
        [{"name": "SharpeRatio", "value": 1.5}]
    )
    return ModelList([model], crud_stub)


def _make_analyzer_service(find_return) -> AnalyzerService:
    with patch("ginkgo.libs.GLOG"):
        crud_repo = MagicMock()
        crud_repo.find.return_value = find_return
        svc = AnalyzerService(analyzer_crud=crud_repo)
    return svc


# ===== AnalyzerService get_records_df =====


@pytest.mark.unit
def test_get_records_df_method_exists():
    assert hasattr(AnalyzerService, "get_records_df")
    sig = inspect.signature(AnalyzerService.get_records_df)
    # filter 域对齐 get_records()：portfolio_id / engine_id / page_size
    assert "portfolio_id" in sig.parameters
    assert "engine_id" in sig.parameters
    assert "page_size" in sig.parameters


@pytest.mark.unit
def test_get_records_df_returns_dataframe():
    """出口①：data 是 pd.DataFrame，非 ModelList。"""
    svc = _make_analyzer_service(_make_analyzer_modellist())
    result = svc.get_records_df(portfolio_id="pf1", engine_id="eng1")
    assert result.success is True
    assert isinstance(result.data, pd.DataFrame)
    assert not isinstance(result.data, ModelList)
    assert len(result.data) == 1


@pytest.mark.unit
def test_get_records_df_empty_returns_empty_dataframe():
    """空结果 data 仍是 pd.DataFrame（非 None / 非 ModelList）。"""
    svc = _make_analyzer_service(_make_empty_modellist())
    result = svc.get_records_df()
    assert result.success is True
    assert isinstance(result.data, pd.DataFrame)
    assert len(result.data) == 0
    assert not isinstance(result.data, ModelList)


@pytest.mark.unit
def test_get_records_df_db_failure():
    """crud_repo.find 抛异常时 success is False。"""
    svc = _make_analyzer_service(_make_empty_modellist())
    svc._crud_repo.find.side_effect = Exception("DB down")
    result = svc.get_records_df()
    assert result.success is False


# ===== filter 构造正确性（_build_analyzer_record_filters 字段映射 + is_del 固定注入） =====


@pytest.mark.unit
def test_build_analyzer_record_filters_construction():
    """_build_analyzer_record_filters 字段映射：portfolio_id / engine_id / is_del=False。"""
    svc = _make_analyzer_service(_make_empty_modellist())
    filters = svc._build_analyzer_record_filters(
        portfolio_id="pf1", engine_id="eng1",
    )
    assert filters["portfolio_id"] == "pf1"
    assert filters["engine_id"] == "eng1"
    assert filters["is_del"] is False


@pytest.mark.unit
def test_build_analyzer_record_filters_optional_omitted():
    """portfolio_id/engine_id 为空时不注入对应键，is_del 恒定 False。"""
    svc = _make_analyzer_service(_make_empty_modellist())
    filters = svc._build_analyzer_record_filters(portfolio_id=None, engine_id=None)
    assert "portfolio_id" not in filters
    assert "engine_id" not in filters
    assert filters["is_del"] is False
