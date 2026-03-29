# Upstream: ginkgo.validation.monte_carlo
# Downstream: pytest
# Role: MonteCarloSimulator 测试

"""
MonteCarloSimulator 测试

TDD Green 阶段: 测试用例实现
"""

import pytest
from decimal import Decimal
import pandas as pd
import numpy as np
from datetime import datetime, timedelta


@pytest.fixture
def sample_returns():
    """创建示例收益序列"""
    np.random.seed(42)
    # 生成 252 个交易日的收益率
    returns = np.random.randn(252) * 0.02  # 日波动率 2%
    return returns


@pytest.fixture
def sample_returns_dataframe(sample_returns):
    """创建示例 DataFrame 格式收益"""
    dates = pd.date_range("2023-01-01", periods=252, freq="B")
    return pd.DataFrame({
        "date": dates,
        "return": sample_returns,
    })


@pytest.mark.unit
class TestMonteCarloResult:
    """MonteCarloResult 测试"""

    def test_init(self):
        """测试初始化"""
        from ginkgo.validation.models import MonteCarloResult

        result = MonteCarloResult(
            n_simulations=10000,
            confidence_level=0.95,
        )

        assert result.n_simulations == 10000
        assert result.confidence_level == 0.95

    def test_var_calculation(self):
        """测试 VaR 计算"""
        from ginkgo.validation.models import MonteCarloResult

        result = MonteCarloResult(
            n_simulations=10000,
            confidence_level=0.95,
            var=-0.05,
        )

        assert result.var == -0.05

    def test_cvar_calculation(self):
        """测试 CVaR 计算"""
        from ginkgo.validation.models import MonteCarloResult

        result = MonteCarloResult(
            n_simulations=10000,
            confidence_level=0.95,
            var=-0.05,
            cvar=-0.08,
        )

        # CVaR 通常比 VaR 更保守 (绝对值更大)
        assert result.cvar < result.var  # 负数，所以 <

    def test_to_dict(self):
        """测试序列化"""
        from ginkgo.validation.models import MonteCarloResult

        result = MonteCarloResult(
            n_simulations=10000,
            confidence_level=0.95,
            mean=0.001,
            std=0.02,
            var=-0.05,
            cvar=-0.08,
        )

        d = result.to_dict()
        assert d["n_simulations"] == 10000
        assert "var" in d
        assert "cvar" in d


@pytest.mark.unit
class TestMonteCarloSimulator:
    """MonteCarloSimulator 测试"""

    def test_init_with_array(self, sample_returns):
        """测试用数组初始化"""
        from ginkgo.validation.monte_carlo import MonteCarloSimulator

        simulator = MonteCarloSimulator(
            returns=sample_returns,
            n_simulations=1000,
        )

        assert simulator is not None
        assert simulator.n_simulations == 1000

    def test_init_with_dataframe(self, sample_returns_dataframe):
        """测试用 DataFrame 初始化"""
        from ginkgo.validation.monte_carlo import MonteCarloSimulator

        simulator = MonteCarloSimulator(
            returns=sample_returns_dataframe,
            n_simulations=1000,
            return_col="return",
        )

        assert simulator is not None

    def test_run(self, sample_returns):
        """测试运行模拟"""
        from ginkgo.validation.monte_carlo import MonteCarloSimulator

        simulator = MonteCarloSimulator(
            returns=sample_returns,
            n_simulations=1000,
        )

        result = simulator.run()

        assert result is not None
        assert result.n_simulations == 1000
        assert result.mean is not None
        assert result.std is not None

    def test_calculate_var(self, sample_returns):
        """测试 VaR 计算"""
        from ginkgo.validation.monte_carlo import MonteCarloSimulator

        simulator = MonteCarloSimulator(
            returns=sample_returns,
            n_simulations=10000,
        )

        result = simulator.run()
        var_95 = result.var

        # VaR 应该是负数 (损失)
        assert var_95 < 0

    def test_calculate_cvar(self, sample_returns):
        """测试 CVaR 计算"""
        from ginkgo.validation.monte_carlo import MonteCarloSimulator

        simulator = MonteCarloSimulator(
            returns=sample_returns,
            n_simulations=10000,
        )

        result = simulator.run()

        # CVaR 通常比 VaR 更保守
        assert result.cvar < result.var

    def test_different_confidence_levels(self, sample_returns):
        """测试不同置信水平"""
        from ginkgo.validation.monte_carlo import MonteCarloSimulator

        simulator_95 = MonteCarloSimulator(
            returns=sample_returns,
            n_simulations=10000,
            confidence_level=0.95,
        )

        simulator_99 = MonteCarloSimulator(
            returns=sample_returns,
            n_simulations=10000,
            confidence_level=0.99,
        )

        result_95 = simulator_95.run()
        result_99 = simulator_99.run()

        # 99% 置信水平的 VaR 应该更保守 (绝对值更大)
        assert result_99.var < result_95.var

    def test_percentiles(self, sample_returns):
        """测试分位数计算"""
        from ginkgo.validation.monte_carlo import MonteCarloSimulator

        simulator = MonteCarloSimulator(
            returns=sample_returns,
            n_simulations=10000,
        )

        result = simulator.run()

        # 应该有多个分位数
        assert result.percentiles is not None
        assert 5 in result.percentiles or "p5" in result.percentiles

    def test_get_simulation_paths(self, sample_returns):
        """测试获取模拟路径"""
        from ginkgo.validation.monte_carlo import MonteCarloSimulator

        simulator = MonteCarloSimulator(
            returns=sample_returns,
            n_simulations=100,
            time_horizon=30,
        )

        result = simulator.run()

        # 如果存储路径，检查形状
        if hasattr(result, 'paths') and result.paths is not None:
            assert len(result.paths) == 100

    def test_custom_time_horizon(self, sample_returns):
        """测试自定义时间范围"""
        from ginkgo.validation.monte_carlo import MonteCarloSimulator

        simulator = MonteCarloSimulator(
            returns=sample_returns,
            n_simulations=1000,
            time_horizon=63,  # 约 3 个月
        )

        result = simulator.run()

        assert result.time_horizon == 63

    def test_seed_reproducibility(self, sample_returns):
        """测试种子可重现性"""
        from ginkgo.validation.monte_carlo import MonteCarloSimulator

        simulator1 = MonteCarloSimulator(
            returns=sample_returns,
            n_simulations=1000,
            seed=42,
        )

        simulator2 = MonteCarloSimulator(
            returns=sample_returns,
            n_simulations=1000,
            seed=42,
        )

        result1 = simulator1.run()
        result2 = simulator2.run()

        # 相同种子应该产生相同结果
        assert abs(result1.var - result2.var) < 1e-10
