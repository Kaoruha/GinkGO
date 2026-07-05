"""
SignalService unit tests (#5949).

覆盖 get_signals_df 的 task_id 过滤透传：signal 已有 engine_id/portfolio_id，
补齐 task_id 后与 order/position 三维对称。

Run: pytest tests/unit/data/services/test_signal_service.py -v -o "addopts="
"""

from unittest.mock import MagicMock

import pandas as pd
import pytest

from ginkgo.data.services.signal_service import SignalService


@pytest.fixture
def mock_crud():
    return MagicMock()


@pytest.fixture
def signal_svc(mock_crud):
    return SignalService(crud_repo=mock_crud)


@pytest.mark.unit
class TestGetSignalsDfFilters:
    """get_signals_df 的三维过滤透传（#5949）"""

    def test_filters_by_engine_portfolio_task(self, signal_svc, mock_crud):
        """engine_id + portfolio_id + task_id 透传到 crud.find 的 filters"""
        model_list = MagicMock()
        model_list.to_dataframe.return_value = pd.DataFrame()
        mock_crud.find.return_value = model_list

        signal_svc.get_signals_df(engine_id="e1", portfolio_id="p1", task_id="t1")

        _, kwargs = mock_crud.find.call_args
        filters = kwargs["filters"]
        assert filters == {
            "is_del": False,
            "engine_id": "e1",
            "portfolio_id": "p1",
            "task_id": "t1",
        }

    def test_task_id_optional(self, signal_svc, mock_crud):
        """未传 task_id 时不应进入 filters（避免误加 None）"""
        model_list = MagicMock()
        model_list.to_dataframe.return_value = pd.DataFrame()
        mock_crud.find.return_value = model_list

        signal_svc.get_signals_df(engine_id="e1")

        _, kwargs = mock_crud.find.call_args
        assert "task_id" not in kwargs["filters"]

    def test_passes_page_and_page_size(self, signal_svc, mock_crud):
        model_list = MagicMock()
        model_list.to_dataframe.return_value = pd.DataFrame()
        mock_crud.find.return_value = model_list

        signal_svc.get_signals_df(page=2, page_size=30)

        _, kwargs = mock_crud.find.call_args
        assert kwargs["page"] == 2
        assert kwargs["page_size"] == 30
        assert kwargs["order_by"] == "create_at"
        assert kwargs["desc_order"] is True


@pytest.mark.unit
class TestGetSignalsByPortfolioDateFilter:
    """get_signals_by_portfolio: 日期范围下推到 crud.find_by_portfolio (#6030)"""

    def test_passes_start_end_date_to_crud(self, signal_svc, mock_crud):
        mock_crud.find_by_portfolio.return_value = []
        signal_svc.get_signals_by_portfolio(portfolio_id="p1", start_date="2026-06-23", end_date="2026-06-24")
        _, kwargs = mock_crud.find_by_portfolio.call_args
        assert kwargs["portfolio_id"] == "p1"
        assert kwargs["start_date"] == "2026-06-23"
        assert kwargs["end_date"] == "2026-06-24"

    def test_date_optional(self, signal_svc, mock_crud):
        mock_crud.find_by_portfolio.return_value = []
        signal_svc.get_signals_by_portfolio(portfolio_id="p1")
        _, kwargs = mock_crud.find_by_portfolio.call_args
        assert kwargs["portfolio_id"] == "p1"
        assert kwargs.get("start_date") is None
        assert kwargs.get("end_date") is None

    def test_returns_crud_results_in_success(self, signal_svc, mock_crud):
        mock_crud.find_by_portfolio.return_value = ["sig1", "sig2"]
        result = signal_svc.get_signals_by_portfolio(portfolio_id="p1")
        assert result.is_success()
        assert result.data == ["sig1", "sig2"]
