# Issue: components 列表全量加载 + Python 过滤
# Upstream: api.api.components.list_components
# Downstream: FileService.list_components()
# Role: 验证组件列表使用服务端分页和过滤，不在 API 层做 Python 过滤

"""
组件列表分页测试

验证 list_components 将过滤条件和分页参数下推到 service 层，
不在 API 层全量加载后 Python 过滤/排序/切片。
"""

import asyncio
import pytest
from unittest.mock import patch, MagicMock


def run_async(coro):
    return asyncio.run(coro)


def make_mock_result(data=None, success=True):
    result = MagicMock()
    result.is_success.return_value = success
    result.data = data
    return result


class TestComponentsPagination:
    """组件列表分页测试"""

    def test_calls_list_components_not_get_by_type(self):
        """TDD Red: list_components 应调用 list_components 方法而非 get_by_type"""
        mock_service = MagicMock()
        mock_service.list_components.return_value = make_mock_result(data={"data": [], "total": 0})

        from api.components import list_components

        with patch("api.components.get_file_service", return_value=mock_service):
            result = run_async(list_components(page=1, page_size=20))

        mock_service.list_components.assert_called_once()
        mock_service.get_by_type.assert_not_called()

    def test_passes_filters_and_pagination(self):
        """TDD Red: 过滤条件和分页参数应传给 service"""

        mock_service = MagicMock()
        mock_service.list_components.return_value = make_mock_result(data={"data": [], "total": 0})

        from api.components import list_components

        with patch("api.components.get_file_service", return_value=mock_service):
            result = run_async(
                list_components(
                    component_type="strategy",
                    is_active=True,
                    keyword="ma",
                    page=2,
                    page_size=15,
                )
            )

        call_kwargs = mock_service.list_components.call_args.kwargs
        assert call_kwargs.get("page") == 1  # 0-based
        assert call_kwargs.get("page_size") == 15
        assert call_kwargs.get("keyword") == "ma"

    def test_returns_total_from_service_plus_builtins(self):
        """#5827: total 应包含 service/DB 组件和内置组件。"""
        mock_service = MagicMock()
        mock_service.list_components.return_value = make_mock_result(data={"data": [], "total": 50})

        from api.components import list_components, _list_builtin_components

        with patch("api.components.get_file_service", return_value=mock_service):
            result = run_async(list_components(page=1, page_size=20))

        assert result["meta"]["total"] == 50 + len(_list_builtin_components())

    def test_handles_orm_objects_from_crud(self):
        """service 返回 ModelList（ORM 对象）时，API 应通过属性访问"""

        mock_file = MagicMock()
        mock_file.uuid = "uuid-1"
        mock_file.name = "MyStrategy"
        mock_file.type = 6
        mock_file.is_del = False
        mock_file.create_at.isoformat.return_value = "2025-01-01T00:00:00"
        mock_file.update_at.isoformat.return_value = "2025-01-02T00:00:00"

        mock_service = MagicMock()
        mock_service.list_components.return_value = make_mock_result(data={"data": [mock_file], "total": 1})

        from api.components import list_components

        with patch("api.components.get_file_service", return_value=mock_service):
            result = run_async(list_components(page=1, page_size=20))

        from api.components import _list_builtin_components

        assert result["meta"]["total"] == 1 + len(_list_builtin_components())
        item = result["data"][0]
        assert item["name"] == "MyStrategy"
        assert item["component_type"] == "strategy"
        assert item["is_active"] is True
