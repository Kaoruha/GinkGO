"""OperatorRegistry 注册冲突检测 + Rank 截面/滚动语义测试 -- #6706 (ADR-022 原则4)"""
import pytest
import pandas as pd
import numpy as np

from ginkgo.features.engines.expression.registry import (
    OperatorRegistry,
    register_operator,
)
# 触发所有 operator 模块导入注册（basic/statistical/temporal/technical）
import ginkgo.features.engines.expression.operators  # noqa: F401


@pytest.fixture(autouse=True)
def _cleanup_test_operators():
    """每个测试后清理 _test_ 前缀的临时 operator，防全局类变量注册表污染"""
    yield
    for name in list(OperatorRegistry.get_available_operators()):
        if name.startswith("_test_"):
            OperatorRegistry.unregister(name)


class TestRegisterOverrideGuard:
    """ADR-022 原则4：注册冲突检测"""

    def test_register_same_name_raises_by_default(self):
        """同名注册（默认 override=False）应 raise ValueError，而非静默覆盖"""
        OperatorRegistry.register("_test_dup", lambda data, x: x, min_args=1, max_args=1)
        with pytest.raises(ValueError, match="already registered"):
            OperatorRegistry.register(
                "_test_dup", lambda data, x: x * 2, min_args=1, max_args=1
            )

    def test_register_override_true_allows_replacement(self):
        """override=True 显式允许覆盖"""
        first = lambda data, x: x  # noqa: E731
        second = lambda data, x: x * 2  # noqa: E731
        OperatorRegistry.register("_test_ovr", first, min_args=1, max_args=1)
        # 不 raise，覆盖成功
        OperatorRegistry.register(
            "_test_ovr", second, min_args=1, max_args=1, override=True
        )
        assert OperatorRegistry.is_registered("_test_ovr")

    def test_register_operator_decorator_propagates_override(self):
        """装饰器透传 override 参数"""
        @register_operator("_test_dec", min_args=1, max_args=1)
        def op_v1(data, x):
            return x

        # 默认同名 raise
        with pytest.raises(ValueError):
            @register_operator("_test_dec", min_args=1, max_args=1)
            def op_v2(data, x):
                return x * 2

        # override=True 允许
        @register_operator("_test_dec", min_args=1, max_args=1, override=True)
        def op_v3(data, x):
            return x * 3


class TestRankSemanticsDisambiguated:
    """Rank 截面版(CS_Rank) 与滚动版(Rank) 改名消歧后应共存各司其职"""

    def test_cs_rank_cross_sectional_single_arg(self):
        """CS_Rank 单参 = 截面排名（alpha101 的 Rank($close) 语义）"""
        data = pd.DataFrame({"close": [14.0, 10.0, 12.0, 13.0, 11.0]})
        series = data["close"]
        result = OperatorRegistry.execute_function("CS_Rank", [series], data)
        # 截面排名 method='min'：10→1, 11→2, 12→3, 13→4, 14→5
        assert list(result) == [5.0, 1.0, 3.0, 4.0, 2.0]

    def test_rank_rolling_double_arg(self):
        """Rank 双参 = 滚动排名（statistical.py 滚动版保留 Rank 名）"""
        data = pd.DataFrame({"close": [10.0, 11.0, 12.0, 13.0, 14.0]})
        series = data["close"]
        window = pd.Series([3.0])
        result = OperatorRegistry.execute_function("Rank", [series, window], data)
        # 滚动 rank 不应全 nan（min_args=2 校验通过 + 滚动计算正常）
        assert not result.isna().all()
        assert len(result) == 5

    def test_cs_rank_and_rank_both_registered_distinct(self):
        """CS_Rank 与 Rank 同时注册，元数据各不相同（截面 min1 / 滚动 min2）"""
        assert OperatorRegistry.is_registered("CS_Rank")
        assert OperatorRegistry.is_registered("Rank")
        cs_meta = OperatorRegistry.get_operator_info("CS_Rank")
        roll_meta = OperatorRegistry.get_operator_info("Rank")
        assert cs_meta["min_args"] == 1
        assert roll_meta["min_args"] == 2


class TestWithErrorHandling:
    """ADR-022 原则5：@with_error_handling 装饰器收敛 operator 异常兜底"""

    def test_normal_return_passes_through(self):
        from ginkgo.features.engines.expression.registry import with_error_handling

        @with_error_handling()
        def op(data, series):
            return series * 2

        result = op(None, pd.Series([1.0, 2.0, 3.0]))
        assert list(result) == [2.0, 4.0, 6.0]

    def test_exception_returns_nan_series_aligned_to_series(self):
        from ginkgo.features.engines.expression.registry import with_error_handling

        idx = pd.Index([10, 11, 12])

        @with_error_handling()
        def op(data, series):
            raise ValueError("boom")

        result = op(None, pd.Series([1.0, 2.0, 3.0], index=idx))
        assert len(result) == 3
        assert result.isna().all()
        assert list(result.index) == [10, 11, 12]

    def test_exception_fallback_first_series_arg(self):
        from ginkgo.features.engines.expression.registry import with_error_handling

        @with_error_handling()
        def op(data, x, y):
            raise RuntimeError("x")

        result = op(None, pd.Series([1.0, 2.0]), pd.Series([3.0]))
        assert len(result) == 2
        assert result.isna().all()


class TestExtractScalar:
    """ADR-022 原则5：_extract_scalar 收敛 50 处 iloc[0] if len>0 else 模板"""

    def test_non_empty_returns_first_cast_to_int(self):
        from ginkgo.features.engines.expression.registry import _extract_scalar
        assert _extract_scalar(pd.Series([5.0, 9.0, 3.0]), 20) == 5

    def test_non_empty_float_cast(self):
        from ginkgo.features.engines.expression.registry import _extract_scalar
        assert _extract_scalar(pd.Series([0.5]), 0.5, cast=float) == 0.5

    def test_empty_returns_default(self):
        from ginkgo.features.engines.expression.registry import _extract_scalar
        assert _extract_scalar(pd.Series([]), 14) == 14
        assert _extract_scalar(pd.Series([]), 0.618, cast=float) == 0.618
