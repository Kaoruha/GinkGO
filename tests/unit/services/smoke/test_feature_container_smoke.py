"""Smoke test for FeatureContainer -- #3823"""
import pytest
from unittest.mock import MagicMock, patch

try:
    from ginkgo.features.containers import FeatureContainer
    HAS_MODULE = True
except ImportError:
    HAS_MODULE = False


@pytest.mark.skipif(not HAS_MODULE, reason="ginkgo.features.containers not importable")
class TestFeatureContainerSmoke:
    """冒烟测试：验证可实例化和公开方法可调用"""

    def _make_svc(self):
        with patch("ginkgo.features.containers.auto_discover_factor_libraries", return_value={}):
            with patch("ginkgo.features.containers.factor_registry") as mock_reg:
                mock_reg.get_library_metadata.return_value = {}
                mock_reg.validate_libraries.return_value = {}
                svc = FeatureContainer()
        return svc, mock_reg

    def test_instantiation(self):
        svc, _ = self._make_svc()
        assert svc is not None

    def test_reload_definitions_callable(self):
        svc, _ = self._make_svc()
        with patch("ginkgo.features.containers.auto_discover_factor_libraries", return_value={}):
            svc.reload_definitions()

    def test_get_registered_libraries_callable(self):
        svc, mock_reg = self._make_svc()
        mock_reg.get_library_metadata.return_value = {"lib_a": {"name": "Alpha"}}
        result = svc.get_registered_libraries()
        assert isinstance(result, dict)

    def test_validate_definitions_callable(self):
        svc, mock_reg = self._make_svc()
        mock_reg.validate_libraries.return_value = {"lib_a": []}
        result = svc.validate_definitions()
        assert isinstance(result, dict)
