# Issue #5880 缺陷2: GET /components/?name=xxx 名称过滤失效
# Upstream: api.api.components.list_components
# Downstream: FileService.list_components(keyword=...) -> filters["name__like"]
# Role: ?name=xxx 应作为 keyword 下推到 service 层做 name__like 过滤，
#       而非被 FastAPI 当未知 query 参数静默丢弃

import asyncio
from unittest.mock import patch, MagicMock


def run_async(coro):
    return asyncio.run(coro)


def make_mock_result(total=0):
    result = MagicMock()
    result.is_success.return_value = True
    result.data = {"data": [], "total": total}
    return result


class TestComponentsNameFilter:
    """缺陷2: GET /components/?name=xxx 名称过滤"""

    def test_name_param_passed_as_keyword_to_service(self):
        """?name=moving_average 应作为 keyword 传给 service（复用 name__like 过滤）"""
        mock_service = MagicMock()
        mock_service.list_components.return_value = make_mock_result(total=0)

        from api.components import list_components

        with patch("api.components.get_file_service", return_value=mock_service):
            run_async(list_components(name="moving_average", page=1, page_size=20))

        call_kwargs = mock_service.list_components.call_args.kwargs
        assert call_kwargs.get("keyword") == "moving_average"
