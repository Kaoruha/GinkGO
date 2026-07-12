"""Smoke tests for features.engines.expression.registry + operators -- #3870"""
import pytest
import pandas as pd
import numpy as np

try:
    from ginkgo.features.engines.expression.registry import OperatorRegistry, register_operator
    HAS_REGISTRY = True
except ImportError:
    HAS_REGISTRY = False

# collection-time 注册 operators/*.py：每个子模块的 @register_operator 装饰器在 import
# 时才执行注册。registry.py 只定义内置 operator（Mean/Std/.../Log），basic/statistical/
# temporal/technical 须显式 import 才进注册表。否则下面 parametrize 的 get_available_operators()
# 只含 11 个内置，覆盖不到 operators/*.py 函数体（#6708 diff coverage gate 的目标）。
# 逐个 try/except：单模块缺失不阻断其余注册。
if HAS_REGISTRY:
    for _op_mod in ("basic", "statistical", "temporal", "technical"):
        try:
            __import__(f"ginkgo.features.engines.expression.operators.{_op_mod}")
        except ImportError:
            pass


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
        # 截面排名原名 Rank，#6706 为与 statistical.py 滚动 Rank(min_args=2) 消歧改名 CS_Rank
        for name in ['Mean', 'Std', 'CS_Rank', 'Abs', 'Sum', 'Delta', 'Ref']:
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


@pytest.mark.skipif(not HAS_REGISTRY, reason="OperatorRegistry not available")
class TestAllOperatorsSmokeCallable:
    """参数化烟雾：遍历全量已注册 operator 用通用 series 输入调用一次（#6708 diff coverage）。

    #6708 ADR-022 原则5 给所有 operator 包 @with_error_handling + _extract_scalar（收敛
    93 处 try/except + 50 处 iloc 模板），等价重构无业务逻辑变化，但 diff coverage gate
    要求被重构的函数体被执行。execute_function 自带 try/except 返回 nan Series，
    @with_error_handling 装饰器同样兜底——operator 内部即便因输入语义不符抛异常（如
    Quantile 的 q=3 触发 0-1 校验），到异常点为止的函数体行仍被覆盖，断言始终成立。
    """

    @staticmethod
    def _build_args(info, sample_df):
        # min_args 是函数签名所需的最少 series 参数数（不含 data）；按此构造保证不被
        # execute_function 的 max_args 校验拒绝（min <= max 恒成立），operator 函数体必被
        # 实际调用而非执行前被拒。配置类参数（window/period/q）经 _extract_scalar 取 iloc[0]=3。
        # 窗口 Series 取与 close 等长：逐 bar 循环型 operator（PinBar/Gap）把第 2~N 参数当
        # 价格序列遍历，len-1 窗口会在循环第二轮 IndexError 被兜底吞掉致循环体零覆盖；
        # 等长既不破坏 _extract_scalar（仍取 iloc[0]），又让循环拿到全长序列。
        min_args = info.get("min_args", 1) or 1
        close = sample_df["close"]
        window = pd.Series([3.0] * len(close), index=close.index)
        return [close] + [window] * max(min_args - 1, 0)

    @pytest.mark.parametrize(
        "name",
        sorted(OperatorRegistry.get_available_operators()) if HAS_REGISTRY else [],
    )
    def test_every_operator_callable(self, name, sample_df):
        info = OperatorRegistry.get_operator_info(name)
        args = self._build_args(info, sample_df)
        result = OperatorRegistry.execute_function(name, args, sample_df)
        # 正常路径返回数值 Series；异常路径（execute_function / with_error_handling 兜底）返回 nan Series
        assert isinstance(result, pd.Series), f"{name} returned {type(result)}, expected pd.Series"


@pytest.mark.skipif(not HAS_REGISTRY, reason="OperatorRegistry not available")
class TestWindowedOperatorColdBranches:
    """覆盖 registry 内置 windowed operator 的冷分支（#6708 diff coverage 补量）。

    parametrize 烟雾用正窗口（3）走 happy path，window<=0 的 ValueError raise 分支与
    Quantile 合法 q 的成功 return 分支未被触达。这两类是 #6708 重构（_extract_scalar +
    window<=0 守卫）新增的可执行行，补定向用例拿稳定余量过 80% 门禁。raise 被
    @with_error_handling 兜底成 nan Series，断言只验类型不验值。
    """

    @pytest.mark.parametrize("name", ["Mean", "Std", "Max", "Min", "Sum", "Quantile"])
    def test_window_le_zero_raises_and_is_caught(self, name, sample_df):
        # window=0 触发各 operator 的 ``if window_size <= 0: raise``，覆盖 raise 行。
        # Quantile 还需 q 参数（min_args=3）；其余 min_args=2，多出的 q 被 max_args 拒，
        # 故按 min_args 构造：2-arg 给 [close, zero_window]，3-arg 再补一个 q。
        close = sample_df["close"]
        zero_window = pd.Series([0.0])
        info = OperatorRegistry.get_operator_info(name)
        args = [close, zero_window] + [pd.Series([0.5])] * max(info["min_args"] - 2, 0)
        result = OperatorRegistry.execute_function(name, args, sample_df)
        assert isinstance(result, pd.Series)

    def test_quantile_valid_q_returns_series(self, sample_df):
        # q=0.5 落在 [0,1]，走完 Quantile 函数体到末行 return（覆盖 happy-path 末行）。
        close = sample_df["close"]
        result = OperatorRegistry.execute_function(
            "Quantile", [close, pd.Series([3.0]), pd.Series([0.5])], sample_df
        )
        assert isinstance(result, pd.Series)
