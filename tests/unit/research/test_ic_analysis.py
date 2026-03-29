# Upstream: ginkgo.research.ic_analysis
# Downstream: pytest
# Role: ICAnalyzer 单元测试

"""
ICAnalyzer 测试

TDD Green 阶段: 测试用例实现
"""

import pytest
from decimal import Decimal
import pandas as pd
import numpy as np


@pytest.fixture
def sample_factor_data():
    """创建示例因子数据"""
    dates = pd.date_range("2023-01-01", periods=100, freq="D")
    codes = ["000001.SZ", "000002.SZ", "000003.SZ", "000004.SZ", "000005.SZ"]

    data = []
    for date in dates:
        for code in codes:
            data.append({
                "date": date.strftime("%Y%m%d"),
                "code": code,
                "factor_value": np.random.randn(),
            })

    return pd.DataFrame(data)


@pytest.fixture
def sample_return_data():
    """创建示例收益数据"""
    dates = pd.date_range("2023-01-01", periods=105, freq="D")
    codes = ["000001.SZ", "000002.SZ", "000003.SZ", "000004.SZ", "000005.SZ"]

    data = []
    for date in dates:
        for code in codes:
            data.append({
                "date": date.strftime("%Y%m%d"),
                "code": code,
                "return_1d": np.random.randn() * 0.02,
                "return_5d": np.random.randn() * 0.05,
            })

    return pd.DataFrame(data)


@pytest.mark.financial
class TestICAnalyzer:
    """ICAnalyzer 单元测试"""

    def test_init(self, sample_factor_data, sample_return_data):
        """测试初始化"""
        from ginkgo.research.ic_analysis import ICAnalyzer

        analyzer = ICAnalyzer(sample_factor_data, sample_return_data)
        assert analyzer.factor_data is not None
        assert analyzer.return_data is not None

    def test_init_with_validation(self, sample_factor_data):
        """测试输入验证"""
        from ginkgo.research.ic_analysis import ICAnalyzer

        # 缺少必需列
        bad_data = pd.DataFrame({"date": [], "code": []})
        with pytest.raises(ValueError):
            ICAnalyzer(bad_data, sample_factor_data)

    def test_analyze_pearson(self, sample_factor_data, sample_return_data):
        """测试 Pearson IC 计算"""
        from ginkgo.research.ic_analysis import ICAnalyzer

        analyzer = ICAnalyzer(sample_factor_data, sample_return_data)
        result = analyzer.analyze(periods=[1, 5], method="pearson")

        assert 1 in result.ic_series
        assert 5 in result.ic_series
        assert len(result.ic_series[1]) > 0

    def test_analyze_spearman(self, sample_factor_data, sample_return_data):
        """测试 Rank IC (Spearman) 计算"""
        from ginkgo.research.ic_analysis import ICAnalyzer

        analyzer = ICAnalyzer(sample_factor_data, sample_return_data)
        result = analyzer.analyze(periods=[1], method="spearman")

        assert result.rank_ic_series is not None
        assert 1 in result.rank_ic_series

    def test_get_statistics(self, sample_factor_data, sample_return_data):
        """测试统计指标计算"""
        from ginkgo.research.ic_analysis import ICAnalyzer
        from ginkgo.research.models import ICStatistics

        analyzer = ICAnalyzer(sample_factor_data, sample_return_data)
        analyzer.analyze(periods=[1, 5])
        stats = analyzer.get_statistics(period=5)  # 使用存在的周期

        assert isinstance(stats, ICStatistics)
        assert stats.mean is not None
        assert stats.std is not None
        assert stats.icir is not None

    def test_icir_calculation(self, sample_factor_data, sample_return_data):
        """测试 ICIR 计算"""
        from ginkgo.research.ic_analysis import ICAnalyzer

        analyzer = ICAnalyzer(sample_factor_data, sample_return_data)
        analyzer.analyze(periods=[1, 5])
        stats = analyzer.get_statistics(period=5)  # 使用存在的周期

        # 如果有统计数据，验证 ICIR
        if stats is not None and stats.std != 0:
            expected_icir = stats.mean / stats.std
            assert abs(stats.icir - expected_icir) < 0.01

    def test_positive_ratio(self, sample_factor_data, sample_return_data):
        """测试正向 IC 比例"""
        from ginkgo.research.ic_analysis import ICAnalyzer

        analyzer = ICAnalyzer(sample_factor_data, sample_return_data)
        analyzer.analyze(periods=[1, 5])
        stats = analyzer.get_statistics(period=5)  # 使用存在的周期

        # 如果有统计数据，验证正向比例
        if stats is not None:
            # 正向比例应在 0-1 之间
            assert 0 <= stats.pos_ratio <= 1

    def test_analyze_with_custom_return_col(self, sample_factor_data, sample_return_data):
        """测试自定义收益列"""
        from ginkgo.research.ic_analysis import ICAnalyzer

        analyzer = ICAnalyzer(
            sample_factor_data,
            sample_return_data,
            return_col="return_5d"
        )
        result = analyzer.analyze(periods=[5])

        assert result is not None


@pytest.mark.financial
class TestICStatistics:
    """ICStatistics 测试"""

    def test_init(self):
        """测试初始化"""
        from ginkgo.research.models import ICStatistics

        stats = ICStatistics(
            mean=Decimal("0.05"),
            std=Decimal("0.15"),
            icir=Decimal("0.33"),
            t_stat=Decimal("2.1"),
            p_value=Decimal("0.03"),
            pos_ratio=Decimal("0.55"),
        )

        assert stats.mean == Decimal("0.05")
        assert stats.std == Decimal("0.15")

    def test_to_dict(self):
        """测试序列化"""
        from ginkgo.research.models import ICStatistics

        stats = ICStatistics(
            mean=Decimal("0.05"),
            std=Decimal("0.15"),
            icir=Decimal("0.33"),
        )
        d = stats.to_dict()

        assert d["mean"] == "0.05"
        assert "icir" in d


@pytest.mark.financial
class TestICAnalysisResult:
    """ICAnalysisResult 测试"""

    def test_init(self):
        """测试初始化"""
        from ginkgo.research.models import ICAnalysisResult

        result = ICAnalysisResult(
            factor_name="MOM_20",
            periods=[1, 5, 10, 20],
        )

        assert result.factor_name == "MOM_20"
        assert result.periods == [1, 5, 10, 20]

    def test_get_best_period(self):
        """测试获取最佳周期"""
        from ginkgo.research.models import ICAnalysisResult, ICStatistics

        result = ICAnalysisResult(
            factor_name="MOM_20",
            periods=[1, 5, 10],
            statistics={
                1: ICStatistics(icir=Decimal("0.2")),
                5: ICStatistics(icir=Decimal("0.5")),
                10: ICStatistics(icir=Decimal("0.3")),
            }
        )

        best = result.get_best_period(metric="icir")
        assert best == 5

    def test_to_dataframe(self):
        """测试转换为 DataFrame"""
        from ginkgo.research.models import ICAnalysisResult

        result = ICAnalysisResult(
            factor_name="MOM_20",
            periods=[1, 5, 10],
            ic_series={1: [0.1, 0.2, 0.15], 5: [0.08, 0.12, 0.09]},
        )

        df = result.to_dataframe()
        assert df is not None
