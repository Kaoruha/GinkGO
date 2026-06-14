"""
ADR-010 Phase 4 Task R1a：EngineService / PortfolioService 多出口方法契约测试。

补 get_engines_df() / get_portfolios_df()：data 是 pandas.DataFrame（类型即契约），
消除未来消费者「result.data.to_dataframe()」绕多出口的反模式。

设计：Mock crud_repo.find 返真实 ModelList（带 mock crud 支持 to_dataframe），
断言 data 运行时类型契约（isinstance），**不**用 inspect.getsource 字符串 grep。
参照 test_bar_multiexit.py 的桩写法。
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
from ginkgo.data.services.engine_service import EngineService
from ginkgo.data.services.portfolio_service import PortfolioService


# ===== 桩工厂 =====


def _make_empty_modellist() -> ModelList:
    crud_stub = MagicMock()
    crud_stub._convert_models_to_dataframe.return_value = pd.DataFrame()
    return ModelList([], crud_stub)


def _make_engine_modellist() -> ModelList:
    from ginkgo.data.models import MEngine

    model = MEngine(name="test-engine", is_live=False)
    crud_stub = MagicMock()
    crud_stub._convert_models_to_dataframe.return_value = pd.DataFrame(
        [{"name": "test-engine", "is_live": False}]
    )
    return ModelList([model], crud_stub)


def _make_portfolio_modellist() -> ModelList:
    from ginkgo.data.models import MPortfolio

    model = MPortfolio(name="test-portfolio")
    crud_stub = MagicMock()
    crud_stub._convert_models_to_dataframe.return_value = pd.DataFrame(
        [{"name": "test-portfolio"}]
    )
    return ModelList([model], crud_stub)


def _make_engine_service(find_return) -> EngineService:
    with patch("ginkgo.libs.GLOG"):
        crud_repo = MagicMock()
        crud_repo.find.return_value = find_return
        mapping_crud = MagicMock()
        param_crud = MagicMock()
        svc = EngineService(
            crud_repo=crud_repo,
            engine_portfolio_mapping_crud=mapping_crud,
            param_crud=param_crud,
        )
    return svc


def _make_portfolio_service(find_return) -> PortfolioService:
    with patch("ginkgo.libs.GLOG"):
        crud_repo = MagicMock()
        crud_repo.find.return_value = find_return
        file_mapping_crud = MagicMock()
        svc = PortfolioService(
            crud_repo=crud_repo,
            portfolio_file_mapping_crud=file_mapping_crud,
        )
    return svc


# ===== EngineService get_engines_df =====


@pytest.mark.unit
def test_get_engines_df_method_exists():
    assert hasattr(EngineService, "get_engines_df")
    sig = inspect.signature(EngineService.get_engines_df)
    # filter 域对齐 get()：engine_id / name / is_live / status
    assert "engine_id" in sig.parameters
    assert "name" in sig.parameters
    assert "is_live" in sig.parameters
    assert "status" in sig.parameters


@pytest.mark.unit
def test_get_engines_df_returns_dataframe():
    """出口①：data 是 pd.DataFrame，非 ModelList。"""
    svc = _make_engine_service(_make_engine_modellist())
    result = svc.get_engines_df(name="test-engine")
    assert result.success is True
    assert isinstance(result.data, pd.DataFrame)
    assert not isinstance(result.data, ModelList)
    assert len(result.data) == 1


@pytest.mark.unit
def test_get_engines_df_empty_returns_empty_dataframe():
    """空结果 data 仍是 pd.DataFrame（非 None / 非 ModelList）。"""
    svc = _make_engine_service(_make_empty_modellist())
    result = svc.get_engines_df()
    assert result.success is True
    assert isinstance(result.data, pd.DataFrame)
    assert len(result.data) == 0
    assert not isinstance(result.data, ModelList)


@pytest.mark.unit
def test_get_engines_df_db_failure():
    """crud_repo.find 抛异常时 success is False。"""
    svc = _make_engine_service(_make_empty_modellist())
    svc._crud_repo.find.side_effect = Exception("DB down")
    result = svc.get_engines_df()
    assert result.success is False


# ===== PortfolioService get_portfolios_df =====


@pytest.mark.unit
def test_get_portfolios_df_method_exists():
    assert hasattr(PortfolioService, "get_portfolios_df")
    sig = inspect.signature(PortfolioService.get_portfolios_df)
    # filter 域对齐 get()：portfolio_id / name / mode / state
    assert "portfolio_id" in sig.parameters
    assert "name" in sig.parameters
    assert "mode" in sig.parameters
    assert "state" in sig.parameters


@pytest.mark.unit
def test_get_portfolios_df_returns_dataframe():
    """出口①：data 是 pd.DataFrame，非 ModelList。"""
    svc = _make_portfolio_service(_make_portfolio_modellist())
    result = svc.get_portfolios_df(name="test-portfolio")
    assert result.success is True
    assert isinstance(result.data, pd.DataFrame)
    assert not isinstance(result.data, ModelList)
    assert len(result.data) == 1


@pytest.mark.unit
def test_get_portfolios_df_empty_returns_empty_dataframe():
    """空结果 data 仍是 pd.DataFrame。"""
    svc = _make_portfolio_service(_make_empty_modellist())
    result = svc.get_portfolios_df()
    assert result.success is True
    assert isinstance(result.data, pd.DataFrame)
    assert len(result.data) == 0
    assert not isinstance(result.data, ModelList)


@pytest.mark.unit
def test_get_portfolios_df_db_failure():
    """crud_repo.find 抛异常时 success is False。"""
    svc = _make_portfolio_service(_make_empty_modellist())
    svc._crud_repo.find.side_effect = Exception("DB down")
    result = svc.get_portfolios_df()
    assert result.success is False


# ===== filter 构造正确性（_build_*_filters 字段映射 + is_del 固定注入） =====


@pytest.mark.unit
def test_build_portfolio_filters_construction():
    """_build_portfolio_filters 字段映射：portfolio_id→uuid / name / mode(validate_input→int) / is_del=False。"""
    from ginkgo.enums import PORTFOLIO_MODE_TYPES

    svc = _make_portfolio_service(_make_empty_modellist())
    filters = svc._build_portfolio_filters(
        portfolio_id="uid", name="n", mode=PORTFOLIO_MODE_TYPES.LIVE,
    )
    assert filters["uuid"] == "uid"
    assert filters["name"] == "n"
    assert filters["mode"] == PORTFOLIO_MODE_TYPES.LIVE.value
    assert filters["is_del"] is False


@pytest.mark.unit
def test_build_engine_filters_construction():
    """_build_engine_filters 字段映射：engine_id→uuid / name / is_live / status / is_del=False。"""
    from ginkgo.enums import ENGINESTATUS_TYPES

    svc = _make_engine_service(_make_empty_modellist())
    filters = svc._build_engine_filters(
        engine_id="uid", name="n", is_live=True, status=ENGINESTATUS_TYPES.RUNNING,
    )
    assert filters["uuid"] == "uid"
    assert filters["name"] == "n"
    assert filters["is_live"] is True
    assert filters["status"] == ENGINESTATUS_TYPES.RUNNING
    assert filters["is_del"] is False
