"""
#3867: DeploymentService 新增 find 方法的单元测试

覆盖：
- find_by_source_portfolio: 按源组合查找部署记录
- find_by_target_portfolio: 按目标组合查找部署记录
"""

import sys
import os
import pytest
from unittest.mock import MagicMock

_path = os.path.join(os.path.dirname(__file__), '..', '..', '..')
if _path not in sys.path:
    sys.path.insert(0, _path)

from ginkgo.trading.services.deployment_service import DeploymentService
from ginkgo.data.services.base_service import ServiceResult


class TestFindBySourcePortfolio:
    """DeploymentService.find_by_source_portfolio 测试"""

    @pytest.fixture
    def service(self):
        deployment_crud = MagicMock()
        return DeploymentService(deployment_crud=deployment_crud)

    @pytest.mark.unit
    def test_returns_deployments(self, service):
        """返回源组合的部署记录"""
        dep = MagicMock()
        dep.source_portfolio_id = "pf-src"
        dep.target_portfolio_id = "pf-tgt"
        service._deployment_crud.get_by_source_portfolio.return_value = [dep]

        result = service.find_by_source_portfolio(source_portfolio_id="pf-src")

        assert result.is_success()
        assert len(result.data) == 1
        service._deployment_crud.get_by_source_portfolio.assert_called_once_with("pf-src")

    @pytest.mark.unit
    def test_returns_empty_when_none(self, service):
        """无部署记录返回空列表"""
        service._deployment_crud.get_by_source_portfolio.return_value = []

        result = service.find_by_source_portfolio(source_portfolio_id="pf-src")

        assert result.is_success()
        assert result.data == []

    @pytest.mark.unit
    def test_returns_error_on_exception(self, service):
        """CRUD 异常返回错误结果"""
        service._deployment_crud.get_by_source_portfolio.side_effect = Exception("DB error")

        result = service.find_by_source_portfolio(source_portfolio_id="pf-src")

        assert result.is_success() is False


class TestFindByTargetPortfolio:
    """DeploymentService.find_by_target_portfolio 测试"""

    @pytest.fixture
    def service(self):
        deployment_crud = MagicMock()
        return DeploymentService(deployment_crud=deployment_crud)

    @pytest.mark.unit
    def test_returns_deployments(self, service):
        """返回目标组合的部署记录"""
        dep = MagicMock()
        dep.source_portfolio_id = "pf-src"
        dep.target_portfolio_id = "pf-tgt"
        service._deployment_crud.get_by_target_portfolio.return_value = [dep]

        result = service.find_by_target_portfolio(target_portfolio_id="pf-tgt")

        assert result.is_success()
        assert len(result.data) == 1
        service._deployment_crud.get_by_target_portfolio.assert_called_once_with("pf-tgt")

    @pytest.mark.unit
    def test_returns_error_on_exception(self, service):
        """CRUD 异常返回错误结果"""
        service._deployment_crud.get_by_target_portfolio.side_effect = Exception("DB error")

        result = service.find_by_target_portfolio(target_portfolio_id="pf-tgt")

        assert result.is_success() is False
