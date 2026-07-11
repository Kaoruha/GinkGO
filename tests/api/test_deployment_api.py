import pytest
from unittest.mock import MagicMock, patch


def test_deploy_request_accepts_portfolio_uuid_alias():
    """#5718: deploy request accepts the public portfolio_uuid field name."""
    from api.deployment import DeployRequest

    req = DeployRequest(name="test", portfolio_uuid="portfolio-123", mode="paper")

    assert req.portfolio_id == "portfolio-123"


def test_deploy_request_keeps_portfolio_id_compatibility():
    """Existing callers using portfolio_id remain compatible."""
    from api.deployment import DeployRequest

    req = DeployRequest(name="test", portfolio_id="portfolio-123", mode="paper")

    assert req.portfolio_id == "portfolio-123"


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
