# Upstream: ginkgo.research.orthogonalization
# Downstream: pytest
# Role: FactorOrthogonalizer 测试

"""
FactorOrthogonalizer 测试

TDD Green 阶段: 测试用例实现
"""

import pytest
from decimal import Decimal
import pandas as pd
import numpy as np


@pytest.fixture
def sample_factor_data():
    """创建示例多因子数据"""
    np.random.seed(42)
    n_samples = 1000

    # 创建有相关性的因子
    factor1 = np.random.randn(n_samples)
    factor2 = factor1 * 0.7 + np.random.randn(n_samples) * 0.3  # 与 factor1 相关
    factor3 = factor2 * 0.5 + np.random.randn(n_samples) * 0.5  # 与 factor2 相关

    return pd.DataFrame({
        "factor1": factor1,
        "factor2": factor2,
        "factor3": factor3,
    })


@pytest.mark.unit
class TestOrthogonalizationResult:
    """OrthogonalizationResult 测试"""

    def test_init(self):
        """测试初始化"""
        from ginkgo.research.orthogonalization import OrthogonalizationResult

        result = OrthogonalizationResult(
            method="gram_schmidt",
            n_factors=3,
        )

        assert result.method == "gram_schmidt"
        assert result.n_factors == 3

    def test_to_dict(self):
        """测试序列化"""
        from ginkgo.research.orthogonalization import OrthogonalizationResult

        result = OrthogonalizationResult(
            method="pca",
            n_factors=3,
            explained_variance=0.85,
        )

        d = result.to_dict()
        assert d["method"] == "pca"
        assert d["explained_variance"] == 0.85


@pytest.mark.unit
class TestFactorOrthogonalizer:
    """FactorOrthogonalizer 测试"""

    def test_init(self, sample_factor_data):
        """测试初始化"""
        from ginkgo.research.orthogonalization import FactorOrthogonalizer

        orth = FactorOrthogonalizer(sample_factor_data)

        assert orth is not None
        assert orth.factor_data is not None

    def test_init_with_column_names(self, sample_factor_data):
        """测试指定列名初始化"""
        from ginkgo.research.orthogonalization import FactorOrthogonalizer

        orth = FactorOrthogonalizer(
            sample_factor_data,
            factor_columns=["factor1", "factor2"],
        )

        assert len(orth.factor_columns) == 2

    def test_gram_schmidt(self, sample_factor_data):
        """测试 Gram-Schmidt 正交化"""
        from ginkgo.research.orthogonalization import FactorOrthogonalizer

        orth = FactorOrthogonalizer(sample_factor_data)
        result = orth.gram_schmidt(order=["factor1", "factor2", "factor3"])

        assert result is not None
        assert result.orthogonal_data is not None
        assert result.orthogonal_data.shape == sample_factor_data.shape

    def test_gram_schmidt_reduces_correlation(self, sample_factor_data):
        """测试 Gram-Schmidt 降低相关性"""
        from ginkgo.research.orthogonalization import FactorOrthogonalizer

        # 原始相关性
        original_corr = sample_factor_data.corr().iloc[0, 1]

        orth = FactorOrthogonalizer(sample_factor_data)
        result = orth.gram_schmidt(order=["factor1", "factor2", "factor3"])

        # 正交化后相关性应降低
        new_corr = result.orthogonal_data.corr().iloc[0, 1]
        assert abs(new_corr) < abs(original_corr)

    def test_gram_schmidt_custom_order(self, sample_factor_data):
        """测试 Gram-Schmidt 自定义顺序"""
        from ginkgo.research.orthogonalization import FactorOrthogonalizer

        orth = FactorOrthogonalizer(sample_factor_data)
        result = orth.gram_schmidt(order=["factor3", "factor2", "factor1"])

        # 第一个因子应该不变
        assert np.allclose(
            result.orthogonal_data.iloc[:, 0],
            sample_factor_data["factor3"],
        )

    def test_pca(self, sample_factor_data):
        """测试 PCA 正交化"""
        from ginkgo.research.orthogonalization import FactorOrthogonalizer

        orth = FactorOrthogonalizer(sample_factor_data)
        result = orth.pca(n_components=2)

        assert result is not None
        assert result.orthogonal_data.shape[1] == 2

    def test_pca_explained_variance(self, sample_factor_data):
        """测试 PCA 解释方差"""
        from ginkgo.research.orthogonalization import FactorOrthogonalizer

        orth = FactorOrthogonalizer(sample_factor_data)
        result = orth.pca(n_components=2)

        # 应该返回解释方差比例
        assert result.explained_variance is not None
        assert result.explained_variance > 0

    def test_pca_variance_ratio(self, sample_factor_data):
        """测试 PCA 方差比例参数"""
        from ginkgo.research.orthogonalization import FactorOrthogonalizer

        orth = FactorOrthogonalizer(sample_factor_data)
        result = orth.pca(variance_ratio=0.9)

        # 保留足够解释 90% 方差的成分
        assert result is not None

    def test_residualize(self, sample_factor_data):
        """测试残差化"""
        from ginkgo.research.orthogonalization import FactorOrthogonalizer

        orth = FactorOrthogonalizer(sample_factor_data)
        result = orth.residualize(
            target="factor1",
            controls=["factor2", "factor3"],
        )

        assert result is not None
        assert result.orthogonal_data is not None

    def test_residualize_removes_correlation(self, sample_factor_data):
        """测试残差化移除相关性"""
        from ginkgo.research.orthogonalization import FactorOrthogonalizer

        orth = FactorOrthogonalizer(sample_factor_data)
        result = orth.residualize(
            target="factor1",
            controls=["factor2"],
        )

        # factor1 的残差应该与 factor2 不相关
        residual = result.orthogonal_data["factor1_residual"]
        correlation = residual.corr(sample_factor_data["factor2"])
        assert abs(correlation) < 0.1  # 相关系数接近 0

    def test_get_correlation_matrix(self, sample_factor_data):
        """测试获取相关矩阵"""
        from ginkgo.research.orthogonalization import FactorOrthogonalizer

        orth = FactorOrthogonalizer(sample_factor_data)
        corr_matrix = orth.get_correlation_matrix()

        assert corr_matrix.shape == (3, 3)
        # 对角线应该为 1
        assert np.allclose(np.diag(corr_matrix), 1.0)

    def test_standardize(self, sample_factor_data):
        """测试标准化"""
        from ginkgo.research.orthogonalization import FactorOrthogonalizer

        orth = FactorOrthogonalizer(sample_factor_data)
        standardized = orth.standardize()

        # 标准化后均值接近 0，标准差接近 1
        assert np.allclose(standardized.mean(), 0, atol=0.1)
        assert np.allclose(standardized.std(), 1, atol=0.1)

    def test_compare_methods(self, sample_factor_data):
        """测试比较不同方法"""
        from ginkgo.research.orthogonalization import FactorOrthogonalizer

        orth = FactorOrthogonalizer(sample_factor_data)

        gs_result = orth.gram_schmidt()
        pca_result = orth.pca(n_components=3)

        # 两种方法结果形状相同（使用所有成分时）
        assert gs_result.orthogonal_data.shape[0] == pca_result.orthogonal_data.shape[0]
