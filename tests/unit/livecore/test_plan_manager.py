"""Tests for PlanManager -- #4661"""
import pytest
from unittest.mock import MagicMock, patch

from ginkgo.data.services.base_service import ServiceResult


@pytest.fixture()
def mock_services():
    """Create a mock services module."""
    svc = MagicMock()
    with patch("ginkgo.services", svc):
        yield svc


@pytest.mark.tdd
class TestGetAllPortfolios:
    """#4661: _get_all_portfolios must query PAPER + LIVE modes explicitly.

    The old code called portfolio_service.get(is_live=True), but `is_live`
    is a @property on MPortfolio (mode >= PAPER), not a queryable DB field.
    It falls into **kwargs and is silently dropped by kwargs.get('filters', {}),
    returning ALL portfolios including BACKTEST ones.

    Fix: query PAPER mode and LIVE mode separately, then merge.
    """

    def test_queries_paper_and_live_modes(self, mock_services):
        """Must call portfolio_service.get() once for PAPER and once for LIVE."""
        from ginkgo.livecore.scheduler.plan_manager import PlanManager

        paper_portfolio = MagicMock()
        paper_portfolio.mode = 1  # PAPER

        live_portfolio = MagicMock()
        live_portfolio.mode = 2  # LIVE

        mock_pf_svc = MagicMock()
        mock_pf_svc.get.side_effect = [
            ServiceResult.success([paper_portfolio]),
            ServiceResult.success([live_portfolio]),
        ]
        mock_services.data.portfolio_service.return_value = mock_pf_svc

        result = PlanManager._get_all_portfolios()

        # Must have called get() twice — once for PAPER, once for LIVE
        assert mock_pf_svc.get.call_count == 2
        calls = mock_pf_svc.get.call_args_list

        from ginkgo.enums import PORTFOLIO_MODE_TYPES
        modes_called = []
        for call in calls:
            mode_arg = call.kwargs.get("mode")
            if mode_arg is not None:
                modes_called.append(mode_arg)

        # Both PAPER and LIVE modes must be queried
        assert PORTFOLIO_MODE_TYPES.PAPER in modes_called, \
            f"PAPER mode not queried. Modes called: {modes_called}"
        assert PORTFOLIO_MODE_TYPES.LIVE in modes_called, \
            f"LIVE mode not queried. Modes called: {modes_called}"

        # Result must contain both portfolios
        assert len(result) == 2

    def test_does_not_query_backtest_mode(self, mock_services):
        """Must NOT return BACKTEST portfolios."""
        from ginkgo.livecore.scheduler.plan_manager import PlanManager

        mock_pf_svc = MagicMock()
        mock_pf_svc.get.side_effect = [
            ServiceResult.success([]),  # PAPER: none
            ServiceResult.success([]),  # LIVE: none
        ]
        mock_services.data.portfolio_service.return_value = mock_pf_svc

        result = PlanManager._get_all_portfolios()

        assert result == []
        # Should not call with is_live=True (which is silently dropped)
        for call in mock_pf_svc.get.call_args_list:
            assert "is_live" not in call.kwargs, \
                "is_live should not be used — it's a @property, not a DB field"

    def test_returns_empty_on_service_error(self, mock_services):
        """Must return empty list when service fails."""
        from ginkgo.livecore.scheduler.plan_manager import PlanManager

        mock_pf_svc = MagicMock()
        mock_pf_svc.get.return_value = ServiceResult.error("DB error")
        mock_services.data.portfolio_service.return_value = mock_pf_svc

        result = PlanManager._get_all_portfolios()

        assert result == []
