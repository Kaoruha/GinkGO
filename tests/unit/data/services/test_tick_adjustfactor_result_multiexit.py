"""
ADR-010 Phase 4 Task R1c：TickService / AdjustfactorService / ResultService 多出口契约测试。

补 get_ticks_df() / get_adjustfactors_df() / get_analyzer_values_df()：data 是 pandas.DataFrame
（类型即契约），消除未来消费者「result.data.to_dataframe()」绕多出口的反模式。

消费点：
- tick：data_cli.py:307 调 tick_service.get(code,start,end) → 新出口 get_ticks_df
- adjustfactor：data_cli.py:359 注释占位（R1c 不迁）→ 新出口 get_adjustfactors_df
- analyzer：flat_cli.py:768 调 get_analyzer_values 再 to_dataframe
  → 新出口 get_analyzer_values_df（对应 result_service.get_analyzer_values()）

设计：Mock crud_repo.find / get_by_task_id 返真实 ModelList（带 mock crud 支持
to_dataframe），断言 data 运行时类型契约（isinstance），参照 test_signal_order_position_multiexit.py。
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
from ginkgo.data.services.tick_service import TickService
from ginkgo.data.services.adjustfactor_service import AdjustfactorService
from ginkgo.data.services.result_service import ResultService


# ===== 桩工厂 =====


def _make_empty_modellist() -> ModelList:
    crud_stub = MagicMock()
    crud_stub._convert_models_to_dataframe.return_value = pd.DataFrame()
    return ModelList([], crud_stub)


def _make_tick_modellist() -> ModelList:
    from ginkgo.data.models import MTick

    model = MTick()
    crud_stub = MagicMock()
    crud_stub._convert_models_to_dataframe.return_value = pd.DataFrame(
        [{"code": "000001.SZ", "price": 10.0, "volume": 100}]
    )
    return ModelList([model], crud_stub)


def _make_adjustfactor_modellist() -> ModelList:
    from ginkgo.data.models import MAdjustfactor

    model = MAdjustfactor()
    crud_stub = MagicMock()
    crud_stub._convert_models_to_dataframe.return_value = pd.DataFrame(
        [{"code": "000001.SZ", "adjust_factor": 1.0}]
    )
    return ModelList([model], crud_stub)


def _make_analyzer_modellist() -> ModelList:
    from ginkgo.data.models import MAnalyzerRecord

    model = MAnalyzerRecord()
    crud_stub = MagicMock()
    crud_stub._convert_models_to_dataframe.return_value = pd.DataFrame(
        [{"name": "net_value", "value": 1.05}]
    )
    return ModelList([model], crud_stub)


def _make_tick_service(find_return) -> TickService:
    with patch("ginkgo.libs.GLOG"):
        crud_repo = MagicMock()
        crud_repo.find.return_value = find_return
        stockinfo = MagicMock()
        stockinfo.exists.return_value = True
        data_source = MagicMock()
        svc = TickService(
            data_source=data_source,
            stockinfo_service=stockinfo,
            crud_repo=crud_repo,
        )
    return svc


def _make_adjustfactor_service(find_return) -> AdjustfactorService:
    with patch("ginkgo.libs.GLOG"):
        crud_repo = MagicMock()
        crud_repo.find.return_value = find_return
        stockinfo = MagicMock()
        stockinfo.exists.return_value = True
        data_source = MagicMock()
        svc = AdjustfactorService(
            crud_repo=crud_repo,
            data_source=data_source,
            stockinfo_service=stockinfo,
        )
    return svc


def _make_result_service(get_return) -> ResultService:
    with patch("ginkgo.libs.GLOG"):
        analyzer_crud = MagicMock()
        analyzer_crud.get_by_task_id.return_value = get_return
        svc = ResultService(analyzer_crud=analyzer_crud)
    return svc


# ===== TickService get_ticks_df =====


@pytest.mark.unit
def test_get_ticks_df_method_exists():
    assert hasattr(TickService, "get_ticks_df")
    sig = inspect.signature(TickService.get_ticks_df)
    # filter 域对齐 get()：code / start_date / end_date
    assert "code" in sig.parameters
    assert "start_date" in sig.parameters
    assert "end_date" in sig.parameters


@pytest.mark.unit
def test_get_ticks_df_returns_dataframe():
    """出口①：data 是 pd.DataFrame，非 ModelList。"""
    svc = _make_tick_service(_make_tick_modellist())
    result = svc.get_ticks_df(code="000001.SZ", start_date="2026-01-01", end_date="2026-01-02")
    assert result.success is True
    assert isinstance(result.data, pd.DataFrame)
    assert not isinstance(result.data, ModelList)
    assert len(result.data) == 1


@pytest.mark.unit
def test_get_ticks_df_empty_returns_empty_dataframe():
    """空结果 data 仍是 pd.DataFrame（非 None / 非 ModelList）。"""
    svc = _make_tick_service(_make_empty_modellist())
    result = svc.get_ticks_df(code="000001.SZ")
    assert result.success is True
    assert isinstance(result.data, pd.DataFrame)
    assert len(result.data) == 0
    assert not isinstance(result.data, ModelList)


@pytest.mark.unit
def test_get_ticks_df_db_failure():
    """crud_repo.find 抛异常时 success is False。"""
    svc = _make_tick_service(_make_empty_modellist())
    svc._crud_repo.find.side_effect = Exception("DB down")
    result = svc.get_ticks_df(code="000001.SZ")
    assert result.success is False


@pytest.mark.unit
def test_get_ticks_df_filters_construction():
    """_build_tick_filters 字段映射正确，与 get() 一致（code/timestamp__gte/timestamp__lte）。"""
    svc = _make_tick_service(_make_empty_modellist())
    filters = svc._build_tick_filters(
        code="000001.SZ",
        start_date="2026-01-01",
        end_date="2026-01-02",
    )
    assert filters["code"] == "000001.SZ"
    assert "timestamp__gte" in filters  # start_date → timestamp__gte
    assert "timestamp__lte" in filters  # end_date → timestamp__lte
    assert filters["timestamp__gte"] is not None
    assert filters["timestamp__lte"] is not None


@pytest.mark.unit
def test_get_ticks_df_filters_partial():
    """只传 code 时 filters 不含 timestamp 键（与 get() 行为一致）。"""
    svc = _make_tick_service(_make_empty_modellist())
    filters = svc._build_tick_filters(code="000001.SZ")
    assert filters == {"code": "000001.SZ"}


# ===== AdjustfactorService get_adjustfactors_df =====


@pytest.mark.unit
def test_get_adjustfactors_df_method_exists():
    assert hasattr(AdjustfactorService, "get_adjustfactors_df")
    sig = inspect.signature(AdjustfactorService.get_adjustfactors_df)
    # filter 域对齐 get()：code / start_date / end_date / adjust_type
    assert "code" in sig.parameters
    assert "start_date" in sig.parameters
    assert "end_date" in sig.parameters
    assert "adjust_type" in sig.parameters


@pytest.mark.unit
def test_get_adjustfactors_df_returns_dataframe():
    """出口①：data 是 pd.DataFrame，非 ModelList。"""
    svc = _make_adjustfactor_service(_make_adjustfactor_modellist())
    result = svc.get_adjustfactors_df(code="000001.SZ")
    assert result.success is True
    assert isinstance(result.data, pd.DataFrame)
    assert not isinstance(result.data, ModelList)
    assert len(result.data) == 1


@pytest.mark.unit
def test_get_adjustfactors_df_empty_returns_empty_dataframe():
    """空结果 data 仍是 pd.DataFrame。"""
    svc = _make_adjustfactor_service(_make_empty_modellist())
    result = svc.get_adjustfactors_df(code="000001.SZ")
    assert result.success is True
    assert isinstance(result.data, pd.DataFrame)
    assert len(result.data) == 0
    assert not isinstance(result.data, ModelList)


@pytest.mark.unit
def test_get_adjustfactors_df_db_failure():
    """crud_repo.find 抛异常时 success is False。"""
    svc = _make_adjustfactor_service(_make_empty_modellist())
    svc._crud_repo.find.side_effect = Exception("DB down")
    result = svc.get_adjustfactors_df(code="000001.SZ")
    assert result.success is False


@pytest.mark.unit
def test_get_adjustfactors_df_filters_construction():
    """_build_adjustfactor_filters 字段映射正确（code/timestamp__gte/timestamp__lte/adjust_type）。"""
    svc = _make_adjustfactor_service(_make_empty_modellist())
    filters = svc._build_adjustfactor_filters(
        code="000001.SZ",
        start_date="2026-01-01",
        end_date="2026-01-02",
        adjust_type="fore",
    )
    assert filters["code"] == "000001.SZ"
    assert "timestamp__gte" in filters
    assert "timestamp__lte" in filters
    assert filters["adjust_type"] == "fore"


# ===== ResultService get_analyzer_values_df =====


@pytest.mark.unit
def test_get_analyzer_values_df_method_exists():
    assert hasattr(ResultService, "get_analyzer_values_df")
    sig = inspect.signature(ResultService.get_analyzer_values_df)
    # filter 域对齐 get_analyzer_values()：task_id / portfolio_id / analyzer_name
    assert "task_id" in sig.parameters
    assert "portfolio_id" in sig.parameters
    assert "analyzer_name" in sig.parameters


@pytest.mark.unit
def test_get_analyzer_values_df_returns_dataframe():
    """出口①：data 是 pd.DataFrame，非 ModelList。"""
    svc = _make_result_service(_make_analyzer_modellist())
    result = svc.get_analyzer_values_df(task_id="task1")
    assert result.success is True
    assert isinstance(result.data, pd.DataFrame)
    assert not isinstance(result.data, ModelList)
    assert len(result.data) == 1


@pytest.mark.unit
def test_get_analyzer_values_df_empty_returns_empty_dataframe():
    """空结果 data 仍是 pd.DataFrame。"""
    svc = _make_result_service(_make_empty_modellist())
    result = svc.get_analyzer_values_df(task_id="task1")
    assert result.success is True
    assert isinstance(result.data, pd.DataFrame)
    assert len(result.data) == 0
    assert not isinstance(result.data, ModelList)


@pytest.mark.unit
def test_get_analyzer_values_df_db_failure():
    """crud_repo.get_by_task_id 抛异常时 success is False。"""
    svc = _make_result_service(_make_empty_modellist())
    svc._crud_repo.get_by_task_id.side_effect = Exception("DB down")
    result = svc.get_analyzer_values_df(task_id="task1")
    assert result.success is False


@pytest.mark.unit
def test_get_analyzer_values_df_empty_task_id():
    """task_id 为空时 success is False（与 get_analyzer_values() 一致）。"""
    svc = _make_result_service(_make_empty_modellist())
    result = svc.get_analyzer_values_df(task_id="")
    assert result.success is False
