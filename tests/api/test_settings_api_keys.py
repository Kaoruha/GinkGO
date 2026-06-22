# Issue #5780 + #5816: settings api-keys 端点接 ApiKeyService（不再返回硬编码桩）
# Upstream: api.api.settings.list_api_keys / create_api_key
# Downstream: ginkgo.data.services.api_key_service.ApiKeyService
# Role: 验证 list/create 端点装配真实 ApiKeyService，返回扁平数组（前端 apiKey.ts
#       期望 res.data 是 list，字段 uuid/key_prefix 对齐 service 非 key_id/masked_key）；
#       create 返回唯一 uuid + key_value（仅一次），不再硬编码 new-key。

"""
#5780/#5816 回归测试：settings api-keys 端点返回硬编码桩。

桩（settings.py:1799-1825）list 返固定 ``[{key_id:key-1, masked_key:...}]``、
create 返固定 ``{key_id:new-key, masked_key:...}``，未接已存在的
``ApiKeyService``（crud 真实查 DB，容器已注入）。前端 ``apiKey.ts`` 已按 service
真实契约（uuid/key_prefix/permissions_list）写好，后端欠债。

本测试用 ``MagicMock(spec=ApiKeyService)`` 强制 mock 只暴露真实方法，mock 返回值
用 service 实际的裸 dict 格式（``{"success":True,"data":{...}}``，非 ServiceResult）。
"""
import asyncio

import pytest
from unittest.mock import patch, MagicMock

from ginkgo.data.services.api_key_service import ApiKeyService
from ginkgo.libs import GCONF


@pytest.fixture(autouse=True)
def _ensure_debug():
    """连 test 库（Debug 模式），真实 service 冒烟隔离生产库。"""
    GCONF.set_debug(True)


def run_async(coro):
    return asyncio.run(coro)


def _list_result(keys):
    """ApiKeyService.list_api_keys 返回裸 dict（非 ServiceResult）。"""
    return {
        "success": True,
        "data": {"api_keys": list(keys)},
    }


def _create_result(uuid="ak-uuid-1", key_value="ginkgo-abc123"):
    """ApiKeyService.create_api_key 返回裸 dict。"""
    return {
        "success": True,
        "data": {
            "uuid": uuid,
            "name": "TestKey",
            "key_value": key_value,
            "key_prefix": "ginkgo",
            "permissions": "read",
            "expires_at": None,
            "is_active": True,
            "user_id": None,
        },
    }


class TestListApiKeysContract:
    """GET /api-keys 端点契约测试（#5780）。"""

    def test_returns_flat_array_from_service(self):
        """list_api_keys 接 service，返回扁平数组（前端期望 res.data 是 list）。"""
        mock_service = MagicMock(spec=ApiKeyService)
        mock_service.list_api_keys.return_value = _list_result([
            {"uuid": "k-1", "name": "Test", "key_prefix": "ginkgo"},
        ])

        from api.settings import list_api_keys

        with patch("api.settings.get_api_key_service", return_value=mock_service):
            result = run_async(list_api_keys())

        assert result["code"] == 0
        # 扁平数组，非 {"api_keys":[...]} 包装
        assert isinstance(result["data"], list)
        assert result["data"][0]["uuid"] == "k-1"

    def test_empty_list_returns_empty_array(self):
        """无 key 时返回空数组（非硬编码 key-1）。"""
        mock_service = MagicMock(spec=ApiKeyService)
        mock_service.list_api_keys.return_value = _list_result([])

        from api.settings import list_api_keys

        with patch("api.settings.get_api_key_service", return_value=mock_service):
            result = run_async(list_api_keys())

        assert result["code"] == 0
        assert result["data"] == []

    def test_service_failure_raises_http_exception(self):
        """service success=False 时端点 raise HTTPException 500（不把失败当 ok 返）。"""
        from fastapi import HTTPException

        mock_service = MagicMock(spec=ApiKeyService)
        mock_service.list_api_keys.return_value = {"success": False, "message": "DB down"}

        from api.settings import list_api_keys

        with patch("api.settings.get_api_key_service", return_value=mock_service):
            with pytest.raises(HTTPException) as exc:
                run_async(list_api_keys())

        assert exc.value.status_code == 500


class TestCreateApiKeyContract:
    """POST /api-keys 端点契约测试（#5816）。"""

    def test_returns_unique_uuid_not_new_key(self):
        """create 返回 service 生成的唯一 uuid（不再硬编码 new-key）。"""
        mock_service = MagicMock(spec=ApiKeyService)
        mock_service.create_api_key.return_value = _create_result(
            uuid="ak-real-uuid-xyz", key_value="ginkgo-secret-123"
        )

        from api.settings import create_api_key

        with patch("api.settings.get_api_key_service", return_value=mock_service):
            result = run_async(create_api_key({"name": "TestKey", "permissions": ["read"]}))

        assert result["code"] == 0
        assert result["data"]["uuid"] == "ak-real-uuid-xyz"
        assert result["data"]["uuid"] != "new-key"  # 不再是桩的通用值

    def test_returns_full_key_value_once(self):
        """create 返回完整 key_value（仅创建时返回一次，#5816 验收）。"""
        mock_service = MagicMock(spec=ApiKeyService)
        mock_service.create_api_key.return_value = _create_result(key_value="ginkgo-full-secret")

        from api.settings import create_api_key

        with patch("api.settings.get_api_key_service", return_value=mock_service):
            result = run_async(create_api_key({"name": "TestKey"}))

        assert result["data"]["key_value"] == "ginkgo-full-secret"

    def test_forwards_name_and_permissions_to_service(self):
        """端点透传 name/permissions 给 service。"""
        mock_service = MagicMock(spec=ApiKeyService)
        mock_service.create_api_key.return_value = _create_result()

        from api.settings import create_api_key

        with patch("api.settings.get_api_key_service", return_value=mock_service):
            run_async(create_api_key({"name": "MyKey", "permissions": ["read", "trade"]}))

        mock_service.create_api_key.assert_called_once()
        _, kwargs = mock_service.create_api_key.call_args
        assert kwargs["name"] == "MyKey"
        assert kwargs["permissions"] == ["read", "trade"]
