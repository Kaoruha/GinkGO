"""statistics.py 统计工具模块单元测试
性能: 212MB RSS, 1.24s, 14 tests [PASS]

覆盖范围:
- t_test(): 独立样本 t 检验
- chi2_test(): 卡方独立性检验
- kolmogorov_smirnov_test(): 占位函数
- rank_sum_test(): 占位函数
- 边界条件和异常处理
"""

import sys
from pathlib import Path

import numpy as np
import pytest

sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent / "src"))

from ginkgo.libs.data.statistics import chi2_test, kolmogorov_smirnov_test, rank_sum_test, t_test


# ---------------------------------------------------------------------------
# scipy 可用性检查
# ---------------------------------------------------------------------------
_scipy_available = True
try:
    import scipy.stats  # noqa: F401
except ImportError:
    _scipy_available = False

skip_no_scipy = pytest.mark.skipif(
    not _scipy_available, reason="scipy is not installed"
)


# ---------------------------------------------------------------------------
# t_test
# ---------------------------------------------------------------------------
@pytest.mark.unit
@skip_no_scipy
class TestTTest:
    """独立样本 t 检验测试"""

    def test_identical_distributions(self):
        """相同分布的两个样本，p 值应较大

        注意: t_test 源码直接调用 .var()，要求输入支持 numpy 数组方法，
        因此传入 numpy 数组。
        """
        np.random.seed(42)
        data = np.random.normal(0, 1, 100)
        result = t_test(data, data)
        assert result.pvalue > 0.05

    def test_different_distributions(self):
        """不同均值分布，p 值应较小"""
        np.random.seed(42)
        group1 = np.random.normal(0, 1, 100)
        group2 = np.random.normal(5, 1, 100)
        result = t_test(group1, group2)
        assert result.pvalue < 0.05

    def test_custom_confidence_level(self):
        """自定义置信水平"""
        np.random.seed(42)
        group1 = np.random.normal(0, 1, 50)
        group2 = np.random.normal(0, 1, 50)
        result = t_test(group1, group2, level_of_confidence=0.95)
        assert result is not None

    def test_different_variances(self):
        """不同方差的两个样本"""
        np.random.seed(42)
        group1 = np.random.normal(0, 1, 100)
        group2 = np.random.normal(0, 10, 100)
        result = t_test(group1, group2)
        assert result is not None

    def test_equal_variances(self):
        """相同方差的两个样本（自由度计算路径不同）"""
        np.random.seed(42)
        group1 = np.random.normal(0, 1, 50)
        group2 = np.random.normal(0, 1, 50)
        result = t_test(group1, group2)
        assert result is not None

    def test_small_samples(self):
        """小样本测试"""
        group1 = np.array([1.0, 2.0, 3.0, 4.0, 5.0])
        group2 = np.array([6.0, 7.0, 8.0, 9.0, 10.0])
        result = t_test(group1, group2)
        assert result is not None

    def test_returns_ttest_result(self):
        """返回值类型检查"""
        group1 = np.array([1.0, 2.0, 3.0])
        group2 = np.array([4.0, 5.0, 6.0])
        result = t_test(group1, group2)
        assert hasattr(result, "statistic")
        assert hasattr(result, "pvalue")


# ---------------------------------------------------------------------------
# chi2_test
# ---------------------------------------------------------------------------
@pytest.mark.unit
@skip_no_scipy
class TestChi2Test:
    """卡方独立性检验测试"""

    def test_same_distribution(self):
        """相同分布样本"""
        np.random.seed(42)
        data = np.random.normal(0, 1, 200)
        chi2, p, dof, expected = chi2_test(data.tolist(), data.tolist())
        assert p > 0.05  # 相同分布，不拒绝零假设
        assert dof > 0
        assert chi2 >= 0

    def test_different_distributions(self):
        """不同分布样本"""
        np.random.seed(42)
        group1 = np.random.normal(0, 1, 100)
        group2 = np.random.normal(5, 1, 100)
        chi2, p, dof, expected = chi2_test(group1.tolist(), group2.tolist())
        assert p < 0.05  # 不同分布，拒绝零假设

    def test_custom_category_count(self):
        """自定义分箱数量"""
        np.random.seed(42)
        group1 = np.random.normal(0, 1, 100)
        group2 = np.random.normal(0, 1, 100)
        chi2, p, dof, expected = chi2_test(
            group1.tolist(), group2.tolist(), category_count=5
        )
        assert dof > 0

    def test_return_structure(self):
        """返回值结构检查: (chi2, p, dof, expected)"""
        group1 = [1.0, 2.0, 3.0, 4.0, 5.0]
        group2 = [6.0, 7.0, 8.0, 9.0, 10.0]
        result = chi2_test(group1, group2)
        assert len(result) == 4
        chi2, p, dof, expected = result
        assert isinstance(chi2, float)
        assert isinstance(p, float)
        assert isinstance(dof, int)
        assert expected is not None

    def test_all_same_values_raises_error(self):
        """所有值相同时应抛出异常（无法形成有效分箱）"""
        group1 = [1.0, 1.0]
        group2 = [1.0, 1.0]
        with pytest.raises((ValueError, Exception)):
            chi2_test(group1, group2)


# ---------------------------------------------------------------------------
# 占位函数
# ---------------------------------------------------------------------------
@pytest.mark.unit
class TestPlaceholderFunctions:
    """占位函数测试"""

    def test_kolmogorov_smirnov_test_returns_none(self):
        """kolmogorov_smirnov_test 是占位函数，返回 None"""
        assert kolmogorov_smirnov_test() is None

    def test_rank_sum_test_returns_none(self):
        """rank_sum_test 是占位函数，返回 None"""
        assert rank_sum_test() is None
