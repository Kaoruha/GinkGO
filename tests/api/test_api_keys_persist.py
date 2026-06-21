# Issue: #5459 — API keys endpoints return hardcoded mock data, not persisted
# Upstream: api.api.settings.create_api_key / list_api_keys / delete_api_key
# Downstream: ApiKeyService.create_api_key / list_api_keys / delete_api_key
# Role: 验证 settings.py api-keys 端点接线现成 ApiKeyService（持久化），非硬编码 mock

"""
API keys 持久化测试 (#5459)。

根因：api/api/settings.py list/create 端点 `# TODO` 占位直返硬编码 mock
（key-1/new-key），现成 ApiKeyService/CRUD/Model 从未接线。

修复：端点接线 container.api_key_service()——
- create → service.create_api_key(auto_generate=True)，返回一次性 full_key + masked
- list   → service.list_api_keys()，映射 service 数据（非硬编码）
- delete → service.delete_api_key(uuid)
"""

import asyncio
from unittest.mock import patch, MagicMock

import pytest

from core.exceptions import BusinessError


def run_async(coro):
    return asyncio.run(coro)


class TestCreateApiKeyPersists:
    """#5459: create 端点接线 service，返回一次性 full_key + masked。"""

    def test_create_calls_service_autogen_and_returns_full_key(self):
        """验收: create 调 service.create_api_key(auto_generate=True)，返回一次性 full_key + masked。"""
        from api.settings import create_api_key, CreateApiKeyRequest

        req = CreateApiKeyRequest(name="test_key", expires_in_days=365)

        mock_svc = MagicMock()
        mock_svc.create_api_key.return_value = {
            "success": True,
            "data": {
                "uuid": "u1",
                "name": "test_key",
                "key_value": "ginkgo-abc123",  # 仅创建时返回一次
                "key_prefix": "ginkgo-a",
                "permissions": "read",
                "expires_at": "2027-01-01T00:00:00",
                "is_active": True,
                "user_id": None,
            },
            "message": "API Key created successfully",
        }

        with patch("api.settings.get_api_key_service", return_value=mock_svc):
            result = run_async(create_api_key(req))

        # service 被调用
        mock_svc.create_api_key.assert_called_once()
        # auto_generate=True（一次性明文 key 仅在 autogen 时返回）
        args, kwargs = mock_svc.create_api_key.call_args
        assert kwargs.get("name") == "test_key"
        assert kwargs.get("expires_days") == 365
        assert kwargs.get("auto_generate") is True

        # 返回含一次性 full_key + masked + key_id（非硬编码 new-key）
        assert result["data"]["key_id"] == "u1"
        assert result["data"]["full_key"] == "ginkgo-abc123"
        assert "****" in result["data"]["masked_key"]
        assert result["data"]["name"] == "test_key"

    def test_create_service_failure_raises_business_error(self):
        """service 返回 success=False → BusinessError（非静默返回 mock）。"""
        from api.settings import create_api_key, CreateApiKeyRequest

        req = CreateApiKeyRequest(name="bad")
        mock_svc = MagicMock()
        mock_svc.create_api_key.return_value = {"success": False, "message": "boom"}

        with patch("api.settings.get_api_key_service", return_value=mock_svc):
            with pytest.raises(BusinessError):
                run_async(create_api_key(req))


class TestListApiKeyMapsService:
    """#5459: list 端点接线 service.list_api_keys，返回实际数据（非硬编码 key-1）。"""

    def test_list_returns_service_data_not_hardcoded(self):
        """验收: list 调 service.list_api_keys，映射返回，不含硬编码 key-1/生产环境密钥。"""
        from api.settings import list_api_keys

        mock_svc = MagicMock()
        mock_svc.list_api_keys.return_value = {
            "success": True,
            "data": {
                "api_keys": [
                    {
                        "uuid": "real-uuid-1",
                        "name": "我的开发密钥",
                        "key_prefix": "ginkgo-x",
                        "permissions": "read",
                        "permissions_list": ["read"],
                        "is_active": True,
                        "is_expired": False,
                        "expires_at": "2027-01-01T00:00:00",
                        "last_used_at": "2026-06-20T10:00:00",
                        "created_at": "2026-06-01T00:00:00",
                        "description": None,
                        "user_id": None,
                    }
                ]
            },
        }

        with patch("api.settings.get_api_key_service", return_value=mock_svc):
            result = run_async(list_api_keys())

        mock_svc.list_api_keys.assert_called_once()
        keys = result["data"]
        assert len(keys) == 1
        # 映射 service 数据，非硬编码
        assert keys[0]["key_id"] == "real-uuid-1"
        assert keys[0]["name"] == "我的开发密钥"
        assert "****" in keys[0]["masked_key"]
        # 绝不含硬编码 mock
        assert all(k["key_id"] != "key-1" for k in keys)
        assert all("生产环境" not in k["name"] for k in keys)


class TestDeleteApiKeyCallsService:
    """#5459: delete 端点接线 service.delete_api_key（验收: Delete removes the key）。"""

    def test_delete_calls_service_and_returns_ok(self):
        """验收: delete 调 service.delete_api_key(key_id)，success 返回 ok。"""
        from api.settings import delete_api_key

        mock_svc = MagicMock()
        mock_svc.delete_api_key.return_value = {
            "success": True,
            "message": "API Key deleted successfully",
        }

        with patch("api.settings.get_api_key_service", return_value=mock_svc):
            result = run_async(delete_api_key(key_id="real-uuid-1"))

        mock_svc.delete_api_key.assert_called_once_with("real-uuid-1")
        assert result["data"]["deleted"] is True
        assert result["data"]["key_id"] == "real-uuid-1"

    def test_delete_not_found_raises_business_error(self):
        """service 返回 success=False（key 不存在）→ BusinessError。"""
        from api.settings import delete_api_key

        mock_svc = MagicMock()
        mock_svc.delete_api_key.return_value = {"success": False, "message": "API Key not found"}

        with patch("api.settings.get_api_key_service", return_value=mock_svc):
            with pytest.raises(BusinessError):
                run_async(delete_api_key(key_id="ghost"))
