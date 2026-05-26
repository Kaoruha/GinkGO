"""Smoke test for ApiKeyService -- #3823"""
import pytest
from unittest.mock import MagicMock, patch

try:
    from ginkgo.data.services.api_key_service import ApiKeyService
    HAS_MODULE = True
except ImportError:
    HAS_MODULE = False


@pytest.mark.skipif(not HAS_MODULE, reason="ginkgo.data.services.api_key_service not importable")
class TestApiKeyServiceSmoke:
    """冒烟测试：验证可实例化和公开方法可调用"""

    def _make_svc(self):
        with patch("ginkgo.data.services.api_key_service.ApiKeyCRUD"):
            svc = ApiKeyService()
        return svc, svc.crud

    def test_instantiation(self):
        with patch("ginkgo.data.services.api_key_service.ApiKeyCRUD"):
            svc = ApiKeyService()
        assert svc is not None

    def test_create_api_key_callable(self):
        svc, mock_crud = self._make_svc()
        mock_crud.create_api_key.return_value = MagicMock(
            uuid="u1", name="k1", key_prefix="gk",
            permissions="read", expires_at=None, is_active=True,
            user_id=None,
        )
        result = svc.create_api_key(name="test_key")
        assert result is not None
        assert isinstance(result, dict)

    def test_get_api_key_callable(self):
        svc, mock_crud = self._make_svc()
        mock_key = MagicMock(
            uuid="u1", name="k1", key_prefix="gk",
            permissions="read", expires_at=None, is_active=True,
            last_used_at=None, description=None, create_at=MagicMock(
                isoformat=lambda: "2025-01-01"
            ),
            user_id=None,
        )
        mock_key.get_permissions_list.return_value = ["read"]
        mock_key.is_expired.return_value = False
        mock_crud.get_api_key_by_uuid.return_value = mock_key
        result = svc.get_api_key(uuid="u1")
        assert result is not None
        assert isinstance(result, dict)

    def test_list_api_keys_callable(self):
        svc, mock_crud = self._make_svc()
        mock_crud.get_all_api_keys.return_value = {"items": []}
        result = svc.list_api_keys()
        assert result is not None
        assert isinstance(result, dict)

    def test_verify_api_key_callable(self):
        svc, mock_crud = self._make_svc()
        mock_crud.verify_api_key.return_value = None
        result = svc.verify_api_key(key_value="ginkgo-test")
        assert result is None  # no key found returns None
