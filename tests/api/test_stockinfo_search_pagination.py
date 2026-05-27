# Issue: stockinfo 搜索后分页结果不完整
# Upstream: api.api.data.get_stockinfo
# Downstream: StockinfoService.search()
# Role: 验证 stockinfo 搜索通过 DB 层 or_ 条件完成，不做 Python 过滤

"""
stockinfo 搜索分页测试

验证 get_stockinfo 将 search 参数下推到 DB 层，
不再在 Python 层做搜索过滤导致结果不完整和 total 不准。
"""

import asyncio
import pytest
from unittest.mock import patch, MagicMock


def run_async(coro):
    return asyncio.run(coro)


def make_mock_result(data=None, success=True):
    """创建模拟 ServiceResult"""
    result = MagicMock()
    result.is_success.return_value = success
    result.data = data
    return result


class TestStockinfoSearchPagination:
    """stockinfo 搜索分页测试"""

    def test_calls_service_search_when_keyword_provided(self):
        """TDD Red: 有 search 参数时应调用 service 的 search 方法"""

        mock_service = MagicMock()
        mock_service.search.return_value = make_mock_result(
            data={"data": [], "total": 0}
        )

        from api.data import get_stockinfo

        with patch("api.data.get_stockinfo_service", return_value=mock_service):
            result = run_async(get_stockinfo(search="平安", page=1, page_size=20))

        # 应调用 search 而非 get
        mock_service.search.assert_called_once()

    def test_search_passes_pagination_params(self):
        """TDD Red: search 参数应传递 page/page_size 到 service"""

        mock_service = MagicMock()
        mock_service.search.return_value = make_mock_result(
            data={"data": [], "total": 0}
        )

        from api.data import get_stockinfo

        with patch("api.data.get_stockinfo_service", return_value=mock_service):
            result = run_async(get_stockinfo(search="000001", page=3, page_size=15))

        call_args = mock_service.search.call_args
        assert call_args.kwargs.get("page") == 2 or call_args[1].get("page") == 2
        assert call_args.kwargs.get("page_size") == 15 or call_args[1].get("page_size") == 15

    def test_search_returns_total_from_db(self):
        """TDD Red: total 应来自 DB count 而非 len(过滤后结果)"""

        mock_service = MagicMock()
        stock = MagicMock()
        stock.code = "000001.SZ"
        stock.code_name = "平安银行"
        stock.market = 1
        stock.industry = "银行"
        stock.is_active = True
        stock.uuid = "uuid-1"
        stock.update_at = None

        mock_service.search.return_value = make_mock_result(
            data={"data": [stock], "total": 42}
        )

        from api.data import get_stockinfo

        with patch("api.data.get_stockinfo_service", return_value=mock_service):
            result = run_async(get_stockinfo(search="平安", page=1, page_size=20))

        # total 应来自 DB count
        assert result["meta"]["total"] == 42

    def test_search_handles_orm_objects_from_crud(self):
        """service 返回 ModelList（ORM 对象）时，API 应通过属性访问"""

        mock_service = MagicMock()
        stock = MagicMock()
        stock.code = "000001.SZ"
        stock.code_name = "平安银行"
        stock.market = 1
        stock.industry = "银行"
        stock.is_del = False
        stock.uuid = "uuid-1"
        stock.update_at = None

        mock_service.search.return_value = make_mock_result(
            data={"data": [stock], "total": 1}
        )

        from api.data import get_stockinfo

        with patch("api.data.get_stockinfo_service", return_value=mock_service):
            result = run_async(get_stockinfo(search="平安", page=1, page_size=20))

        items = result["data"]
        assert len(items) == 1
        assert items[0]["code"] == "000001.SZ"
        assert items[0]["name"] == "平安银行"
        assert items[0]["is_active"] is True

    def test_no_search_uses_get_with_pagination(self):
        """TDD Red: 无 search 时直接用 get + DB 分页，不经过 search"""

        mock_service = MagicMock()
        mock_stock = MagicMock()
        mock_stock.code = "000001.SZ"
        mock_stock.code_name = "平安银行"
        mock_stock.market = 1
        mock_stock.industry = "银行"
        mock_stock.is_active = True
        mock_stock.uuid = "uuid-1"
        mock_stock.update_at = None

        mock_service.get.return_value = make_mock_result(data=[mock_stock])
        mock_service.count.return_value = make_mock_result(data=100)

        from api.data import get_stockinfo

        with patch("api.data.get_stockinfo_service", return_value=mock_service):
            result = run_async(get_stockinfo(page=2, page_size=10))

        # 无 search 时应调 get（带分页）而非 search
        mock_service.get.assert_called_once()
        mock_service.search.assert_not_called()
