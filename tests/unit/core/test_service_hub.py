# Tests for ServiceHub observability (issues #4609, #3868, #3871)
import pytest
from unittest.mock import patch, MagicMock

from ginkgo.service_hub import ServiceHub, _MODULE_REGISTRY


class TestServiceHubLoadModuleReturnsNoneOnError:
    """_load_module should return None and log error when import fails."""

    def test_load_module_returns_none_on_bad_import(self):
        hub = ServiceHub()
        with patch.dict(_MODULE_REGISTRY, {"bad": ("nonexistent.module.path", "attr", None)}):
            result = hub._load_module("bad")
            assert result is None

    def test_load_module_records_error_on_failure(self):
        hub = ServiceHub()
        with patch.dict(_MODULE_REGISTRY, {"bad": ("nonexistent.module.path", "attr", None)}):
            hub._load_module("bad")
        assert "bad" in hub._module_errors

    def test_getattr_raises_on_missing_module(self):
        hub = ServiceHub()
        with pytest.raises(AttributeError, match="no module"):
            hub.nonexistent_module

    def test_successful_load_returns_container(self):
        hub = ServiceHub()
        mock_module = MagicMock()
        mock_container = MagicMock()
        mock_module.container = mock_container

        with patch.dict(_MODULE_REGISTRY, {"test_mod": ("fake.path", "container", None)}):
            with patch("builtins.__import__", return_value=mock_module):
                result = hub._load_module("test_mod")
                assert result is mock_container

    def test_successful_load_caches_result(self):
        hub = ServiceHub()
        mock_module = MagicMock()
        mock_module.container = MagicMock()

        with patch.dict(_MODULE_REGISTRY, {"test_mod": ("fake.path", "container", None)}):
            with patch("builtins.__import__", return_value=mock_module) as mock_import:
                # Access through __getattr__ (public interface)
                result1 = hub.test_mod
                import_count = mock_import.call_count
                result2 = hub.test_mod
                # Second call hits cache, no new import
                assert mock_import.call_count == import_count
                assert result1 is result2


class TestServiceHubLegacyAliasesRemoved:
    """DataService/ManagementService/BusinessService aliases should not exist."""

    def test_data_service_alias_removed(self):
        from ginkgo.data.services.base_service import BaseService
        assert not hasattr(BaseService, "__name__") or BaseService.__name__ == "BaseService"
        # The module should not export legacy aliases
        import ginkgo.data.services as svc_mod
        # These names should NOT be legacy aliases pointing to BaseService
        # (They may not exist at all after cleanup)
        for name in ("DataService", "ManagementService", "BusinessService"):
            if hasattr(svc_mod, name):
                # If it still exists, it must not just be BaseService
                assert getattr(svc_mod, name) is not BaseService, \
                    f"{name} should be removed, not aliased to BaseService"
