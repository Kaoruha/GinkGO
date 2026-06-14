"""
ADR-010 Phase 4 Task R1b：SignalService / OrderService / PositionService 多出口契约测试。

补 get_signals_df() / get_orders_df() / get_positions_df()：data 是 pandas.DataFrame
（类型即契约），消除未来消费者「result.data.to_dataframe()」绕多出口的反模式。

消费点（record_cli.py）：
- signal 消费 get_signals(engine_id, portfolio_id, page_size) → 新出口 get_signals_df
- order 消费 get_orders(portfolio_id, page_size) → 新出口 get_orders_df
- position 消费 get_all_positions(portfolio_id, page_size) → 新出口 get_positions_df

设计：Mock crud_repo.find 返真实 ModelList（带 mock crud 支持 to_dataframe），
断言 data 运行时类型契约（isinstance），参照 test_engine_portfolio_multiexit.py 桩写法。
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
from ginkgo.data.services.signal_service import SignalService
from ginkgo.data.services.order_service import OrderService
from ginkgo.data.services.position_service import PositionService


# ===== 桩工厂 =====


def _make_empty_modellist() -> ModelList:
    crud_stub = MagicMock()
    crud_stub._convert_models_to_dataframe.return_value = pd.DataFrame()
    return ModelList([], crud_stub)


def _make_signal_modellist() -> ModelList:
    from ginkgo.data.models import MSignal

    model = MSignal()
    crud_stub = MagicMock()
    crud_stub._convert_models_to_dataframe.return_value = pd.DataFrame(
        [{"code": "000001.SZ", "direction": 1}]
    )
    return ModelList([model], crud_stub)


def _make_order_modellist() -> ModelList:
    from ginkgo.data.models import MOrder

    model = MOrder()
    crud_stub = MagicMock()
    crud_stub._convert_models_to_dataframe.return_value = pd.DataFrame(
        [{"code": "000001.SZ", "status": 3}]
    )
    return ModelList([model], crud_stub)


def _make_position_modellist() -> ModelList:
    from ginkgo.data.models import MPosition

    model = MPosition()
    crud_stub = MagicMock()
    crud_stub._convert_models_to_dataframe.return_value = pd.DataFrame(
        [{"code": "000001.SZ", "volume": 100}]
    )
    return ModelList([model], crud_stub)


def _make_signal_service(find_return) -> SignalService:
    with patch("ginkgo.libs.GLOG"):
        crud_repo = MagicMock()
        crud_repo.find.return_value = find_return
        svc = SignalService(crud_repo=crud_repo)
    return svc


def _make_order_service(find_return) -> OrderService:
    with patch("ginkgo.libs.GLOG"):
        crud_repo = MagicMock()
        crud_repo.find.return_value = find_return
        svc = OrderService(crud_repo=crud_repo)
    return svc


def _make_position_service(find_return) -> PositionService:
    with patch("ginkgo.libs.GLOG"):
        crud_repo = MagicMock()
        crud_repo.find.return_value = find_return
        svc = PositionService(crud_repo=crud_repo)
    return svc


# ===== SignalService get_signals_df =====


@pytest.mark.unit
def test_get_signals_df_method_exists():
    assert hasattr(SignalService, "get_signals_df")
    sig = inspect.signature(SignalService.get_signals_df)
    # filter 域对齐 get_signals()：engine_id / portfolio_id / page_size
    assert "engine_id" in sig.parameters
    assert "portfolio_id" in sig.parameters
    assert "page_size" in sig.parameters


@pytest.mark.unit
def test_get_signals_df_returns_dataframe():
    """出口①：data 是 pd.DataFrame，非 ModelList。"""
    svc = _make_signal_service(_make_signal_modellist())
    result = svc.get_signals_df(engine_id="eng1", portfolio_id="pf1")
    assert result.success is True
    assert isinstance(result.data, pd.DataFrame)
    assert not isinstance(result.data, ModelList)
    assert len(result.data) == 1


@pytest.mark.unit
def test_get_signals_df_empty_returns_empty_dataframe():
    """空结果 data 仍是 pd.DataFrame（非 None / 非 ModelList）。"""
    svc = _make_signal_service(_make_empty_modellist())
    result = svc.get_signals_df()
    assert result.success is True
    assert isinstance(result.data, pd.DataFrame)
    assert len(result.data) == 0
    assert not isinstance(result.data, ModelList)


@pytest.mark.unit
def test_get_signals_df_db_failure():
    """crud_repo.find 抛异常时 success is False。"""
    svc = _make_signal_service(_make_empty_modellist())
    svc._crud_repo.find.side_effect = Exception("DB down")
    result = svc.get_signals_df()
    assert result.success is False


# ===== OrderService get_orders_df =====


@pytest.mark.unit
def test_get_orders_df_method_exists():
    assert hasattr(OrderService, "get_orders_df")
    sig = inspect.signature(OrderService.get_orders_df)
    # filter 域对齐 get_orders()：portfolio_id / page_size
    assert "portfolio_id" in sig.parameters
    assert "page_size" in sig.parameters


@pytest.mark.unit
def test_get_orders_df_returns_dataframe():
    """出口①：data 是 pd.DataFrame，非 ModelList。"""
    svc = _make_order_service(_make_order_modellist())
    result = svc.get_orders_df(portfolio_id="pf1")
    assert result.success is True
    assert isinstance(result.data, pd.DataFrame)
    assert not isinstance(result.data, ModelList)
    assert len(result.data) == 1


@pytest.mark.unit
def test_get_orders_df_empty_returns_empty_dataframe():
    """空结果 data 仍是 pd.DataFrame。"""
    svc = _make_order_service(_make_empty_modellist())
    result = svc.get_orders_df()
    assert result.success is True
    assert isinstance(result.data, pd.DataFrame)
    assert len(result.data) == 0
    assert not isinstance(result.data, ModelList)


@pytest.mark.unit
def test_get_orders_df_db_failure():
    """crud_repo.find 抛异常时 success is False。"""
    svc = _make_order_service(_make_empty_modellist())
    svc._crud_repo.find.side_effect = Exception("DB down")
    result = svc.get_orders_df()
    assert result.success is False


# ===== PositionService get_positions_df =====


@pytest.mark.unit
def test_get_positions_df_method_exists():
    assert hasattr(PositionService, "get_positions_df")
    sig = inspect.signature(PositionService.get_positions_df)
    # filter 域对齐 get_all_positions()：portfolio_id / page_size
    assert "portfolio_id" in sig.parameters
    assert "page_size" in sig.parameters


@pytest.mark.unit
def test_get_positions_df_returns_dataframe():
    """出口①：data 是 pd.DataFrame，非 ModelList。"""
    svc = _make_position_service(_make_position_modellist())
    result = svc.get_positions_df(portfolio_id="pf1")
    assert result.success is True
    assert isinstance(result.data, pd.DataFrame)
    assert not isinstance(result.data, ModelList)
    assert len(result.data) == 1


@pytest.mark.unit
def test_get_positions_df_empty_returns_empty_dataframe():
    """空结果 data 仍是 pd.DataFrame。"""
    svc = _make_position_service(_make_empty_modellist())
    result = svc.get_positions_df()
    assert result.success is True
    assert isinstance(result.data, pd.DataFrame)
    assert len(result.data) == 0
    assert not isinstance(result.data, ModelList)


@pytest.mark.unit
def test_get_positions_df_db_failure():
    """crud_repo.find 抛异常时 success is False。"""
    svc = _make_position_service(_make_empty_modellist())
    svc._crud_repo.find.side_effect = Exception("DB down")
    result = svc.get_positions_df()
    assert result.success is False


# ===== filter 构造正确性（_build_*_filters 字段映射 + is_del 固定注入） =====


@pytest.mark.unit
def test_build_signal_filters_construction():
    """_build_signal_filters 字段映射：engine_id / portfolio_id / is_del=False。"""
    svc = _make_signal_service(_make_empty_modellist())
    filters = svc._build_signal_filters(
        engine_id="eng1", portfolio_id="pf1",
    )
    assert filters["engine_id"] == "eng1"
    assert filters["portfolio_id"] == "pf1"
    assert filters["is_del"] is False


@pytest.mark.unit
def test_build_signal_filters_optional_omitted():
    """engine_id/portfolio_id 为空时不注入对应键，is_del 恒定 False。"""
    svc = _make_signal_service(_make_empty_modellist())
    filters = svc._build_signal_filters(engine_id=None, portfolio_id=None)
    assert "engine_id" not in filters
    assert "portfolio_id" not in filters
    assert filters["is_del"] is False


@pytest.mark.unit
def test_build_order_filters_construction():
    """_build_order_filters 字段映射：portfolio_id / is_del=False。"""
    svc = _make_order_service(_make_empty_modellist())
    filters = svc._build_order_filters(portfolio_id="pf1")
    assert filters["portfolio_id"] == "pf1"
    assert filters["is_del"] is False


@pytest.mark.unit
def test_build_order_filters_optional_omitted():
    """portfolio_id 为空时不注入，is_del 恒定 False。"""
    svc = _make_order_service(_make_empty_modellist())
    filters = svc._build_order_filters(portfolio_id=None)
    assert "portfolio_id" not in filters
    assert filters["is_del"] is False


@pytest.mark.unit
def test_build_position_filters_construction():
    """_build_position_filters 字段映射：portfolio_id / is_del=False。"""
    svc = _make_position_service(_make_empty_modellist())
    filters = svc._build_position_filters(portfolio_id="pf1")
    assert filters["portfolio_id"] == "pf1"
    assert filters["is_del"] is False


@pytest.mark.unit
def test_build_position_filters_optional_omitted():
    """portfolio_id 为空时不注入，is_del 恒定 False。"""
    svc = _make_position_service(_make_empty_modellist())
    filters = svc._build_position_filters(portfolio_id=None)
    assert "portfolio_id" not in filters
    assert filters["is_del"] is False
