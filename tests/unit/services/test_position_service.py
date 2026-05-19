"""
Unit tests for PositionService.

Verifies that PositionService orchestrates position persistence
through PositionCRUD, providing the `save_positions` interface
that PortfolioLive depends on.
"""
import pytest
from unittest.mock import MagicMock, call

from ginkgo.data.services.position_service import PositionService
from ginkgo.data.services.base_service import ServiceResult


@pytest.fixture
def mock_crud():
    return MagicMock()


@pytest.fixture
def service(mock_crud):
    return PositionService(crud_repo=mock_crud)


@pytest.fixture
def mock_position():
    """A duck-typed position object matching what PortfolioLive passes."""
    pos = MagicMock()
    pos.portfolio_id = "p-001"
    pos.engine_id = "e-001"
    pos.task_id = "t-001"
    pos.code = "000001.SZ"
    pos.direction = "LONG"
    pos.volume = 100
    pos.frozen = 0
    pos.cost = 10.5
    pos.price = 11.0
    pos.fee = 0.5
    pos.timestamp = None
    return pos


class TestSavePositions:
    """save_positions is the primary interface used by PortfolioLive."""

    def test_empty_list(self, service, mock_crud):
        result = service.save_positions([])
        assert result.is_success()
        # Should delete existing then create none
        mock_crud.delete_by_portfolio.assert_not_called()

    def test_saves_positions_via_add(self, service, mock_crud, mock_position):
        result = service.save_positions([mock_position])

        assert result.is_success()
        # 应使用 add 而非 create（model 实例应走 add 路径）
        mock_crud.add.assert_called_once_with(mock_position)
        mock_crud.create.assert_not_called()

    def test_multiple_positions(self, service, mock_crud, mock_position):
        pos2 = MagicMock()
        pos2.portfolio_id = "p-001"
        pos2.engine_id = "e-001"
        pos2.task_id = "t-001"
        pos2.code = "600000.SH"
        pos2.direction = "LONG"
        pos2.volume = 200
        pos2.frozen = 0
        pos2.cost = 20.0
        pos2.price = 21.0
        pos2.fee = 1.0
        pos2.timestamp = None

        result = service.save_positions([mock_position, pos2])
        assert result.is_success()
        assert mock_crud.add.call_count == 2

    def test_crud_failure_returns_error(self, service, mock_crud, mock_position):
        mock_crud.add.side_effect = Exception("DB write failed")

        result = service.save_positions([mock_position])
        assert result.is_success() is False
        assert "DB write failed" in result.error


class TestGetPositions:
    """Query positions by portfolio."""

    def test_find_by_portfolio(self, service, mock_crud):
        mock_crud.find_by_portfolio.return_value = []

        result = service.get_positions("p-001")
        assert result.is_success()
        mock_crud.find_by_portfolio.assert_called_once_with("p-001")

    def test_get_portfolio_value(self, service, mock_crud):
        mock_crud.get_portfolio_value.return_value = {
            "total_market_value": 10000,
            "total_cost": 9000,
        }

        result = service.get_portfolio_value("p-001")
        assert result.is_success()
        assert result.data["total_market_value"] == 10000
