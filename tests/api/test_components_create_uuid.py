# #5885 — POST /components/ 创建成功但返回 500 "Failed to get created component UUID"
# Upstream: api.api.components.create_component
# Downstream: FileService.add
# Role: 验证 create_component 从 FileService.add 返回的嵌套结构正确提取 uuid

"""
组件创建 uuid 提取测试

FileService.add 成功返回 ServiceResult(data={"file_info": {"uuid": ..., ...}})，
uuid 嵌套在 file_info 下。create_component 必须从 file_info 取 uuid，
直接 result.data.get("uuid") 会取到 None 抛 500（数据已入库的不一致状态）。
"""

import asyncio
import pytest
from unittest.mock import patch, MagicMock, AsyncMock


def run_async(coro):
    return asyncio.run(coro)


def make_mock_result(data=None, success=True, message="ok"):
    result = MagicMock()
    result.is_success.return_value = success
    result.data = data
    result.message = message
    return result


class TestCreateComponentExtractsUuid:
    """create_component 应从 file_info 嵌套结构提取 uuid（#5885）"""

    def test_extracts_uuid_from_file_info(self):
        """add 返回 data={"file_info":{"uuid":..}}，create_component 应取到 uuid 传给 get_component。

        根因: components.py:264 ``result.data.get("uuid")`` 跳过了 file_info 层，
        取到 None 抛 500 "Failed to get created component UUID"，但数据已入库。
        """
        mock_service = MagicMock()
        mock_service.add.return_value = make_mock_result(
            data={"file_info": {"uuid": "comp-uuid-123", "name": "test"}}
        )
        mock_get_component = AsyncMock(
            return_value={"code": 0, "data": {"uuid": "comp-uuid-123"}}
        )

        from api.components import create_component, ComponentCreate

        data = ComponentCreate(name="test", component_type="strategy", code="code...")
        with patch("api.components.get_file_service", return_value=mock_service), \
             patch("api.components.get_component", mock_get_component):
            response = run_async(create_component(data))

        # 证明从 file_info 取到了 uuid（传给 get_component 而非抛 500）
        mock_get_component.assert_called_once_with("comp-uuid-123")
        assert response["data"]["uuid"] == "comp-uuid-123"
