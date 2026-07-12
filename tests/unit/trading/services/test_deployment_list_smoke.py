"""#5009 DeploymentService.list/count 分页 smoke（#6685 diff coverage gate 采集）。

list_deployments(page=, page_size=) → _deployment_crud.find(filters=, page=, page_size=,
order_by="create_at", desc_order=True)；count_deployments → _deployment_crud.count(filters=)。
两者为本 PR 新增可执行行，供 CLI metadata.total 真实总数。用 mock 依赖（不连 DB）补
覆盖信号，纳入 smoke 子集供门禁测量。
"""

import os
import sys
import pytest
from unittest.mock import MagicMock

_path = os.path.join(os.path.dirname(__file__), "..", "..", "..")
if _path not in sys.path:
    sys.path.insert(0, _path)

from ginkgo.trading.services.deployment_service import DeploymentService


@pytest.fixture
def service():
    return DeploymentService(deployment_crud=MagicMock())


class TestListDeploymentsPagination:
    """list_deployments 把 page/page_size/portfolio 下推 find（#5009）。"""

    @pytest.mark.unit
    def test_list_passes_page_pagesize_order_to_find(self, service):
        service._deployment_crud.find.return_value = []
        result = service.list_deployments(page=2, page_size=10)
        assert result.success is True
        assert result.data == []
        _, kwargs = service._deployment_crud.find.call_args
        assert kwargs["page"] == 2
        assert kwargs["page_size"] == 10
        assert kwargs["order_by"] == "create_at"
        assert kwargs["desc_order"] is True

    @pytest.mark.unit
    def test_list_unlimited_passes_none(self, service):
        service._deployment_crud.find.return_value = []
        service.list_deployments(page=0, page_size=0)
        _, kwargs = service._deployment_crud.find.call_args
        # page_size=0 → CLI 侧转 None；service 直传（None = BaseCRUD 不分页）
        assert kwargs["page_size"] == 0 or kwargs["page_size"] is None

    @pytest.mark.unit
    def test_list_portfolio_filter_pushed_to_find(self, service):
        service._deployment_crud.find.return_value = []
        service.list_deployments(portfolio_id="pf-src")
        _, kwargs = service._deployment_crud.find.call_args
        assert kwargs["filters"]["source_portfolio_id"] == "pf-src"

    @pytest.mark.unit
    def test_list_maps_records_to_dict(self, service):
        rec = MagicMock()
        service._deployment_crud.find.return_value = [rec]
        result = service.list_deployments()
        assert result.success is True
        assert len(result.data) == 1

    @pytest.mark.unit
    def test_list_slices_records_when_portfolio_and_page(self, service):
        """#5009: portfolio + page + page_size 时对 find 结果二次切片（offset 对齐）。"""
        recs = [MagicMock() for _ in range(3)]
        service._deployment_crud.find.return_value = recs
        # page=0, page_size=2 → records[0:2]，返回 2 条
        result = service.list_deployments(portfolio_id="pf-src", page=0, page_size=2)
        assert result.success is True
        assert len(result.data) == 2
        # page=1 → records[2:4]，返回 1 条（翻页对齐 offset）
        result2 = service.list_deployments(portfolio_id="pf-src", page=1, page_size=2)
        assert len(result2.data) == 1


class TestCountDeployments:
    """count_deployments → _deployment_crud.count(filters=)（#5009 metadata.total）。"""

    @pytest.mark.unit
    def test_count_returns_dict(self, service):
        service._deployment_crud.count.return_value = 7
        result = service.count_deployments()
        assert result.success is True
        assert result.data == {"count": 7}
        service._deployment_crud.count.assert_called_once()

    @pytest.mark.unit
    def test_count_portfolio_filter(self, service):
        service._deployment_crud.count.return_value = 3
        service.count_deployments(portfolio_id="pf-src")
        _, kwargs = service._deployment_crud.count.call_args
        assert kwargs["filters"]["source_portfolio_id"] == "pf-src"
