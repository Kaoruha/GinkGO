# Upstream: ginkgo.trading.optimization.grid_search
# Downstream: pytest
# Role: GridSearchOptimizer 测试

"""
GridSearchOptimizer 测试

TDD Green 阶段: 测试用例实现
"""

import pytest
from decimal import Decimal
import pandas as pd
import numpy as np


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


@pytest.mark.unit
class TestGridSearchOptimizer:
    """GridSearchOptimizer 测试"""

    def test_init(self, sample_param_ranges):
        """测试初始化"""
        from ginkgo.trading.optimization.grid_search import GridSearchOptimizer

        optimizer = GridSearchOptimizer(param_ranges=sample_param_ranges)
        assert optimizer is not None
        assert len(optimizer.param_ranges) == 2

    def test_generate_grid(self, sample_param_ranges):
        """测试生成网格"""
        from ginkgo.trading.optimization.grid_search import GridSearchOptimizer

        optimizer = GridSearchOptimizer(param_ranges=sample_param_ranges)
        grid = optimizer.generate_grid()

        # 2 * 2 = 4 种组合
        assert len(grid) == 4
        assert {"fast": 5, "slow": 20} in grid
        assert {"fast": 5, "slow": 30} in grid
        assert {"fast": 10, "slow": 20} in grid
        assert {"fast": 10, "slow": 30} in grid

    def test_optimize(self, sample_param_ranges, mock_backtest_function):
        """测试优化运行"""
        from ginkgo.trading.optimization.grid_search import GridSearchOptimizer

        optimizer = GridSearchOptimizer(param_ranges=sample_param_ranges)
        optimizer.set_backtest_function(mock_backtest_function)

        result = optimizer.optimize(data=None)

        assert result is not None
        assert len(result.results) == 4
        assert result.best_params is not None

    def test_optimize_finds_best(self, sample_param_ranges, mock_backtest_function):
        """测试找到最佳参数"""
        from ginkgo.trading.optimization.grid_search import GridSearchOptimizer

        optimizer = GridSearchOptimizer(param_ranges=sample_param_ranges)
        optimizer.set_backtest_function(mock_backtest_function)

        result = optimizer.optimize(data=None)

        # 最大差值是 slow=30, fast=5，差值=25，score=25/30≈0.833
        assert result.best_params == {"fast": 5, "slow": 30}
        assert result.best_score > 0.8

    def test_optimize_with_maximize_false(self, sample_param_ranges):
        """测试最小化优化"""
        from ginkgo.trading.optimization.grid_search import GridSearchOptimizer

        # 反向的回测函数：差值越大分数越低
        def backtest(params, data):
            diff = params["slow"] - params["fast"]
            score = 1 - diff / 30.0
            return {"score": score}

        optimizer = GridSearchOptimizer(
            param_ranges=sample_param_ranges,
            maximize=False,
        )
        optimizer.set_backtest_function(backtest)

        result = optimizer.optimize(data=None)

        # 最小化时，最小分数对应的参数
        # params {"fast": 5, "slow": 30}: diff = 25, score = 0.1667 (最小)
        # params {"fast": 10, "slow": 20}: diff = 10, score = 0.6667
        assert result.best_params == {"fast": 5, "slow": 30}
        assert result.best_score < 0.2

    def test_optimize_with_parallel(self, sample_param_ranges, mock_backtest_function):
        """测试并行优化"""
        from ginkgo.trading.optimization.grid_search import GridSearchOptimizer

        optimizer = GridSearchOptimizer(
            param_ranges=sample_param_ranges,
            n_jobs=2,
        )
        optimizer.set_backtest_function(mock_backtest_function)

        result = optimizer.optimize(data=None)

        assert len(result.results) == 4

    def test_get_progress(self, sample_param_ranges, mock_backtest_function):
        """测试获取进度"""
        from ginkgo.trading.optimization.grid_search import GridSearchOptimizer

        optimizer = GridSearchOptimizer(param_ranges=sample_param_ranges)
        optimizer.set_backtest_function(mock_backtest_function)

        # 运行优化
        optimizer.optimize(data=None)

        # 完成后检查进度
        progress = optimizer.get_progress()
        assert progress["total"] == 4
        assert progress["completed"] == 4

    def test_result_sorting(self, sample_param_ranges, mock_backtest_function):
        """测试结果排序"""
        from ginkgo.trading.optimization.grid_search import GridSearchOptimizer

        optimizer = GridSearchOptimizer(param_ranges=sample_param_ranges)
        optimizer.set_backtest_function(mock_backtest_function)

        result = optimizer.optimize(data=None)

        # 结果应按分数降序排列
        scores = [r["score"] for r in result.results]
        assert scores == sorted(scores, reverse=True)

    def test_early_stopping(self, sample_param_ranges):
        """测试早停"""
        from ginkgo.trading.optimization.grid_search import GridSearchOptimizer

        call_count = 0

        def backtest(params, data):
            nonlocal call_count
            call_count += 1
            if call_count >= 2:
                # 模拟达到目标分数
                return {"score": 1.0}
            return {"score": 0.5}

        optimizer = GridSearchOptimizer(
            param_ranges=sample_param_ranges,
            early_stopping=True,
            target_score=0.95,
        )
        optimizer.set_backtest_function(backtest)

        result = optimizer.optimize(data=None)

        # 找到目标分数后应该停止
        assert result.best_score >= 0.95
