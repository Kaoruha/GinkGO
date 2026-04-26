import pytest
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

# Add api directory to path for imports
api_path = Path(__file__).parent.parent.parent / "api"
sys.path.insert(0, str(api_path))


def test_update_saga_rejects_frozen_portfolio():
    """update_portfolio_saga 应拒绝冻结组合"""
    from services.saga_transaction import PortfolioSagaFactory

    with patch("ginkgo.data.containers.container") as mock_container:
        mock_service = MagicMock()
        mock_service.is_portfolio_frozen.return_value = True
        mock_container.portfolio_service.return_value = mock_service

        with pytest.raises(Exception, match="已部署"):
            PortfolioSagaFactory.update_portfolio_saga(
                portfolio_uuid="frozen-uuid",
                name="new-name",
            )


def test_delete_saga_rejects_frozen_portfolio():
    """delete_portfolio_saga 应拒绝冻结组合"""
    from services.saga_transaction import PortfolioSagaFactory

    with patch("ginkgo.data.containers.container") as mock_container:
        mock_service = MagicMock()
        mock_service.is_portfolio_frozen.return_value = True
        mock_container.portfolio_service.return_value = mock_service

        with pytest.raises(Exception, match="已部署"):
            PortfolioSagaFactory.delete_portfolio_saga(
                portfolio_uuid="frozen-uuid",
            )
