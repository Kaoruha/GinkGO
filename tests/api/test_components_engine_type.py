# Issue #5880 缺陷4b: GET /components/?component_type=engine 返回 0 / 抛 400
# Upstream: api.api.components.COMPONENT_FILE_TYPE_MAP / FILE_TYPE_TO_COMPONENT_TYPE
# Downstream: list_components 的 component_type 校验 + types_to_check 构建
# Role: engine 是 file-based 组件（file_crud 支持 ENGINE），API 类型映射应覆盖 engine，
#       否则 ?component_type=engine 命中 400 Invalid component type。
#       注意缺陷4a 已修正 loader 源码回退映射，此处是 API 层的类型字典。

import asyncio
from unittest.mock import patch, MagicMock


def run_async(coro):
    return asyncio.run(coro)


def make_mock_result(total=0):
    result = MagicMock()
    result.is_success.return_value = True
    result.data = {"data": [], "total": total}
    return result


class TestComponentsEngineType:
    """缺陷4b: engine 类型在 API 类型映射中可用"""

    def test_engine_in_component_file_type_map(self):
        from api.components import COMPONENT_FILE_TYPE_MAP
        from ginkgo.enums import FILE_TYPES

        assert "engine" in COMPONENT_FILE_TYPE_MAP
        assert COMPONENT_FILE_TYPE_MAP["engine"] == FILE_TYPES.ENGINE

    def test_engine_reverse_mapping(self):
        from api.components import FILE_TYPE_TO_COMPONENT_TYPE
        from ginkgo.enums import FILE_TYPES

        assert FILE_TYPE_TO_COMPONENT_TYPE[FILE_TYPES.ENGINE.value] == "engine"

    def test_list_components_engine_not_400(self):
        """?component_type=engine 不再抛 400，且 ENGINE 被加入 types_to_check 下推 service"""
        mock_service = MagicMock()
        mock_service.list_components.return_value = make_mock_result(total=0)

        from api.components import list_components
        from ginkgo.enums import FILE_TYPES

        with patch("api.components.get_file_service", return_value=mock_service):
            result = run_async(list_components(component_type="engine", page=1, page_size=20))

        call_kwargs = mock_service.list_components.call_args.kwargs
        assert FILE_TYPES.ENGINE in call_kwargs.get("file_types", [])
