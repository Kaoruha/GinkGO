"""Smoke test for ComponentParameterExtractor -- #3823"""
import pytest
from unittest.mock import MagicMock, patch

try:
    from ginkgo.data.services.component_parameter_extractor import ComponentParameterExtractor
    HAS_MODULE = True
except ImportError:
    HAS_MODULE = False


@pytest.mark.skipif(not HAS_MODULE, reason="ginkgo.data.services.component_parameter_extractor not importable")
class TestComponentParameterExtractorSmoke:
    """冒烟测试：验证可实例化和公开方法可调用"""

    def test_instantiation(self):
        ext = ComponentParameterExtractor()
        assert ext is not None

    def test_extract_component_parameters_callable(self):
        ext = ComponentParameterExtractor()
        result = ext.extract_component_parameters("nonexistent_component")
        assert isinstance(result, dict)

    def test_extract_component_parameters_with_content(self):
        """传入源码内容时通过 AST 解析参数"""
        ext = ComponentParameterExtractor()
        source = '''
class FixedSelector:
    def __init__(self, name, codes):
        self.name = name
        self.codes = codes
'''
        result = ext.extract_component_parameters(
            component_name="fixed_selector", file_content=source,
        )
        assert isinstance(result, dict)
        assert 0 in result
        assert result[0] == "name"
        assert result[1] == "codes"

    def test_get_parameter_info_callable(self):
        ext = ComponentParameterExtractor()
        result = ext.get_parameter_info("nonexistent", param_index=0)
        assert isinstance(result, str)

    def test_clear_cache_callable(self):
        ext = ComponentParameterExtractor()
        ext._component_cache["test_key"] = {"dummy": True}
        ext.clear_cache()
        assert len(ext._component_cache) == 0
