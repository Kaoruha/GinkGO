# Issue: 组件列表需要显示被多少个 Portfolio 组装持有（新列 portfolio_count）
# Upstream: api.api.components.list_components（注入列）, PortfolioMappingService.count_portfolios_by_files
# Downstream: PortfolioFileMappingCRUD.count_portfolios_by_files（SQL 层 GROUP BY + COUNT(DISTINCT)）
# Role: 契约——分页条目带 portfolio_count、单次聚合查询、失败不阻断列表、无 N+1

"""
组件持有数（portfolio_count）测试

验证：
1. service：单次调 CRUD 聚合方法透传 {file_id: 去重 portfolio 数}；空入参短路
2. endpoint：分页后条目注入 portfolio_count；service 失败时列表仍 200（列全 0）
3. 内置组件（无 DB 记录）计数为 0

去重语义在 CRUD 的 SQL 层（COUNT(DISTINCT portfolio_id)），此处只验 service
契约：透传正确、单次调用（无 N+1）、空入参不触发查询。
"""

import asyncio
from types import SimpleNamespace
from unittest.mock import patch, MagicMock


def run_async(coro):
    return asyncio.run(coro)


class TestCountPortfoliosByFiles:
    def _service(self, crud):
        from ginkgo.data.services.portfolio_mapping_service import PortfolioMappingService

        return PortfolioMappingService(
            mapping_crud=crud,
            param_service=MagicMock(),
            mongo_driver=MagicMock(),
            file_service=MagicMock(),
        )

    def test_passes_through_crud_aggregate_result(self):
        crud = MagicMock()
        # CRUD SQL 层 GROUP BY + COUNT(DISTINCT) 的产物：每组件一行计数
        crud.count_portfolios_by_files.return_value = {"f-1": 2, "f-2": 1}

        result = self._service(crud).count_portfolios_by_files(["f-1", "f-2"])

        assert result.is_success()
        assert result.data == {"f-1": 2, "f-2": 1}

    def test_calls_crud_aggregate_once_with_ids(self):
        crud = MagicMock()
        crud.count_portfolios_by_files.return_value = {}

        self._service(crud).count_portfolios_by_files(["f-1", "f-2", "f-3"])

        assert crud.count_portfolios_by_files.call_args.args[0] == ["f-1", "f-2", "f-3"]
        assert crud.count_portfolios_by_files.call_count == 1  # 无 N+1

    def test_none_result_normalizes_to_empty_map(self):
        crud = MagicMock()
        crud.count_portfolios_by_files.return_value = None

        result = self._service(crud).count_portfolios_by_files(["f-1"])

        assert result.is_success() and result.data == {}

    def test_empty_input_shortcircuits_without_query(self):
        crud = MagicMock()

        result = self._service(crud).count_portfolios_by_files([])

        assert result.is_success() and result.data == {}
        crud.count_portfolios_by_files.assert_not_called()

    def test_crud_failure_returns_error_not_raise(self):
        crud = MagicMock()
        crud.count_portfolios_by_files.side_effect = RuntimeError("db down")

        result = self._service(crud).count_portfolios_by_files(["f-1"])

        assert not result.is_success()
        assert "db down" in result.error


class TestListComponentInjectsCount:
    def _file_record(self, uuid, name):
        return SimpleNamespace(
            uuid=uuid, name=name, type=1,
            create_at=None, update_at=None, is_del=False,
        )

    def test_page_items_get_portfolio_count(self):
        from api.components import list_components

        file_service = MagicMock()
        file_service.list_components.return_value = MagicMock(
            is_success=lambda: True,
            data={"data": [self._file_record("f-1", "s1.py"), self._file_record("f-2", "s2.py")]},
        )
        mapping_service = MagicMock()
        mapping_service.count_portfolios_by_files.return_value = MagicMock(
            is_success=lambda: True, data={"f-1": 3},
        )

        with patch("api.components.get_file_service", return_value=file_service), \
             patch("api.components.get_portfolio_mapping_service", return_value=mapping_service):
            result = run_async(list_components(component_type="strategy", page=1, page_size=20))

        items = result["data"]  # paginated() → ok(data=items, meta=分页)
        by_uuid = {it["uuid"]: it for it in items}
        assert by_uuid["f-1"]["portfolio_count"] == 3
        assert by_uuid["f-2"]["portfolio_count"] == 0  # map 未含 → 0
        # 只对分页条目查一次（含内置组件 uuid——DB 无记录自然 0，无害）
        ids = mapping_service.count_portfolios_by_files.call_args.args[0]
        page_uuids = {it["uuid"] for it in items}
        assert set(ids) <= page_uuids
        assert {"f-1", "f-2"} <= set(ids)

    def test_mapping_failure_does_not_block_list(self):
        from api.components import list_components

        file_service = MagicMock()
        file_service.list_components.return_value = MagicMock(
            is_success=lambda: True,
            data={"data": [self._file_record("f-1", "s1.py")]},
        )
        mapping_service = MagicMock()
        mapping_service.count_portfolios_by_files.side_effect = RuntimeError("boom")

        with patch("api.components.get_file_service", return_value=file_service), \
             patch("api.components.get_portfolio_mapping_service", return_value=mapping_service):
            result = run_async(list_components(component_type="strategy", page=1, page_size=20))

        items = result["data"]
        assert items and items[0]["portfolio_count"] == 0  # 失败兜底 0，列表仍返回
