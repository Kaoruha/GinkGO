"""
TDD test for #5955: get_component_parameter_names() should skip framework 'name'.

Bug: Index 0 maps to 'name' (framework display name) instead of the first
business parameter. When CLI users pass --param '0:value', they intend to set
a business param like 'codes' or 'rsi_period', not the component name.

Root cause: _extract_via_ast_analysis_content and _extract_via_dynamic_import
skip 'self'/'args'/'kwargs' but intentionally keep 'name'.
"""
import pytest
from ginkgo.data.services.component_parameter_extractor import (
    get_component_parameter_names,
    ComponentParameterExtractor,
)


# Fake component source code simulating a typical strategy
_FAKE_STRATEGY_CODE = '''
from ginkgo.trading.bases.base_strategy import BaseStrategy

class FakeStrategy(BaseStrategy):
    """Test strategy with name + business params."""

    def __init__(self, name: str = "FakeStrategy", period: int = 14,
                 threshold: float = 0.5, **kwargs):
        super().__init__(name=name, **kwargs)
        self.period = period
        self.threshold = threshold
'''

_FAKE_SELECTOR_CODE = '''
from ginkgo.trading.bases.base_selector import BaseSelector

class FixedSelector(BaseSelector):
    """Selector with name + codes."""

    def __init__(self, name: str = "FixedSelector", codes=None, **kwargs):
        super().__init__(name=name, **kwargs)
        self.codes = codes or []
'''


@pytest.mark.unit
class TestParameterExtractionSkipsName:
    """参数提取应跳过框架参数 name"""

    def test_ast_content_skips_name_strategy(self):
        """策略参数索引 0 应为 period，不是 name"""
        result = get_component_parameter_names(
            "FakeStrategy",
            file_content=_FAKE_STRATEGY_CODE,
            component_type="strategy",
        )
        assert result is not None
        assert "name" not in result.values()
        # 索引 0 应为第一个业务参数
        assert result[0] == "period"
        assert result[1] == "threshold"

    def test_ast_content_skips_name_selector(self):
        """选择器参数索引 0 应为 codes，不是 name"""
        result = get_component_parameter_names(
            "FixedSelector",
            file_content=_FAKE_SELECTOR_CODE,
            component_type="selector",
        )
        assert result is not None
        assert "name" not in result.values()
        assert result[0] == "codes"

    def test_empty_params_when_only_name(self):
        """只有 name 一个参数时，应返回空映射"""
        code = '''
class SimpleStrategy:
    def __init__(self, name="Simple"):
        self.name = name
'''
        result = get_component_parameter_names(
            "SimpleStrategy",
            file_content=code,
            component_type="strategy",
        )
        assert result is not None
        assert len(result) == 0

    def test_parameter_count_excludes_name(self):
        """参数计数应排除 name"""
        result = get_component_parameter_names(
            "FakeStrategy",
            file_content=_FAKE_STRATEGY_CODE,
            component_type="strategy",
        )
        # period + threshold = 2 (not 3 with name)
        assert len(result) == 2

    def test_snake_case_component_name_matches_camel_case_class(self):
        """组件名来自文件名时，snake_case 也应匹配 CamelCase 类名。"""
        code = '''
class MovingAverageCrossover:
    def __init__(self, name="MovingAverageCrossover", short_period=20, long_period=60, **kwargs):
        self.short_period = short_period
        self.long_period = long_period
'''
        result = get_component_parameter_names(
            "moving_average_crossover",
            file_content=code,
            component_type="strategy",
        )
        assert result == {0: "short_period", 1: "long_period"}
