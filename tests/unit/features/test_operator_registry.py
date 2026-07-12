"""Smoke tests for features.engines.expression.registry + operators -- #3870"""
import pytest
import pandas as pd
import numpy as np

try:
    from ginkgo.features.engines.expression.registry import OperatorRegistry, register_operator
    HAS_REGISTRY = True
except ImportError:
    HAS_REGISTRY = False

if HAS_REGISTRY:
    # 触发 operators 包加载,注册全部算子。
    # Rank/Mean 等住 operators 包(statistical),非 registry.py 内建;
    # 不触发则 test_has_builtin_operators 看不到 Rank。
    import ginkgo.features.engines.expression.operators  # noqa: F401


@pytest.fixture
def sample_df():
    return pd.DataFrame({
        'close': [10.0, 11.0, 12.0, 13.0, 14.0, 15.0, 16.0, 17.0, 18.0, 19.0],
        'open': [9.5, 10.5, 11.5, 12.5, 13.5, 14.5, 15.5, 16.5, 17.5, 18.5],
        'high': [10.5, 11.5, 12.5, 13.5, 14.5, 15.5, 16.5, 17.5, 18.5, 19.5],
        'low': [9.0, 10.0, 11.0, 12.0, 13.0, 14.0, 15.0, 16.0, 17.0, 18.0],
        'volume': [1000.0] * 10,
    })


@pytest.mark.skipif(not HAS_REGISTRY, reason="OperatorRegistry not available")
class TestOperatorRegistry:
    def test_has_builtin_operators(self):
        ops = OperatorRegistry.get_available_operators()
        assert isinstance(ops, list)
        assert len(ops) > 0
        # Check some expected builtins
        for name in ['Mean', 'Std', 'Rank', 'Abs', 'Sum', 'Delta', 'Ref']:
            assert name in ops, f"Missing builtin operator: {name}"

    def test_is_registered(self):
        assert OperatorRegistry.is_registered('Mean') is True
        assert OperatorRegistry.is_registered('NONEXISTENT_XYZ') is False

    def test_get_operator_info(self):
        info = OperatorRegistry.get_operator_info('Mean')
        assert isinstance(info, dict)

    def test_register_custom(self):
        def custom_op(data, x):
            return x * 2
        OperatorRegistry.register("test_custom_op_xyz", custom_op, description="test")
        assert OperatorRegistry.is_registered("test_custom_op_xyz")
        OperatorRegistry.unregister("test_custom_op_xyz")
        assert not OperatorRegistry.is_registered("test_custom_op_xyz")

    def test_validate_function_call(self):
        assert OperatorRegistry.validate_function_call('Mean', 2) is True

    def test_duplicate_registration_raises(self):
        """同名重注册必须 raise,禁止静默覆盖(#6479 回归)。"""
        def op_a(data, x):
            return x

        def op_b(data, x):
            return x * 2

        name = "test_dup_op_xyz_6479"
        OperatorRegistry.register(name, op_a, description="first")
        try:
            with pytest.raises(ValueError, match="already registered"):
                OperatorRegistry.register(name, op_b, description="second")
        finally:
            OperatorRegistry.unregister(name)

    def test_rank_is_rolling_two_arg(self):
        """Rank 是滚动排名(2参, statistical),非被覆盖删除的截面版(#6479 回归)。"""
        assert OperatorRegistry.is_registered('Rank')
        info = OperatorRegistry.get_operator_info('Rank')
        assert info['min_args'] == 2
        assert info['max_args'] == 2
        assert OperatorRegistry._operators['Rank'].__module__.endswith('statistical')


# Test operator modules actually load and register their functions
@pytest.mark.skipif(not HAS_REGISTRY, reason="OperatorRegistry not available")
class TestOperatorModules:
    def test_basic_operators_loaded(self):
        try:
            import ginkgo.features.engines.expression.operators.basic as basic_mod
            assert basic_mod is not None
        except ImportError:
            pytest.skip("basic operators not available")

        # Check some basic operators exist
        for name in ['Pow', 'Sqrt', 'Abs', 'Sign', 'Add', 'Subtract', 'Multiply', 'Divide']:
            assert OperatorRegistry.is_registered(name), f"Basic operator {name} not registered"

    def test_statistical_operators_loaded(self):
        try:
            import ginkgo.features.engines.expression.operators.statistical
        except ImportError:
            pytest.skip("statistical operators not available")

        for name in ['Variance', 'Skew', 'Kurt', 'Median', 'Zscore', 'Corr']:
            assert OperatorRegistry.is_registered(name), f"Statistical operator {name} not registered"

    def test_technical_operators_loaded(self):
        try:
            import ginkgo.features.engines.expression.operators.technical
        except ImportError:
            pytest.skip("technical operators not available")

        for name in ['RSI', 'MACD', 'BB_upper', 'BB_lower', 'ATR', 'Stoch']:
            assert OperatorRegistry.is_registered(name), f"Technical operator {name} not registered"

    def test_temporal_operators_loaded(self):
        try:
            import ginkgo.features.engines.expression.operators.temporal
        except ImportError:
            pytest.skip("temporal operators not available")

        for name in ['Returns', 'LogReturns', 'CumSum', 'CumProd', 'Delay', 'Ts_Rank']:
            assert OperatorRegistry.is_registered(name), f"Temporal operator {name} not registered"


@pytest.mark.skipif(not HAS_REGISTRY, reason="OperatorRegistry not available")
class TestBasicOperatorExecution:
    def test_add(self, sample_df):
        close = sample_df['close']
        open_ = sample_df['open']
        result = OperatorRegistry.execute_function('Add', [close, open_], sample_df)
        assert isinstance(result, pd.Series)
        assert len(result) == 10

    def test_subtract(self, sample_df):
        close = sample_df['close']
        open_ = sample_df['open']
        result = OperatorRegistry.execute_function('Subtract', [close, open_], sample_df)
        assert isinstance(result, pd.Series)

    def test_abs(self, sample_df):
        result = OperatorRegistry.execute_function('Abs', [sample_df['close']], sample_df)
        assert isinstance(result, pd.Series)
        assert (result >= 0).all()
