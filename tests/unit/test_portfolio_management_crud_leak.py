"""
Tests for PortfolioManagementService CRUD leak elimination (#3633).

Verifies that PortfolioManagementService uses PositionService/PortfolioService
instead of directly accessing container.cruds or container.services.

Issue: #3633
"""

import pytest
from unittest.mock import MagicMock

from ginkgo.trading.services.portfolio_management_service import PortfolioManagementService


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
