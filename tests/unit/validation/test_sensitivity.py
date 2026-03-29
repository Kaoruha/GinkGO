# Upstream: ginkgo.validation.sensitivity
# Downstream: pytest
# Role: SensitivityAnalyzer 测试

"""
SensitivityAnalyzer 测试

TDD Green 阶段: 测试用例实现
"""

import pytest
import pandas as pd
import numpy as np


@pytest.fixture
def mock_backtest_function():
    """创建模拟回测函数"""

    def backtest(params, data):
        # 简单模拟：参数值越大，分数越高
        param_value = params.get("test_param", 10)
        score = param_value / 20.0  # 归一化到 0-1
        return {"score": score, "sharpe": score * 1.5}

    return backtest


@pytest.mark.unit
class TestSensitivityResult:
    """SensitivityResult 测试"""

    def test_init(self):
        """测试初始化"""
        from ginkgo.validation.sensitivity import SensitivityResult

        result = SensitivityResult(
            param_name="fast_period",
            base_value=10,
        )

        assert result.param_name == "fast_period"
        assert result.base_value == 10

    def test_to_dict(self):
        """测试序列化"""
        from ginkgo.validation.sensitivity import SensitivityResult

        result = SensitivityResult(
            param_name="test",
            base_value=10,
            values=[5, 10, 15],
            scores=[0.5, 0.8, 0.7],
        )

        d = result.to_dict()
        assert d["param_name"] == "test"
        assert len(d["values"]) == 3


@pytest.mark.unit
class TestSensitivityAnalyzer:
    """SensitivityAnalyzer 测试"""

    def test_init(self):
        """测试初始化"""
        from ginkgo.validation.sensitivity import SensitivityAnalyzer

        analyzer = SensitivityAnalyzer(
            param_name="fast_period",
            base_value=10,
            test_values=[5, 10, 15, 20],
        )

        assert analyzer is not None
        assert analyzer.param_name == "fast_period"
        assert len(analyzer.test_values) == 4

    def test_analyze(self, mock_backtest_function):
        """测试分析"""
        from ginkgo.validation.sensitivity import SensitivityAnalyzer

        analyzer = SensitivityAnalyzer(
            param_name="test_param",
            base_value=10,
            test_values=[5, 10, 15, 20],
        )
        analyzer.set_backtest_function(mock_backtest_function)

        result = analyzer.analyze()

        assert result is not None
        assert len(result.values) == 4
        assert len(result.scores) == 4

    def test_get_sensitivity_score(self, mock_backtest_function):
        """测试获取敏感性分数"""
        from ginkgo.validation.sensitivity import SensitivityAnalyzer

        analyzer = SensitivityAnalyzer(
            param_name="test_param",
            base_value=10,
            test_values=[5, 10, 15, 20],
        )
        analyzer.set_backtest_function(mock_backtest_function)

        result = analyzer.analyze()
        score = result.get_sensitivity_score()

        # 敏感性分数应该是一个非负数
        assert score >= 0

    def test_get_elasticity(self, mock_backtest_function):
        """测试获取弹性"""
        from ginkgo.validation.sensitivity import SensitivityAnalyzer

        analyzer = SensitivityAnalyzer(
            param_name="test_param",
            base_value=10,
            test_values=[5, 10, 15, 20],
        )
        analyzer.set_backtest_function(mock_backtest_function)

        result = analyzer.analyze()
        elasticity = result.get_elasticity()

        # 弹性可能为正或负
        assert isinstance(elasticity, (int, float))

    def test_get_optimal_value(self, mock_backtest_function):
        """测试获取最优值"""
        from ginkgo.validation.sensitivity import SensitivityAnalyzer

        analyzer = SensitivityAnalyzer(
            param_name="test_param",
            base_value=10,
            test_values=[5, 10, 15, 20],
        )
        analyzer.set_backtest_function(mock_backtest_function)

        result = analyzer.analyze()
        optimal = result.get_optimal_value()

        # 最优值应该在测试值范围内
        assert optimal in [5, 10, 15, 20]

    def test_to_dataframe(self, mock_backtest_function):
        """测试转换为 DataFrame"""
        from ginkgo.validation.sensitivity import SensitivityAnalyzer

        analyzer = SensitivityAnalyzer(
            param_name="test_param",
            base_value=10,
            test_values=[5, 10, 15],
        )
        analyzer.set_backtest_function(mock_backtest_function)

        result = analyzer.analyze()
        df = result.to_dataframe()

        assert df is not None
        assert len(df) == 3
        assert "value" in df.columns
        assert "score" in df.columns
