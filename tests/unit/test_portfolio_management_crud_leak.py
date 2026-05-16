"""
Tests for PortfolioManagementService CRUD leak elimination (#3633).

Verifies that PortfolioManagementService uses PositionService/PortfolioService
instead of directly accessing container.cruds or container.services.

Issue: #3633
"""

import pytest
from unittest.mock import MagicMock, patch

from ginkgo.data.services.base_service import ServiceResult
from ginkgo.trading.services.portfolio_management_service import PortfolioManagementService


def _make_position(portfolio_id="p-1", engine_id="e-1", code="000001.SZ",
                   cost=100.0, volume=10, price=10.0, fee=0.0):
    """Create a mock Position with standard attributes."""
    pos = MagicMock()
    pos.portfolio_id = portfolio_id
    pos.engine_id = engine_id
    pos.code = code
    pos.cost = cost
    pos.volume = volume
    pos.price = price
    pos.fee = fee
    pos.frozen_volume = 0
    pos.frozen_money = 0.0
    pos.uuid = "pos-uuid-1"
    return pos


def _make_service(position_service=None, portfolio_service=None):
    """Create PortfolioManagementService with mocked dependencies."""
    return PortfolioManagementService(
        component_factory=MagicMock(),
        position_service=position_service or MagicMock(),
        portfolio_service=portfolio_service or MagicMock(),
    )


class TestUpsertPositionCreatesNew:
    """upsert_position should create a new position when none exists."""

    def test_creates_when_no_existing(self):
        position_service = MagicMock()
        position_service.upsert_position.return_value = ServiceResult.success(
            data={"created": True}, message="Position created"
        )
        service = _make_service(position_service=position_service)
        position = _make_position()

        result = service._save_position(position)

        assert result.success
        position_service.upsert_position.assert_called_once_with(position)


class TestUpsertPositionUpdatesExisting:
    """upsert_position should update an existing position."""

    def test_updates_when_existing(self):
        position_service = MagicMock()
        position_service.upsert_position.return_value = ServiceResult.success(
            data={"updated": True}, message="Position updated"
        )
        service = _make_service(position_service=position_service)
        position = _make_position()

        result = service._save_position(position)

        assert result.success
        position_service.upsert_position.assert_called_once_with(position)


class TestNoContainerImport:
    """PortfolioManagementService must not import container at runtime."""

    def test_no_container_import_in_module(self):
        import inspect
        from ginkgo.trading.services.portfolio_management_service import PortfolioManagementService

        source = inspect.getsource(PortfolioManagementService)
        assert "container.cruds" not in source
        assert "container.portfolio_service" not in source
        assert "from ginkgo.data.containers import container" not in source

    def test_constructor_accepts_position_service(self):
        """Constructor should accept position_service via parameter, not container."""
        mock_ps = MagicMock()
        service = PortfolioManagementService(
            component_factory=MagicMock(),
            position_service=mock_ps,
            portfolio_service=MagicMock(),
        )
        assert service._position_service is mock_ps
