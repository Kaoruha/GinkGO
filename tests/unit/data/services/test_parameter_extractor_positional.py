"""
ADR-020: 参数提取器镜像构造函数签名（含 name）。

旧契约（#5955）：提取器跳过 name，假装 index0 = 首个业务参数；装配端再用
打分启发式（resolve_param_kwargs）猜新旧组合 → #6481 崩溃链。
新契约（ADR-020）：提取器原样镜像构造器（name 留在 index0），装配纯位置
splat，提取器只服务 API/UI 展示，两类 bug 物理隔离。

回归保护：禁止重新引入 name-skip。
"""
import pytest
from ginkgo.data.services.component_parameter_extractor import (
    get_component_parameter_names,
    ComponentParameterExtractor,
)


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
class TestParameterExtractionMirrorsConstructor:
    """ADR-020: 提取器镜像构造函数签名，name 保留在 index0"""

    def test_strategy_keeps_name_at_index0(self):
        """策略：index0=name, 1=period, 2=threshold（与构造器位置 1:1）"""
        result = get_component_parameter_names(
            "FakeStrategy",
            file_content=_FAKE_STRATEGY_CODE,
            component_type="strategy",
        )
        assert result == {0: "name", 1: "period", 2: "threshold"}

    def test_selector_keeps_name_at_index0(self):
        """选择器：index0=name, 1=codes"""
        result = get_component_parameter_names(
            "FixedSelector",
            file_content=_FAKE_SELECTOR_CODE,
            component_type="selector",
        )
        assert result == {0: "name", 1: "codes"}

    def test_single_name_constructor_returns_name_only(self):
        """只有 name 一个参数时返回 {0: 'name'}（非空映射）"""
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
        assert result == {0: "name"}

    def test_name_in_values(self):
        """name 必须出现在提取结果中（回归：#5955 曾跳过 name）"""
        result = get_component_parameter_names(
            "FakeStrategy",
            file_content=_FAKE_STRATEGY_CODE,
            component_type="strategy",
        )
        assert "name" in result.values()

    def test_snake_case_component_name_matches_camel_case_class(self):
        """组件名 snake_case 匹配 CamelCase 类名；name 仍在 index0"""
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
        assert result == {0: "name", 1: "short_period", 2: "long_period"}
