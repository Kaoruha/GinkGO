"""Smoke test for PortfolioManagementService -- #3823"""
import pytest
from unittest.mock import MagicMock, patch

# Import with fallback
try:
    from ginkgo.trading.services.portfolio_management_service import PortfolioManagementService
    HAS_MODULE = True
except ImportError:
    HAS_MODULE = False


@pytest.mark.skipif(not HAS_MODULE, reason="ginkgo.trading.services.portfolio_management_service not importable")
class TestPortfolioManagementServiceSmoke:
    """冒烟测试：验证可实例化和公开方法可调用"""

    def test_instantiation_no_args(self):
        """Service 可无参实例化"""
        with patch("ginkgo.trading.services.portfolio_management_service.GLOG"):
            svc = PortfolioManagementService()
        assert svc is not None

    def test_instantiation_with_deps(self):
        """Service 可注入依赖实例化"""
        with patch("ginkgo.trading.services.portfolio_management_service.GLOG"):
            svc = PortfolioManagementService(
                component_factory=MagicMock(),
                position_service=MagicMock(),
                portfolio_service=MagicMock(),
            )
        assert svc is not None

    def test_initialize_callable(self):
        """initialize() 可调用"""
        with patch("ginkgo.trading.services.portfolio_management_service.GLOG"):
            svc = PortfolioManagementService()
            result = svc.initialize()
            assert isinstance(result, bool)
            assert result is True

    def test_create_portfolio_instance_callable(self):
        """create_portfolio_instance() 可调用"""
        with patch("ginkgo.trading.services.portfolio_management_service.GLOG"):
            mock_portfolio_svc = MagicMock()
            mock_portfolio_svc.get_portfolio.return_value = MagicMock(shape=[0])  # empty
            svc = PortfolioManagementService(portfolio_service=mock_portfolio_svc)
            result = svc.create_portfolio_instance("nonexistent-id")
            # Should return None for nonexistent portfolio
            assert result is None

    def test_bind_components_to_portfolio_callable(self):
        """bind_components_to_portfolio() 可调用"""
        with patch("ginkgo.trading.services.portfolio_management_service.GLOG"):
            svc = PortfolioManagementService()
            # No component factory -> should return False
            mock_portfolio = MagicMock()
            result = svc.bind_components_to_portfolio(mock_portfolio, "portfolio-id")
            assert isinstance(result, bool)
            assert result is False

    def test_get_active_portfolios_callable(self):
        """get_active_portfolios() 可调用"""
        with patch("ginkgo.trading.services.portfolio_management_service.GLOG"):
            svc = PortfolioManagementService()
            result = svc.get_active_portfolios()
            assert isinstance(result, dict)
