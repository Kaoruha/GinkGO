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
    def test_list_portfolio_and_pagination_coexist_in_find(self, service):
        """#5009: portfolio 过滤 + page/page_size 同时下推 find（单层分页，service 不二次切片）。

        分页单层委托 find（DB 层 offset/limit）；service 直接返回 find 结果。
        早先的「find 后再内存切片 records[page*page_size:]」是双层分页——find 已按
        page/page_size 截断后再切片，对 page>0 会返空集（生产 bug），且与 engine/
        portfolio service（无内存切片）不一致。契约对齐 test_deployment_service_info_status。
        """
        recs = [MagicMock() for _ in range(3)]
        service._deployment_crud.find.return_value = recs
        result = service.list_deployments(portfolio_id="pf-src", page=1, page_size=2)
        assert result.success is True
        # 过滤 + 分页共存于同一次 find 调用；service 直返 find 结果（3 条），不二次切片
        _, kwargs = service._deployment_crud.find.call_args
        assert kwargs["filters"]["source_portfolio_id"] == "pf-src"
        assert kwargs["page"] == 1
        assert kwargs["page_size"] == 2
        assert len(result.data) == 3


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
