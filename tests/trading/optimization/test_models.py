# Upstream: ginkgo.trading.optimization.models
# Downstream: pytest
# Role: 优化模块数据模型测试

"""
优化模块数据模型测试

TDD Green 阶段: 测试用例实现
"""

import pytest
from decimal import Decimal


@pytest.mark.unit
class TestParameterRange:
    """ParameterRange 测试"""

    def test_init_continuous(self):
        """测试连续值参数范围"""
        from ginkgo.trading.optimization.models import ParameterRange

        pr = ParameterRange(
            name="fast_period",
            min_value=5,
            max_value=20,
            step=1,
        )

        assert pr.name == "fast_period"
        assert pr.min_value == 5
        assert pr.max_value == 20
        assert pr.step == 1

    def test_init_discrete(self):
        """测试离散值参数范围"""
        from ginkgo.trading.optimization.models import ParameterRange

        pr = ParameterRange(
            name="strategy_type",
            values=["momentum", "mean_reversion", "trend"],
        )

        assert pr.name == "strategy_type"
        assert pr.values == ["momentum", "mean_reversion", "trend"]

    def test_generate_values_continuous(self):
        """测试生成连续值序列"""
        from ginkgo.trading.optimization.models import ParameterRange

        pr = ParameterRange(
            name="period",
            min_value=5,
            max_value=10,
            step=1,
        )

        values = pr.generate_values()
        assert values == [5, 6, 7, 8, 9, 10]

    def test_generate_values_discrete(self):
        """测试生成离散值序列"""
        from ginkgo.trading.optimization.models import ParameterRange

        pr = ParameterRange(
            name="type",
            values=["A", "B", "C"],
        )

        values = pr.generate_values()
        assert values == ["A", "B", "C"]

    def test_to_dict(self):
        """测试序列化"""
        from ginkgo.trading.optimization.models import ParameterRange

        pr = ParameterRange(name="period", min_value=5, max_value=20, step=5)
        d = pr.to_dict()

        assert d["name"] == "period"
        assert d["min_value"] == 5
        assert d["max_value"] == 20


@pytest.mark.unit
class TestOptimizationResult:
    """OptimizationResult 测试"""

    def test_init(self):
        """测试初始化"""
        from ginkgo.trading.optimization.models import OptimizationResult

        result = OptimizationResult(
            strategy_name="TestStrategy",
            optimizer_type="grid",
        )

        assert result.strategy_name == "TestStrategy"
        assert result.optimizer_type == "grid"
        assert result.results == []

    def test_add_result(self):
        """测试添加结果"""
        from ginkgo.trading.optimization.models import OptimizationResult

        result = OptimizationResult(strategy_name="Test", optimizer_type="grid")
        result.add_result(
            params={"fast": 10, "slow": 20},
            score=0.85,
            metrics={"sharpe": 1.5, "return": 0.3},
        )

        assert len(result.results) == 1
        assert result.results[0]["params"] == {"fast": 10, "slow": 20}
        assert result.results[0]["score"] == 0.85

    def test_get_best_params(self):
        """测试获取最佳参数"""
        from ginkgo.trading.optimization.models import OptimizationResult

        result = OptimizationResult(strategy_name="Test", optimizer_type="grid")
        result.add_result(params={"fast": 5}, score=0.5)
        result.add_result(params={"fast": 10}, score=0.9)
        result.add_result(params={"fast": 15}, score=0.7)

        best = result.get_best_params()
        assert best == {"fast": 10}

    def test_get_top_n(self):
        """测试获取 Top N 结果"""
        from ginkgo.trading.optimization.models import OptimizationResult

        result = OptimizationResult(strategy_name="Test", optimizer_type="grid")
        result.add_result(params={"fast": 5}, score=0.5)
        result.add_result(params={"fast": 10}, score=0.9)
        result.add_result(params={"fast": 15}, score=0.7)

        top2 = result.get_top_n(2)
        assert len(top2) == 2
        assert top2[0]["score"] == 0.9
        assert top2[1]["score"] == 0.7

    def test_to_dict(self):
        """测试序列化"""
        from ginkgo.trading.optimization.models import OptimizationResult

        result = OptimizationResult(
            strategy_name="Test",
            optimizer_type="grid",
        )
        result.add_result(params={"fast": 10}, score=0.85)

        d = result.to_dict()
        assert d["strategy_name"] == "Test"
        assert d["optimizer_type"] == "grid"
        assert len(d["results"]) == 1


@pytest.mark.unit
class TestOptimizationRun:
    """OptimizationRun 测试"""

    def test_init(self):
        """测试初始化"""
        from ginkgo.trading.optimization.models import OptimizationRun

        run = OptimizationRun(
            params={"fast": 10, "slow": 20},
        )

        assert run.params == {"fast": 10, "slow": 20}
        assert run.score is None
        assert run.metrics == {}

    def test_set_result(self):
        """测试设置结果"""
        from ginkgo.trading.optimization.models import OptimizationRun

        run = OptimizationRun(params={"fast": 10})
        run.set_result(
            score=0.85,
            metrics={"sharpe": 1.5, "return": 0.3, "drawdown": 0.1},
        )

        assert run.score == 0.85
        assert run.metrics["sharpe"] == 1.5

    def test_to_dict(self):
        """测试序列化"""
        from ginkgo.trading.optimization.models import OptimizationRun

        run = OptimizationRun(params={"fast": 10})
        run.set_result(score=0.85, metrics={"sharpe": 1.5})

        d = run.to_dict()
        assert d["params"] == {"fast": 10}
        assert d["score"] == 0.85
