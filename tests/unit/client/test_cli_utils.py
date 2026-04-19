"""
性能: 221MB RSS, 1.86s, 7 tests [PASS]
Unit tests for cli_utils.py helper functions.

cli_utils provides utility functions for tree display and parameter retrieval:
  - _get_component_parameters: Fetch params from database via param_crud
  - _add_portfolio_components: Build tree nodes for portfolio's components
  - _show_portfolio_tree: Display portfolio as rich tree
  - _show_engine_tree: Display engine as rich tree (with nested portfolios)

Mock strategy:
  - Patch "ginkgo.data.containers.container" for service access
  - Functions are tested directly (not via CLI runner)
"""

import os

os.environ["GINKGO_SKIP_DEBUG_CHECK"] = "1"

import uuid
from unittest.mock import MagicMock, patch

import pandas as pd
import pytest

from ginkgo.client import cli_utils
from ginkgo.enums import FILE_TYPES


def _make_mock_model_list(df: pd.DataFrame) -> MagicMock:
    """创建模拟 ModelList 的 mock，支持 .to_dataframe() 返回 DataFrame。"""
    mock_ml = MagicMock()
    mock_ml.to_dataframe.return_value = df
    return mock_ml


# ============================================================================
# 1. _get_component_parameters
# ============================================================================


# NOTE: Testing private methods directly - consider refactoring to test through public CLI interface

@pytest.mark.unit
@pytest.mark.cli
class TestGetComponentParameters:
    """Tests for _get_component_parameters helper."""

    def test_returns_empty_dict_when_no_params(self):
        crud = MagicMock()
        crud.find.return_value = pd.DataFrame(columns=["value"])
        with patch("ginkgo.data.containers.container") as mock_container:
            mock_container.cruds.param.return_value = crud
            result = cli_utils._get_component_parameters("mapping-1", "file-1", FILE_TYPES.STRATEGY)
        assert result == {}

    def test_returns_params_dict(self):
        crud = MagicMock()
        crud.find.return_value = pd.DataFrame({"value": [100, 0.5]})
        with patch("ginkgo.data.containers.container") as mock_container:
            mock_container.cruds.param.return_value = crud
            result = cli_utils._get_component_parameters("mapping-1", "file-1", FILE_TYPES.STRATEGY)
        assert result == {"param_0": 100, "param_1": 0.5}

    def test_returns_empty_on_exception(self):
        crud = MagicMock()
        crud.find.side_effect = Exception("DB error")
        with patch("ginkgo.data.containers.container") as mock_container:
            mock_container.cruds.param.return_value = crud
            result = cli_utils._get_component_parameters("mapping-1", "file-1", FILE_TYPES.STRATEGY)
        assert result == {}


# ============================================================================
# 2. _add_portfolio_components
# ============================================================================


# NOTE: Testing private methods directly - consider refactoring to test through public CLI interface

@pytest.mark.unit
@pytest.mark.cli
class TestAddPortfolioComponents:
    """Tests for _add_portfolio_components tree builder."""

    def test_no_components_shows_message(self):
        mock_service = MagicMock()
        mock_service.get_portfolio_file_mappings.return_value = _make_mock_model_list(
            pd.DataFrame(columns=["portfolio_id", "type", "name", "file_id", "uuid"])
        )
        parent = MagicMock()
        with patch("ginkgo.data.containers.container") as mock_container:
            mock_container.portfolio_service.return_value = mock_service
            cli_utils._add_portfolio_components(parent, "portfolio-1", False, None)
        parent.add.assert_called_once()
        assert "No components bound" in parent.add.call_args[0][0]

    def test_components_added_to_tree(self):
        mock_service = MagicMock()
        mock_service.get_portfolio_file_mappings.return_value = _make_mock_model_list(pd.DataFrame([
            {"portfolio_id": "portfolio-1", "type": FILE_TYPES.STRATEGY.value,
             "name": "MyStrategy", "file_id": "file-1", "uuid": "mapping-1"}
        ]))
        parent = MagicMock()
        with patch("ginkgo.data.containers.container") as mock_container:
            mock_container.portfolio_service.return_value = mock_service
            cli_utils._add_portfolio_components(parent, "portfolio-1", False, None)
        # Should have added a section node via parent.add
        assert parent.add.call_count >= 1


# ============================================================================
# 3. _show_portfolio_tree / _show_engine_tree
# ============================================================================


# NOTE: Testing private methods directly - consider refactoring to test through public CLI interface

@pytest.mark.unit
@pytest.mark.cli
class TestShowTree:
    """Tests for tree display functions."""

    def test_show_portfolio_tree(self):
        portfolio_row = {"name": "TestPortfolio", "uuid": "p-1"}
        mock_service = MagicMock()
        mock_service.get_portfolio_file_mappings.return_value = _make_mock_model_list(
            pd.DataFrame(columns=["portfolio_id", "type", "name", "file_id", "uuid"])
        )
        with patch("ginkgo.data.containers.container") as mock_container, \
             patch.object(cli_utils.console, "print") as mock_print:
            mock_container.portfolio_service.return_value = mock_service
            cli_utils._show_portfolio_tree(portfolio_row, False, None)
        mock_print.assert_called_once()

    def test_show_engine_tree_no_portfolios(self):
        engine_row = {"name": "TestEngine", "uuid": "e-1"}
        mock_engine_service = MagicMock()
        mock_engine_service.get_engine_portfolio_mappings.return_value = _make_mock_model_list(
            pd.DataFrame(columns=["engine_id", "portfolio_id"])
        )
        with patch("ginkgo.data.containers.container") as mock_container, \
             patch.object(cli_utils.console, "print") as mock_print:
            mock_container.engine_service.return_value = mock_engine_service
            cli_utils._show_engine_tree(engine_row, False, None)
        mock_print.assert_called_once()
