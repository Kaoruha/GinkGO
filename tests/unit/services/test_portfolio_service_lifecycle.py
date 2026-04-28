# tests/unit/services/test_portfolio_service_lifecycle.py
import pytest
from unittest.mock import MagicMock


@pytest.fixture
def mock_service():
    """创建带 mock 依赖的 PortfolioService"""
    from ginkgo.data.services.portfolio_service import PortfolioService
    service = PortfolioService.__new__(PortfolioService)
    service._crud_repo = MagicMock()
    service._portfolio_file_mapping_crud = MagicMock()
    service._deployment_crud = MagicMock()
    service._param_crud = MagicMock()
    return service


class TestPortfolioServiceStop:
    def test_stop_requires_paper_or_live_mode(self, mock_service):
        """BACKTEST 模式不允许 stop"""
        mock_portfolio = MagicMock()
        mock_portfolio.mode = 0  # BACKTEST
        mock_service._crud_repo.find.return_value = [mock_portfolio]

        result = mock_service.stop("test-uuid")
        assert result.is_success() is False
        assert "回测" in result.error

    def test_stop_rejects_already_stopped(self, mock_service):
        """STOPPED 状态不允许再次 stop"""
        mock_portfolio = MagicMock()
        mock_portfolio.mode = 1  # PAPER
        mock_portfolio.state = 4  # STOPPED
        mock_service._crud_repo.find.return_value = [mock_portfolio]

        result = mock_service.stop("test-uuid")
        assert result.is_success() is False

    def test_stop_rejects_stopping(self, mock_service):
        """STOPPING 状态不允许再次 stop"""
        mock_portfolio = MagicMock()
        mock_portfolio.mode = 1  # PAPER
        mock_portfolio.state = 3  # STOPPING
        mock_service._crud_repo.find.return_value = [mock_portfolio]

        result = mock_service.stop("test-uuid")
        assert result.is_success() is False


class TestPortfolioServiceDeleteProtection:
    def test_delete_rejects_running_paper(self, mock_service):
        """RUNNING 的 PAPER portfolio 不允许删除"""
        from ginkgo.data.services.base_service import ServiceResult
        mock_portfolio = MagicMock()
        mock_portfolio.mode = 1  # PAPER
        mock_portfolio.state = 1  # RUNNING
        mock_service._crud_repo.find.return_value = [mock_portfolio]
        exists_result = ServiceResult.success({"exists": True})
        mock_service.exists = MagicMock(return_value=exists_result)

        result = mock_service.delete(portfolio_id="test-uuid")
        assert result.is_success() is False
        assert "停止" in result.error

    def test_delete_rejects_stopping_paper(self, mock_service):
        """STOPPING 的 PAPER portfolio 不允许删除"""
        from ginkgo.data.services.base_service import ServiceResult
        mock_portfolio = MagicMock()
        mock_portfolio.mode = 1  # PAPER
        mock_portfolio.state = 3  # STOPPING
        mock_service._crud_repo.find.return_value = [mock_portfolio]
        exists_result = ServiceResult.success({"exists": True})
        mock_service.exists = MagicMock(return_value=exists_result)

        result = mock_service.delete(portfolio_id="test-uuid")
        assert result.is_success() is False

    def test_delete_allows_stopped_paper(self, mock_service):
        """STOPPED 的 PAPER portfolio 允许删除"""
        from ginkgo.data.services.base_service import ServiceResult
        mock_portfolio = MagicMock()
        mock_portfolio.mode = 1  # PAPER
        mock_portfolio.state = 4  # STOPPED
        mock_service._crud_repo.find.return_value = [mock_portfolio]
        mock_service._portfolio_file_mapping_crud.find.return_value = []
        exists_result = ServiceResult.success({"exists": True})
        mock_service.exists = MagicMock(return_value=exists_result)

        result = mock_service.delete(portfolio_id="test-uuid")
        assert result.is_success() is True

    def test_delete_allows_backtest_running(self, mock_service):
        """BACKTEST 模式不受状态限制"""
        from ginkgo.data.services.base_service import ServiceResult
        mock_portfolio = MagicMock()
        mock_portfolio.mode = 0  # BACKTEST
        mock_portfolio.state = 1  # RUNNING
        mock_service._crud_repo.find.return_value = [mock_portfolio]
        mock_service._portfolio_file_mapping_crud.find.return_value = []
        exists_result = ServiceResult.success({"exists": True})
        mock_service.exists = MagicMock(return_value=exists_result)

        result = mock_service.delete(portfolio_id="test-uuid")
        assert result.is_success() is True
