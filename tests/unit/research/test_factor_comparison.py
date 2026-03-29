# Upstream: ginkgo.research.factor_comparison
# Downstream: pytest
# Role: FactorComparator 测试

"""
FactorComparator 测试

TDD Green 阶段: 测试用例实现
"""

import pytest
import pandas as pd
import numpy as np


@pytest.fixture
def sample_multi_factor_data():
    """创建示例多因子数据"""
    np.random.seed(42)
    # 为每个日期创建多个股票的数据
    dates = pd.date_range("2023-01-01", periods=100, freq="B")
    codes = ["000001.SZ", "000002.SZ", "000003.SZ", "000004.SZ", "000005.SZ"]

    data = []
    for date in dates:
        for code in codes:
            data.append({
                "date": date,
                "code": code,
                "factor1": np.random.randn(),
                "factor2": np.random.randn() * 0.5,
                "factor3": np.random.randn() * 0.3,
                "return": np.random.randn() * 0.02,
            })

    return pd.DataFrame(data)


@pytest.mark.unit
class TestFactorComparisonResult:
    """FactorComparisonResult 测试"""

    def test_init(self):
        """测试初始化"""
        from ginkgo.research.factor_comparison import FactorComparisonResult

        result = FactorComparisonResult(factor_names=["factor1", "factor2"])

        assert result.factor_names == ["factor1", "factor2"]
        assert len(result.rankings) == 0

    def test_get_ranking(self):
        """测试获取排名"""
        from ginkgo.research.factor_comparison import FactorComparisonResult

        result = FactorComparisonResult(
            factor_names=["factor1", "factor2", "factor3"],
            rankings={
                "ic_mean": {"factor1": 0.05, "factor2": 0.03, "factor3": 0.04},
            },
        )

        ranking = result.get_ranking("ic_mean")
        assert ranking[0] == "factor1"  # 最高 IC

    def test_to_dict(self):
        """测试序列化"""
        from ginkgo.research.factor_comparison import FactorComparisonResult

        result = FactorComparisonResult(
            factor_names=["factor1", "factor2"],
            rankings={"ic": {"factor1": 0.05, "factor2": 0.03}},
        )

        d = result.to_dict()
        assert "factor_names" in d
        assert "rankings" in d


@pytest.mark.unit
class TestFactorComparator:
    """FactorComparator 测试"""

    def test_init(self, sample_multi_factor_data):
        """测试初始化"""
        from ginkgo.research.factor_comparison import FactorComparator

        comparator = FactorComparator(
            factor_data=sample_multi_factor_data,
            factor_columns=["factor1", "factor2", "factor3"],
            return_col="return",
        )

        assert comparator is not None
        assert len(comparator.factor_columns) == 3

    def test_compare(self, sample_multi_factor_data):
        """测试比较因子"""
        from ginkgo.research.factor_comparison import FactorComparator

        comparator = FactorComparator(
            factor_data=sample_multi_factor_data,
            factor_columns=["factor1", "factor2", "factor3"],
            return_col="return",
            date_col="date",
        )

        result = comparator.compare()

        assert result is not None
        assert len(result.factor_names) == 3
        # 应该有 metrics
        assert result.metrics is not None
        assert len(result.metrics) == 3

    def test_compare_ic(self, sample_multi_factor_data):
        """测试 IC 比较"""
        from ginkgo.research.factor_comparison import FactorComparator

        comparator = FactorComparator(
            factor_data=sample_multi_factor_data,
            factor_columns=["factor1", "factor2"],
            return_col="return",
            date_col="date",
        )

        result = comparator.compare()

        # 应该有 metrics 和 rankings
        assert result.metrics is not None
        assert isinstance(result.rankings, dict)

    def test_get_best_factor(self, sample_multi_factor_data):
        """测试获取最佳因子"""
        from ginkgo.research.factor_comparison import FactorComparator

        comparator = FactorComparator(
            factor_data=sample_multi_factor_data,
            factor_columns=["factor1", "factor2", "factor3"],
            return_col="return",
            date_col="date",
        )

        result = comparator.compare()
        best = result.get_best_factor(metric="composite_score")

        assert best is not None
        assert best in result.factor_names

    def test_get_summary_table(self, sample_multi_factor_data):
        """测试获取摘要表格"""
        from ginkgo.research.factor_comparison import FactorComparator

        comparator = FactorComparator(
            factor_data=sample_multi_factor_data,
            factor_columns=["factor1", "factor2"],
            return_col="return",
            date_col="date",
        )

        result = comparator.compare()
        summary = result.get_summary_table()

        assert summary is not None
        assert len(summary.columns) > 0
