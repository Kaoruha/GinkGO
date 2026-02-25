# Upstream: ginkgo.research.decay_analysis
# Downstream: pytest
# Role: FactorDecayAnalyzer 测试

"""
FactorDecayAnalyzer 测试

TDD Green 阶段: 测试用例实现
"""

import pytest
import pandas as pd
import numpy as np


@pytest.fixture
def sample_factor_return_data():
    """创建示例因子和收益数据"""
    np.random.seed(42)
    # 为每个日期创建多个股票的数据
    dates = pd.date_range("2023-01-01", periods=100, freq="B")
    codes = ["000001.SZ", "000002.SZ", "000003.SZ", "000004.SZ", "000005.SZ"]

    factor_data = []
    return_data = []

    for date in dates:
        for code in codes:
            factor_data.append({
                "date": date,
                "code": code,
                "factor_value": np.random.randn(),
            })
            return_data.append({
                "date": date,
                "code": code,
                "return": np.random.randn() * 0.02,
            })

    return pd.DataFrame(factor_data), pd.DataFrame(return_data)


@pytest.mark.unit
class TestDecayAnalysisResult:
    """DecayAnalysisResult 测试"""

    def test_init(self):
        """测试初始化"""
        from ginkgo.research.decay_analysis import DecayAnalysisResult

        result = DecayAnalysisResult(factor_name="test_factor")

        assert result.factor_name == "test_factor"
        assert result.half_life is None

    def test_to_dict(self):
        """测试序列化"""
        from ginkgo.research.decay_analysis import DecayAnalysisResult

        result = DecayAnalysisResult(
            factor_name="test",
            half_life=10.5,
            lag_ic={1: 0.05, 5: 0.03, 10: 0.01},
        )

        d = result.to_dict()
        assert d["factor_name"] == "test"
        assert d["half_life"] == 10.5


@pytest.mark.unit
class TestFactorDecayAnalyzer:
    """FactorDecayAnalyzer 测试"""

    def test_init(self, sample_factor_return_data):
        """测试初始化"""
        from ginkgo.research.decay_analysis import FactorDecayAnalyzer

        factor_data, return_data = sample_factor_return_data

        analyzer = FactorDecayAnalyzer(
            factor_data=factor_data,
            return_data=return_data,
        )

        assert analyzer is not None

    def test_calculate_lag_ic(self, sample_factor_return_data):
        """测试计算滞后 IC"""
        from ginkgo.research.decay_analysis import FactorDecayAnalyzer

        factor_data, return_data = sample_factor_return_data

        analyzer = FactorDecayAnalyzer(
            factor_data=factor_data,
            return_data=return_data,
        )

        lag_ic = analyzer.calculate_lag_ic(max_lag=10)

        assert lag_ic is not None
        # 应该返回一个字典
        assert isinstance(lag_ic, dict)

    def test_calculate_half_life(self, sample_factor_return_data):
        """测试计算半衰期"""
        from ginkgo.research.decay_analysis import FactorDecayAnalyzer

        factor_data, return_data = sample_factor_return_data

        analyzer = FactorDecayAnalyzer(
            factor_data=factor_data,
            return_data=return_data,
        )

        result = analyzer.analyze()

        # 半衰期应该为正数或 None
        if result.half_life is not None:
            assert result.half_life > 0

    def test_analyze(self, sample_factor_return_data):
        """测试完整分析"""
        from ginkgo.research.decay_analysis import FactorDecayAnalyzer

        factor_data, return_data = sample_factor_return_data

        analyzer = FactorDecayAnalyzer(
            factor_data=factor_data,
            return_data=return_data,
            factor_col="factor_value",
        )

        result = analyzer.analyze(max_lag=20)

        assert result is not None
        assert result.factor_name == "factor_value"
        # lag_ic 是一个字典
        assert isinstance(result.lag_ic, dict)

    def test_get_decay_curve(self, sample_factor_return_data):
        """测试获取衰减曲线"""
        from ginkgo.research.decay_analysis import FactorDecayAnalyzer

        factor_data, return_data = sample_factor_return_data

        analyzer = FactorDecayAnalyzer(
            factor_data=factor_data,
            return_data=return_data,
        )

        analyzer.analyze(max_lag=15)
        curve = analyzer.get_decay_curve()

        assert curve is not None
        # 曲线应该是一个 DataFrame
        assert isinstance(curve, pd.DataFrame)
