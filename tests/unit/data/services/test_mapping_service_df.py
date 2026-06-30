"""#6136: MappingService _df 出口契约测试（ADR-010 多出口范式）。

补 get_engine_portfolio_mappings_df / get_portfolio_file_mappings_df：data 是
pandas.DataFrame（类型即契约），消除 cli_utils 调用方对
不存在方法的死调用 + result.data.to_dataframe() 反模式。

消费点：
- cli_utils._add_portfolio_components → get_portfolio_file_mappings_df
- cli_utils._show_engine_tree          → get_engine_portfolio_mappings_df
"""

import sys
import os

import pandas as pd
from unittest.mock import MagicMock, patch

_path = os.path.join(os.path.dirname(__file__), "..", "..", "..")
if _path not in sys.path:
    sys.path.insert(0, _path)

from ginkgo.data.crud.model_conversion import ModelList
from ginkgo.data.services.mapping_service import MappingService


# ===== 桩工厂（参照 test_signal_order_position_multiexit）=====


def _make_engine_portfolio_modellist() -> ModelList:
    from ginkgo.data.models import MEnginePortfolioMapping

    model = MEnginePortfolioMapping()
    crud_stub = MagicMock()
    crud_stub._convert_models_to_dataframe.return_value = pd.DataFrame(
        [{"engine_id": "eng-1", "portfolio_id": "pf-1",
          "engine_name": "E1", "portfolio_name": "P1"}]
    )
    return ModelList([model], crud_stub)


def _make_portfolio_file_modellist() -> ModelList:
    from ginkgo.data.models import MPortfolioFileMapping

    model = MPortfolioFileMapping()
    crud_stub = MagicMock()
    crud_stub._convert_models_to_dataframe.return_value = pd.DataFrame(
        [{"portfolio_id": "pf-1", "file_id": "f-1", "name": "strat", "type": 6}]
    )
    return ModelList([model], crud_stub)


def _make_mapping_service(ep_find=None, pf_find=None) -> MappingService:
    with patch("ginkgo.libs.GLOG"):
        ep = MagicMock()
        ep.find.return_value = ep_find
        pf = MagicMock()
        pf.find.return_value = pf_find
        svc = MappingService(ep, pf, MagicMock(), MagicMock())
    return svc


# ===== Slice 1: get_engine_portfolio_mappings_df =====


def test_get_engine_portfolio_mappings_df_returns_dataframe_filtered_by_engine():
    """#6136 tracer：_df 出口 data 是 DataFrame（类型即契约），engine 过滤透传 CRUD。"""
    svc = _make_mapping_service(ep_find=_make_engine_portfolio_modellist())
    result = svc.get_engine_portfolio_mappings_df(engine_uuid="eng-1")

    assert result.success
    assert isinstance(result.data, pd.DataFrame)
    assert "engine_id" in result.data.columns
    assert len(result.data) == 1
    svc._engine_portfolio_mapping_crud.find.assert_called_once_with(
        filters={"engine_id": "eng-1"}
    )


# ===== Slice 2: get_portfolio_file_mappings_df =====


def test_get_portfolio_file_mappings_df_returns_dataframe_filtered_by_portfolio():
    """#6136：portfolio-file 映射 _df 出口，portfolio 过滤透传 CRUD。"""
    svc = _make_mapping_service(pf_find=_make_portfolio_file_modellist())
    result = svc.get_portfolio_file_mappings_df(portfolio_uuid="pf-1")

    assert result.success
    assert isinstance(result.data, pd.DataFrame)
    assert "portfolio_id" in result.data.columns
    assert len(result.data) == 1
    svc._portfolio_file_mapping_crud.find.assert_called_once_with(
        filters={"portfolio_id": "pf-1"}
    )


def test_get_engine_portfolio_mappings_df_empty_when_find_returns_none():
    """#6136：find 返 None 时出口给空 DataFrame（不崩）。"""
    svc = _make_mapping_service(ep_find=None)
    result = svc.get_engine_portfolio_mappings_df(engine_uuid="eng-x")

    assert result.success
    assert isinstance(result.data, pd.DataFrame)
    assert len(result.data) == 0

