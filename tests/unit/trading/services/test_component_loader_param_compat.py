"""
TDD test for #5974: component_loader parameter index backward compatibility.

Bug: After #5955 (skipping 'name' in param extraction), old portfolios that
stored params with indices 1,2,3... (where 0=name) can't be correctly mapped
to the new param_names {0:"codes", 1:"period"} (where name is excluded).

Root cause: get_component_parameter_names() now skips 'name', shifting indices.
Old DB records still use the pre-shift indices.

Fix: component_loader must detect old-style indices and apply a shift.
"""
import pytest
from ginkgo.trading.services._assembly.component_loader import resolve_param_kwargs


@pytest.mark.unit
class TestParamIndexBackwardCompat:
    """参数索引向后兼容性测试"""

    def test_new_style_indices_match_directly(self):
        """新组合：索引 0 直接匹配 param_names"""
        param_names = {0: "codes", 1: "period"}
        result = resolve_param_kwargs(
            component_params=['"000001.SH"', 14],
            param_indices=[0, 1],
            param_names=param_names,
        )
        assert result == {"codes": '"000001.SH"', "period": 14}

    def test_old_style_indices_shifted_by_one(self):
        """旧组合：索引 1,2 需要减 1 匹配 param_names（因为 name 曾在 0）"""
        param_names = {0: "codes", 1: "period"}
        result = resolve_param_kwargs(
            component_params=['"000001.SH"', 14],
            param_indices=[1, 2],
            param_names=param_names,
        )
        assert result == {"codes": '"000001.SH"', "period": 14}

    def test_old_style_single_param(self):
        """旧组合只绑定了 1 个参数：索引 1 → 应映射到 param_names[0]"""
        param_names = {0: "codes"}
        result = resolve_param_kwargs(
            component_params=['"000001.SH"'],
            param_indices=[1],
            param_names=param_names,
        )
        assert result == {"codes": '"000001.SH"'}

    def test_empty_params_returns_empty(self):
        """无参数时返回空 dict"""
        result = resolve_param_kwargs(
            component_params=[],
            param_indices=[],
            param_names={0: "codes"},
        )
        assert result == {}

    def test_unknown_index_skipped(self):
        """索引不在 param_names 中应跳过，不崩溃"""
        param_names = {0: "codes"}
        result = resolve_param_kwargs(
            component_params=["value"],
            param_indices=[99],
            param_names=param_names,
        )
        # 99 不在 param_names，99-1=98 也不在 → 空
        assert result == {}

    def test_new_style_partial_params(self):
        """新组合只绑定了第二个参数：索引 1 → period"""
        param_names = {0: "codes", 1: "period"}
        result = resolve_param_kwargs(
            component_params=[14],
            param_indices=[1],
            param_names=param_names,
        )
        assert result == {"period": 14}

    def test_old_style_strategy_with_threshold(self):
        """旧组合：策略有 3 个业务参数，索引 1,2,3"""
        param_names = {0: "codes", 1: "period", 2: "threshold"}
        result = resolve_param_kwargs(
            component_params=['"000001.SH"', 20, 0.8],
            param_indices=[1, 2, 3],
            param_names=param_names,
        )
        assert result == {"codes": '"000001.SH"', "period": 20, "threshold": 0.8}

    def test_old_style_indices_prefer_shifted_mapping_on_tie(self):
        """旧组合 [1,2] 与新索引都能“匹配”时，应优先选择偏移后的业务参数。"""
        param_names = {0: "short_period", 1: "long_period", 2: "frequency"}
        result = resolve_param_kwargs(
            component_params=[5, 20],
            param_indices=[1, 2],
            param_names=param_names,
        )
        assert result == {"short_period": 5, "long_period": 20}
