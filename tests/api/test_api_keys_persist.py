# Issue: #5459 — API keys endpoints return hardcoded mock data, not persisted
# Upstream: api.api.settings.create_api_key / list_api_keys / delete_api_key
# Downstream: ApiKeyService.create_api_key / list_api_keys / delete_api_key
# Role: 验证 settings.py api-keys 端点接线现成 ApiKeyService（持久化），非硬编码 mock

"""
API keys 持久化测试 (#5459)。

根因：api/api/settings.py list/create 端点 `# TODO` 占位直返硬编码 mock
（key-1/new-key），现成 ApiKeyService/CRUD/Model 从未接线。

修复：端点接线 container.api_key_service()，透传 service.data（字段对齐前端
apiKey.ts 契约），覆盖完整 CRUD + reveal 六端点——
- list   → service.list_api_keys()，透传 api_keys 列表（12 字段）
- create → service.create_api_key(auto_generate=True)，透传含一次性 key_value
- get    → service.get_api_key(uuid)
- update → service.update_api_key(uuid, ...)，返回 {uuid}
- delete → service.delete_api_key(uuid)，返回 {uuid}
- reveal → service.reveal_api_key(uuid)，透传明文 key_value
"""

import asyncio
from unittest.mock import patch, MagicMock

import pytest

from core.exceptions import BusinessError


def run_async(coro):
    return asyncio.run(coro)


class TestCreateApiKeyPersists:
    """#5459: create 端点接线 service，返回一次性 full_key + masked。"""

    def test_create_passes_through_service_data(self):
        """#5459: create 调 service.create_api_key(auto_generate=True)，透传 service.data（含一次性 key_value）。

        字段对齐前端 apiKey.ts CreateApiKeyResponse，禁止手动重映射（uuid→key_id 等）。
        """
        from api.settings import create_api_key, CreateApiKeyRequest

        req = CreateApiKeyRequest(name="test_key", expires_days=365)

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
        args, kwargs = mock_svc.create_api_key.call_args
        assert kwargs.get("name") == "test_key"
        assert kwargs.get("expires_days") == 365  # 前端 expires_days 透传（非 expires_in_days）
        assert kwargs.get("auto_generate") is True

        # 透传 service.data（字段对齐前端 CreateApiKeyResponse）
        assert result["data"]["uuid"] == "u1"
        assert result["data"]["key_value"] == "ginkgo-abc123"  # 一次性明文
        assert result["data"]["key_prefix"] == "ginkgo-a"
        assert result["data"]["name"] == "test_key"
        assert result["data"]["permissions"] == "read"
        # 绝非手动重映射后的 key_id/full_key/masked_key
        assert "key_id" not in result["data"]
        assert "full_key" not in result["data"]
        assert "masked_key" not in result["data"]

    def test_create_service_failure_raises_business_error(self):
        """service 返回 success=False → BusinessError（非静默返回 mock）。"""
        from api.settings import create_api_key, CreateApiKeyRequest

        req = CreateApiKeyRequest(name="bad")
        mock_svc = MagicMock()
        mock_svc.create_api_key.return_value = {"success": False, "message": "boom"}

        with patch("api.settings.get_api_key_service", return_value=mock_svc):
            with pytest.raises(BusinessError):
                run_async(create_api_key(req))


class TestListApiKeyPassesThrough:
    """#5459: list 端点透传 service.list_api_keys 的 api_keys 列表（对齐前端 ApiKey 12 字段）。"""

    def test_list_passes_through_service_data(self):
        """#5459: list 透传 service.data.api_keys，字段对齐前端 ApiKey，非手动重映射/硬编码。"""
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
        # 透传字段（对齐前端 ApiKey 12 字段）
        assert keys[0]["uuid"] == "real-uuid-1"
        assert keys[0]["name"] == "我的开发密钥"
        assert keys[0]["key_prefix"] == "ginkgo-x"
        assert keys[0]["permissions"] == "read"
        assert keys[0]["permissions_list"] == ["read"]
        assert keys[0]["is_active"] is True
        assert keys[0]["is_expired"] is False
        assert keys[0]["expires_at"] == "2027-01-01T00:00:00"
        assert keys[0]["last_used_at"] == "2026-06-20T10:00:00"
        assert keys[0]["created_at"] == "2026-06-01T00:00:00"
        assert keys[0]["description"] is None
        assert keys[0]["user_id"] is None
        # 绝非手动重映射的 key_id/masked_key/status
        assert "key_id" not in keys[0]
        assert "masked_key" not in keys[0]
        # 绝不含硬编码 mock
        assert all("key-1" not in k.get("uuid", "") for k in keys)
        assert all("生产环境" not in k["name"] for k in keys)


class TestDeleteApiKeyCallsService:
    """#5459: delete 端点接线 service.delete_api_key（验收: Delete removes the key）。"""

    def test_delete_calls_service_and_returns_uuid(self):
        """#5459: delete 调 service.delete_api_key(key_id)，返回 {uuid}（对齐前端 deleteApiKey）。"""
        from api.settings import delete_api_key

        mock_svc = MagicMock()
        mock_svc.delete_api_key.return_value = {
            "success": True,
            "message": "API Key deleted successfully",
        }

        with patch("api.settings.get_api_key_service", return_value=mock_svc):
            result = run_async(delete_api_key(key_id="real-uuid-1"))

        mock_svc.delete_api_key.assert_called_once_with("real-uuid-1")
        # 前端 deleteApiKey 期望 APIResponse<{uuid: string}>
        assert result["data"] == {"uuid": "real-uuid-1"}

    def test_delete_not_found_raises_business_error(self):
        """service 返回 success=False（key 不存在）→ BusinessError。"""
        from api.settings import delete_api_key

        mock_svc = MagicMock()
        mock_svc.delete_api_key.return_value = {"success": False, "message": "API Key not found"}

        with patch("api.settings.get_api_key_service", return_value=mock_svc):
            with pytest.raises(BusinessError):
                run_async(delete_api_key(key_id="ghost"))


class TestGetApiKeyPassesThrough:
    """#5459: GET /api-keys/{key_id} 透传 service.get_api_key（对齐前端 getApiKey）。"""

    def test_get_passes_through_service_data(self):
        """#5459: get 透传 service.data，字段对齐前端 ApiKey（含 permissions_list/is_active/is_expired）。"""
        from api.settings import get_api_key

        mock_svc = MagicMock()
        mock_svc.get_api_key.return_value = {
            "success": True,
            "data": {
                "uuid": "u1",
                "name": "开发密钥",
                "key_prefix": "ginkgo-a",
                "permissions": "read",
                "permissions_list": ["read"],
                "is_active": True,
                "is_expired": False,
                "expires_at": "2027-01-01T00:00:00",
                "last_used_at": None,
                "description": None,
                "created_at": "2026-06-01T00:00:00",
                "user_id": None,
            },
        }

        with patch("api.settings.get_api_key_service", return_value=mock_svc):
            result = run_async(get_api_key(key_id="u1"))

        mock_svc.get_api_key.assert_called_once_with("u1")
        assert result["data"]["uuid"] == "u1"
        assert result["data"]["name"] == "开发密钥"
        assert result["data"]["permissions_list"] == ["read"]
        assert result["data"]["is_active"] is True
        assert result["data"]["is_expired"] is False

    def test_get_not_found_raises_business_error(self):
        """service 返回 success=False → BusinessError。"""
        from api.settings import get_api_key

        mock_svc = MagicMock()
        mock_svc.get_api_key.return_value = {"success": False, "message": "API Key not found"}

        with patch("api.settings.get_api_key_service", return_value=mock_svc):
            with pytest.raises(BusinessError):
                run_async(get_api_key(key_id="ghost"))


class TestUpdateApiKeyCallsService:
    """#5459: PUT /api-keys/{key_id} 调 service.update_api_key，返回 {uuid}（对齐前端 updateApiKey）。"""

    def test_update_calls_service_and_returns_uuid(self):
        """#5459: update 转发 UpdateApiKeyRequest 字段到 service，返回 {uuid}。"""
        from api.settings import update_api_key, UpdateApiKeyRequest

        req = UpdateApiKeyRequest(name="新名称", is_active=False, expires_days=30)

        mock_svc = MagicMock()
        mock_svc.update_api_key.return_value = {
            "success": True,
            "message": "API Key updated successfully",
        }

        with patch("api.settings.get_api_key_service", return_value=mock_svc):
            result = run_async(update_api_key(key_id="u1", data=req))

        args, kwargs = mock_svc.update_api_key.call_args
        assert kwargs.get("uuid") == "u1"
        assert kwargs.get("name") == "新名称"
        assert kwargs.get("is_active") is False
        assert kwargs.get("expires_days") == 30
        # 前端 updateApiKey 期望 APIResponse<{uuid: string}>
        assert result["data"] == {"uuid": "u1"}

    def test_update_service_failure_raises_business_error(self):
        """service 返回 success=False → BusinessError。"""
        from api.settings import update_api_key, UpdateApiKeyRequest

        req = UpdateApiKeyRequest(name="x")
        mock_svc = MagicMock()
        mock_svc.update_api_key.return_value = {"success": False, "message": "API Key not found"}

        with patch("api.settings.get_api_key_service", return_value=mock_svc):
            with pytest.raises(BusinessError):
                run_async(update_api_key(key_id="ghost", data=req))


class TestRevealApiKeyPassesThrough:
    """#5459: POST /api-keys/{key_id}/reveal 透传 service.reveal_api_key（对齐前端 revealApiKey）。"""

    def test_reveal_passes_through_service_data(self):
        """#5459: reveal 透传 service.data，返回完整明文 key_value（用于复制）。"""
        from api.settings import reveal_api_key

        mock_svc = MagicMock()
        mock_svc.reveal_api_key.return_value = {
            "success": True,
            "data": {
                "uuid": "u1",
                "name": "开发密钥",
                "key_value": "ginkgo-abc1234567890",
            },
            "message": "success",
        }

        with patch("api.settings.get_api_key_service", return_value=mock_svc):
            result = run_async(reveal_api_key(key_id="u1"))

        mock_svc.reveal_api_key.assert_called_once_with("u1")
        assert result["data"]["uuid"] == "u1"
        assert result["data"]["name"] == "开发密钥"
        assert result["data"]["key_value"] == "ginkgo-abc1234567890"

    def test_reveal_not_found_raises_business_error(self):
        """service 返回 success=False → BusinessError。"""
        from api.settings import reveal_api_key

        mock_svc = MagicMock()
        mock_svc.reveal_api_key.return_value = {"success": False, "message": "API Key 不存在"}

        with patch("api.settings.get_api_key_service", return_value=mock_svc):
            with pytest.raises(BusinessError):
                run_async(reveal_api_key(key_id="ghost"))


class TestApiKeysRoutesRegistered:
    """#5459 启动冒烟：6 端点路由注册到 FastAPI app（覆盖应用启动路径，非仅纯函数导入）。

    防回归：端点装饰器丢失（如 @router.delete 被误删）会让路由静默不注册，
    纯函数测试无法捕获——必须 import app 验证路由表。
    """

    def test_all_six_api_keys_routes_registered_on_app(self):
        import sys
        from pathlib import Path

        # 顶层 main.py 遮蔽 api/main.py（预存仓库问题，test_api_versioning 同款 ImportError）；
        # 强制外层 api/ 到 sys.path 前端，使裸 `main` 解析到 api/main.py，覆盖应用启动路径。
        api_dir = str(Path(__file__).resolve().parents[2] / "api")
        if sys.path[:1] != [api_dir]:
            sys.path.insert(0, api_dir)
        from main import app

        routes = {
            (r.path, frozenset(r.methods))
            for r in app.routes
            if hasattr(r, "methods") and "/api-keys" in r.path
        }

        # 前端 apiKey.ts 调用的 6 个端点（prefix=/api/v1/settings 由 main.py include_router 注入）
        required = [
            ("/api/v1/settings/api-keys", "GET"),              # listApiKeys
            ("/api/v1/settings/api-keys", "POST"),             # createApiKey
            ("/api/v1/settings/api-keys/{key_id}", "GET"),     # getApiKey
            ("/api/v1/settings/api-keys/{key_id}", "PUT"),     # updateApiKey
            ("/api/v1/settings/api-keys/{key_id}", "DELETE"),  # deleteApiKey
            ("/api/v1/settings/api-keys/{key_id}/reveal", "POST"),  # revealApiKey
        ]
        missing = [f"{m} {p}" for p, m in required if not any(rp == p and m in rm for rp, rm in routes)]
        assert not missing, f"未注册的 api-keys 路由: {missing}"
