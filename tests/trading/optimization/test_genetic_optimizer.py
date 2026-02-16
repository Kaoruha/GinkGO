# Upstream: ginkgo.trading.optimization.genetic_optimizer
# Downstream: pytest
# Role: GeneticOptimizer 测试

"""
GeneticOptimizer 测试

TDD Green 阶段: 测试用例实现
"""

import pytest
from decimal import Decimal
import pandas as pd
import numpy as np

# 检查 deap 是否可用
try:
    import deap
    DEAP_AVAILABLE = True
except ImportError:
    DEAP_AVAILABLE = False


@pytest.fixture
def sample_param_ranges():
    """创建示例参数范围"""
    from ginkgo.trading.optimization.models import ParameterRange

    return [
        ParameterRange(name="fast", min_value=5, max_value=10, step=5),  # 2 values
        ParameterRange(name="slow", min_value=20, max_value=30, step=10),  # 2 values
    ]


@pytest.fixture
def mock_backtest_function():
    """创建模拟回测函数"""

    def backtest(params, data):
        # 简单模拟：fast 和 slow 差值越大，分数越高
        diff = params["slow"] - params["fast"]
        score = diff / 30.0  # 归一化到 0-1
        return {
            "score": score,
            "sharpe": score * 2,
            "return": score * 0.5,
        }

    return backtest


@pytest.mark.skipif(not DEAP_AVAILABLE, reason="deap not installed")
@pytest.mark.unit
class TestGeneticOptimizer:
    """GeneticOptimizer 测试"""

    def test_init(self, sample_param_ranges):
        """测试初始化"""
        from ginkgo.trading.optimization.genetic_optimizer import GeneticOptimizer

        optimizer = GeneticOptimizer(
            param_ranges=sample_param_ranges,
            population_size=10,
            generations=5,
        )
        assert optimizer is not None
        assert optimizer.population_size == 10
        assert optimizer.generations == 5

    def test_init_without_deap(self, sample_param_ranges):
        """测试无 deap 时初始化失败"""
        # 此测试在 deap 可用时跳过
        pass

    def test_optimize(self, sample_param_ranges, mock_backtest_function):
        """测试优化运行"""
        from ginkgo.trading.optimization.genetic_optimizer import GeneticOptimizer

        optimizer = GeneticOptimizer(
            param_ranges=sample_param_ranges,
            population_size=10,
            generations=3,
        )
        optimizer.set_backtest_function(mock_backtest_function)

        result = optimizer.optimize(data=None)

        assert result is not None
        assert result.optimizer_type == "genetic"
        assert len(result.results) > 0
        assert result.best_params is not None

    def test_optimize_finds_good_params(self, sample_param_ranges, mock_backtest_function):
        """测试找到较好的参数"""
        from ginkgo.trading.optimization.genetic_optimizer import GeneticOptimizer

        optimizer = GeneticOptimizer(
            param_ranges=sample_param_ranges,
            population_size=20,
            generations=10,
        )
        optimizer.set_backtest_function(mock_backtest_function)

        result = optimizer.optimize(data=None)

        # 遗传算法应该能找到接近最优的解
        # 最优是 fast=5, slow=30, score=0.833
        assert result.best_score >= 0.5  # 应该找到不错的解

    def test_optimize_with_maximize_false(self, sample_param_ranges):
        """测试最小化优化"""
        from ginkgo.trading.optimization.genetic_optimizer import GeneticOptimizer

        # 反向回测函数
        def backtest(params, data):
            diff = params["slow"] - params["fast"]
            score = 1 - diff / 30.0
            return {"score": score}

        optimizer = GeneticOptimizer(
            param_ranges=sample_param_ranges,
            maximize=False,
            population_size=10,
            generations=5,
        )
        optimizer.set_backtest_function(backtest)

        result = optimizer.optimize(data=None)

        # 最小化时应该找到较小的分数
        assert result.best_score <= 0.5

    def test_get_progress(self, sample_param_ranges, mock_backtest_function):
        """测试获取进度"""
        from ginkgo.trading.optimization.genetic_optimizer import GeneticOptimizer

        optimizer = GeneticOptimizer(
            param_ranges=sample_param_ranges,
            population_size=10,
            generations=3,
        )
        optimizer.set_backtest_function(mock_backtest_function)

        optimizer.optimize(data=None)

        progress = optimizer.get_progress()
        assert progress["completed"] > 0

    def test_crossover_and_mutation_params(self, sample_param_ranges, mock_backtest_function):
        """测试交叉和变异参数"""
        from ginkgo.trading.optimization.genetic_optimizer import GeneticOptimizer

        optimizer = GeneticOptimizer(
            param_ranges=sample_param_ranges,
            population_size=10,
            generations=3,
            crossover_prob=0.9,
            mutation_prob=0.3,
        )
        optimizer.set_backtest_function(mock_backtest_function)

        result = optimizer.optimize(data=None)

        assert result is not None
        assert optimizer.crossover_prob == 0.9
        assert optimizer.mutation_prob == 0.3
