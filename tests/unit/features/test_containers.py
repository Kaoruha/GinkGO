"""Smoke tests for features.containers -- #3870"""
import pytest

try:
    from ginkgo.features.containers import FeatureContainer
    HAS_MODULE = True
except ImportError:
    HAS_MODULE = False


@pytest.mark.skipif(not HAS_MODULE, reason="FeatureContainer not available")
class TestFeatureContainer:
    def test_instantiation(self):
        container = FeatureContainer()
        assert container is not None

    def test_has_providers(self):
        container = FeatureContainer()
        assert hasattr(container, 'expression_parser')
        assert hasattr(container, 'expression_engine')
        assert hasattr(container, 'factor_engine')
