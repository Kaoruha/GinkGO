# tests/unit/services/test_portfolio_service_performance.py
"""
Unit tests for PortfolioService.update_performance() and MPortfolio.annual_return.

Covers:
- Full and partial performance field updates via the service layer
- Empty / no-op update
- Error on nonexistent portfolio
- MPortfolio.update(str) dispatch correctly sets annual_return
"""
import pytest
from unittest.mock import MagicMock, call

from ginkgo.data.models.model_portfolio import MPortfolio
from ginkgo.data.services.portfolio_service import PortfolioService
from ginkgo.data.services.base_service import ServiceResult


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def mock_service():
    """PortfolioService with mocked dependencies (same pattern as lifecycle tests)."""
    service = PortfolioService.__new__(PortfolioService)
    service._crud_repo = MagicMock()
    service._portfolio_file_mapping_crud = MagicMock()
    service._deployment_crud = MagicMock()
    service._param_crud = MagicMock()
    return service


# ===========================================================================
# update_performance service tests
# ===========================================================================


class TestUpdatePerformanceSetsFields:
    """All performance fields should be forwarded to _crud_repo.modify."""

    def test_all_fields(self, mock_service):
        result = mock_service.update_performance(
            portfolio_id="p-001",
            annual_return=0.145,
            sharpe_ratio=1.23,
            max_drawdown=0.08,
            win_rate=0.62,
            total_trades=100,
            winning_trades=62,
        )

        assert result.is_success()
        mock_service._crud_repo.modify.assert_called_once_with(
            filters={"uuid": "p-001"},
            updates={
                "annual_return": 0.145,
                "sharpe_ratio": 1.23,
                "max_drawdown": 0.08,
                "win_rate": 0.62,
                "total_trades": 100,
                "winning_trades": 62,
            },
        )

    def test_result_data_contains_updated_fields(self, mock_service):
        result = mock_service.update_performance(
            portfolio_id="p-002",
            annual_return=0.10,
        )

        assert result.is_success()
        assert "annual_return" in result.data["updated_fields"]
        assert result.data["portfolio_id"] == "p-002"


class TestUpdatePerformancePartialUpdate:
    """Only supplied fields should appear in the updates dict."""

    def test_sharpe_ratio_and_win_rate_only(self, mock_service):
        result = mock_service.update_performance(
            portfolio_id="p-003",
            sharpe_ratio=2.5,
            win_rate=0.55,
        )

        assert result.is_success()
        mock_service._crud_repo.modify.assert_called_once_with(
            filters={"uuid": "p-003"},
            updates={"sharpe_ratio": 2.5, "win_rate": 0.55},
        )

    def test_single_field(self, mock_service):
        result = mock_service.update_performance(
            portfolio_id="p-004",
            total_trades=42,
        )

        assert result.is_success()
        mock_service._crud_repo.modify.assert_called_once_with(
            filters={"uuid": "p-004"},
            updates={"total_trades": 42},
        )


class TestUpdatePerformanceEmptyUpdate:
    """Calling with no optional args should succeed without calling modify."""

    def test_no_fields(self, mock_service):
        result = mock_service.update_performance(portfolio_id="p-005")

        assert result.is_success()
        mock_service._crud_repo.modify.assert_not_called()


class TestUpdatePerformanceNonexistentPortfolio:
    """modify() raising should produce an error ServiceResult."""

    def test_modify_raises(self, mock_service):
        mock_service._crud_repo.modify.side_effect = Exception("row not found")

        result = mock_service.update_performance(
            portfolio_id="nonexistent-uuid",
            annual_return=0.05,
        )

        assert result.is_success() is False
        assert "Failed to update performance" in result.error

    def test_empty_portfolio_id(self, mock_service):
        result = mock_service.update_performance(portfolio_id="")

        assert result.is_success() is False
        mock_service._crud_repo.modify.assert_not_called()

    def test_whitespace_portfolio_id(self, mock_service):
        result = mock_service.update_performance(portfolio_id="   ")

        assert result.is_success() is False
        mock_service._crud_repo.modify.assert_not_called()


# ===========================================================================
# MPortfolio.annual_return model tests
# ===========================================================================


class TestMPortfolioAnnualReturnInModelUpdate:
    """MPortfolio.update(str) should correctly set annual_return."""

    def test_annual_return_set_via_str_dispatch(self):
        model = MPortfolio()
        model.update(
            "test_portfolio",
            annual_return=0.1543,
        )

        assert float(model.annual_return) == pytest.approx(0.1543)

    def test_annual_return_default_is_none_before_persist(self):
        model = MPortfolio()
        # SQLAlchemy column default only applies on DB INSERT; in-memory is None
        assert model.annual_return is None

    def test_annual_return_not_set_when_none(self):
        model = MPortfolio()
        model.update("test_portfolio", annual_return=0.20)

        # Update again without annual_return -- value should stay unchanged
        model.update("test_portfolio")
        assert float(model.annual_return) == pytest.approx(0.20)

    def test_annual_return_alongside_other_performance_fields(self):
        model = MPortfolio()
        model.update(
            "test_portfolio",
            annual_return=0.12,
            sharpe_ratio=1.5,
            max_drawdown=0.08,
            win_rate=0.60,
            total_trades=50,
            winning_trades=30,
        )

        assert float(model.annual_return) == pytest.approx(0.12)
        assert float(model.sharpe_ratio) == pytest.approx(1.5)
        assert float(model.max_drawdown) == pytest.approx(0.08)
        assert float(model.win_rate) == pytest.approx(0.60)
        assert model.total_trades == 50
        assert model.winning_trades == 30
