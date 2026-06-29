"""
#3882: DeploymentService 返回类型统一 + saga_transaction 死代码移除

守护契约：
- find_by_source_portfolio / find_by_target_portfolio 返回 list[dict]，
  字段对齐 list_deployments（消除 [[arch_service_dict_wrapped_return]] 陷阱：
  消费方属性访问 service 返的 dict 静默失效）。
- get_portfolio_mappings 始终返 list[dict]（saga_transaction isinstance
  死分支移除的前提契约，防回退）。
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


@pytest.fixture
def service():
    deployment_crud = MagicMock()
    return DeploymentService(deployment_crud=deployment_crud)


def _mock_deployment():
    """构造字段齐全的部署记录 mock。"""
    dep = MagicMock()
    dep.uuid = "dep-1"
    dep.source_task_id = "task-1"
    dep.target_portfolio_id = "pf-tgt"
    dep.source_portfolio_id = "pf-src"
    dep.mode = 1
    dep.account_id = "acc-1"
    dep.status = "DEPLOYED"
    dep.create_at = None
    return dep


class TestFindBySourceReturnsDict:
    """find_by_source_portfolio 返回 dict 列表，字段对齐 list_deployments（#3882）。"""

    @pytest.mark.unit
    def test_returns_dict_with_list_deployments_fields(self, service):
        service._deployment_crud.get_by_source_portfolio.return_value = [_mock_deployment()]

        result = service.find_by_source_portfolio(source_portfolio_id="pf-src")

        assert result.is_success()
        assert isinstance(result.data, list)
        assert len(result.data) == 1
        item = result.data[0]
        assert isinstance(item, dict)
        assert item["deployment_id"] == "dep-1"
        assert item["source_task_id"] == "task-1"
        assert item["target_portfolio_id"] == "pf-tgt"
        assert item["source_portfolio_id"] == "pf-src"
        assert item["mode"] == 1
        assert item["account_id"] == "acc-1"
        assert item["status"] == "DEPLOYED"


class TestFindByTargetReturnsDict:
    """find_by_target_portfolio 同样返回 dict 列表（#3882 对称契约）。"""

    @pytest.mark.unit
    def test_returns_dict_with_list_deployments_fields(self, service):
        service._deployment_crud.get_by_target_portfolio.return_value = [_mock_deployment()]

        result = service.find_by_target_portfolio(target_portfolio_id="pf-tgt")

        assert result.is_success()
        item = result.data[0]
        assert isinstance(item, dict)
        assert item["deployment_id"] == "dep-1"
        assert item["target_portfolio_id"] == "pf-tgt"
        assert item["source_portfolio_id"] == "pf-src"


class TestPortfolioMappingsAlwaysReturnsDictList:
    """
    get_portfolio_mappings 始终返 list[dict]（#3882 saga_transaction 移除
    isinstance 死分支的前提契约；若上游回退到返模型对象，此测试先红）。
    """

    @pytest.mark.unit
    def test_returns_list_of_dict_with_file_id(self):
        from ginkgo.data.services.portfolio_mapping_service import PortfolioMappingService

        mapping_crud = MagicMock()
        param_service = MagicMock()
        param_service.find_by_mapping_id.return_value = []
        m = MagicMock()
        m.uuid = "m-1"
        m.portfolio_id = "pf-1"
        m.file_id = "f-1"
        m.name = "n"
        m.type = "T"
        m.source = "S"
        mapping_crud.find_by_portfolio.return_value = [m]

        svc = PortfolioMappingService(
            mapping_crud=mapping_crud,
            param_service=param_service,
            mongo_driver=MagicMock(),
            file_service=MagicMock(),
        )
        result = svc.get_portfolio_mappings(portfolio_uuid="pf-1", include_params=False)

        assert result.is_success()
        assert isinstance(result.data, list)
        assert len(result.data) == 1
        assert isinstance(result.data[0], dict)
        assert result.data[0]["file_id"] == "f-1"
