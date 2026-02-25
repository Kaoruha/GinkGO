# Upstream: numpy, scipy, sklearn, ginkgo.research.models
# Downstream: ginkgo.client.research_cli
# Role: 因子正交化 - Gram-Schmidt、PCA、残差法

"""
FactorOrthogonalizer - 因子正交化

使用多种方法对因子进行正交化处理，消除因子间相关性。

核心功能:
- Gram-Schmidt 正交化
- PCA 降维
- 残差化回归

Usage:
    from ginkgo.research.orthogonalization import FactorOrthogonalizer
    import pandas as pd

    factor_df = pd.DataFrame({
        "factor1": [...],
        "factor2": [...],
        "factor3": [...],
    })

    orth = FactorOrthogonalizer(factor_df)

    # Gram-Schmidt 正交化
    result = orth.gram_schmidt(order=["factor1", "factor2", "factor3"])

    # PCA 降维
    result = orth.pca(n_components=2)

    # 残差化
    result = orth.residualize(target="factor1", controls=["factor2"])
"""

from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal
from typing import Optional, List, Dict, Any, Tuple, Union
import time

import numpy as np
import pandas as pd
from scipy import linalg

from ginkgo.libs import GLOG

# Optional sklearn dependency
try:
    from sklearn.decomposition import PCA as SklearnPCA
    from sklearn.preprocessing import StandardScaler
    SKLEARN_AVAILABLE = True
except ImportError:
    SKLEARN_AVAILABLE = False


@dataclass
class OrthogonalizationResult:
    """
    正交化结果

    存储因子正交化的完整结果。

    Attributes:
        method: 正交化方法
        n_factors: 因子数量
        orthogonal_data: 正交化后的数据
        explained_variance: 解释方差比例 (PCA)
    """

    method: str
    n_factors: int
    orthogonal_data: Optional[pd.DataFrame] = None
    explained_variance: Optional[float] = None
    component_loadings: Optional[np.ndarray] = None
    original_correlation: Optional[np.ndarray] = None
    orthogonal_correlation: Optional[np.ndarray] = None
    created_at: Optional[datetime] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        """初始化后处理"""
        if self.created_at is None:
            self.created_at = datetime.now()

    def to_dict(self) -> Dict[str, Any]:
        """序列化为字典"""
        return {
            "method": self.method,
            "n_factors": self.n_factors,
            "explained_variance": self.explained_variance,
            "original_correlation": self.original_correlation.tolist()
            if self.original_correlation is not None else None,
            "orthogonal_correlation": self.orthogonal_correlation.tolist()
            if self.orthogonal_correlation is not None else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "metadata": self.metadata,
        }


class FactorOrthogonalizer:
    """
    因子正交化器

    使用多种方法对因子进行正交化处理。

    Attributes:
        factor_data: 因子数据 DataFrame
        factor_columns: 因子列名列表
    """

    def __init__(
        self,
        factor_data: pd.DataFrame,
        factor_columns: Optional[List[str]] = None,
    ):
        """
        初始化因子正交化器

        Args:
            factor_data: 因子数据，每列代表一个因子
            factor_columns: 指定因子列名 (可选，默认使用所有数值列)

        Raises:
            ValueError: 如果数据为空或列名无效
        """
        if factor_data.empty:
            raise ValueError("因子数据不能为空")

        self.factor_data = factor_data.copy()

        if factor_columns is None:
            # 使用所有数值列
            self.factor_columns = factor_data.select_dtypes(
                include=[np.number]
            ).columns.tolist()
        else:
            # 验证列名
            missing = [c for c in factor_columns if c not in factor_data.columns]
            if missing:
                raise ValueError(f"因子列不存在: {missing}")
            self.factor_columns = factor_columns

        if len(self.factor_columns) < 2:
            raise ValueError("至少需要 2 个因子进行正交化")

        # 计算原始相关矩阵
        self._original_corr = self.factor_data[self.factor_columns].corr().values

        GLOG.INFO(
            f"FactorOrthogonalizer 初始化: {len(self.factor_columns)} 个因子, "
            f"{len(self.factor_data)} 个样本"
        )

    def gram_schmidt(
        self,
        order: Optional[List[str]] = None,
    ) -> OrthogonalizationResult:
        """
        Gram-Schmidt 正交化

        按指定顺序对因子进行正交化。

        Args:
            order: 因子顺序 (可选，默认使用原始顺序)

        Returns:
            OrthogonalizationResult 正交化结果
        """
        start_time = time.time()

        if order is None:
            order = self.factor_columns.copy()
        else:
            # 验证顺序
            if set(order) != set(self.factor_columns):
                raise ValueError("顺序必须包含所有因子")

        GLOG.INFO(f"开始 Gram-Schmidt 正交化: 顺序 {order}")

        # 获取数据矩阵
        X = self.factor_data[order].values.astype(float)
        n_samples, n_factors = X.shape

        # Gram-Schmidt 过程
        Q = np.zeros_like(X)
        for j in range(n_factors):
            v = X[:, j].copy()
            for i in range(j):
                # 减去在已有正交向量上的投影
                proj = np.dot(Q[:, i], X[:, j]) / np.dot(Q[:, i], Q[:, i]) * Q[:, i]
                v = v - proj
            Q[:, j] = v

        # 创建结果 DataFrame
        orthogonal_data = pd.DataFrame(Q, columns=order, index=self.factor_data.index)

        # 计算正交化后的相关矩阵
        orth_corr = orthogonal_data.corr().values

        result = OrthogonalizationResult(
            method="gram_schmidt",
            n_factors=n_factors,
            orthogonal_data=orthogonal_data,
            original_correlation=self._original_corr,
            orthogonal_correlation=orth_corr,
        )

        duration = time.time() - start_time
        GLOG.INFO(f"Gram-Schmidt 正交化完成: 耗时 {duration:.2f}s")

        return result

    def pca(
        self,
        n_components: Optional[int] = None,
        variance_ratio: Optional[float] = None,
    ) -> OrthogonalizationResult:
        """
        PCA 正交化/降维

        使用主成分分析进行正交化。

        Args:
            n_components: 保留的主成分数量 (可选)
            variance_ratio: 保留的方差比例 (可选，如 0.9 表示 90%)

        Returns:
            OrthogonalizationResult 正交化结果
        """
        start_time = time.time()

        if not SKLEARN_AVAILABLE:
            raise ImportError(
                "sklearn 未安装。请使用: pip install scikit-learn"
            )

        GLOG.INFO(
            f"开始 PCA 正交化: n_components={n_components}, "
            f"variance_ratio={variance_ratio}"
        )

        # 标准化数据
        scaler = StandardScaler()
        X_scaled = scaler.fit_transform(self.factor_data[self.factor_columns])

        # 确定 n_components
        if variance_ratio is not None:
            # 先用所有成分计算
            pca_full = SklearnPCA()
            pca_full.fit(X_scaled)
            cumulative_variance = np.cumsum(pca_full.explained_variance_ratio_)
            n_components = np.argmax(cumulative_variance >= variance_ratio) + 1
            n_components = min(n_components, len(self.factor_columns))
            GLOG.INFO(f"选择 {n_components} 个主成分以满足 {variance_ratio:.0%} 方差")

        # 执行 PCA
        pca = SklearnPCA(n_components=n_components)
        X_pca = pca.fit_transform(X_scaled)

        # 创建结果 DataFrame
        component_names = [f"PC{i + 1}" for i in range(X_pca.shape[1])]
        orthogonal_data = pd.DataFrame(
            X_pca, columns=component_names, index=self.factor_data.index
        )

        # 计算解释方差
        explained_variance = sum(pca.explained_variance_ratio_)

        result = OrthogonalizationResult(
            method="pca",
            n_factors=X_pca.shape[1],
            orthogonal_data=orthogonal_data,
            explained_variance=explained_variance,
            component_loadings=pca.components_,
            original_correlation=self._original_corr,
        )

        duration = time.time() - start_time
        GLOG.INFO(
            f"PCA 正交化完成: {X_pca.shape[1]} 个主成分, "
            f"解释方差 {explained_variance:.2%}, 耗时 {duration:.2f}s"
        )

        return result

    def residualize(
        self,
        target: str,
        controls: List[str],
    ) -> OrthogonalizationResult:
        """
        残差化正交化

        对目标因子关于控制因子进行回归，取残差。

        Args:
            target: 目标因子名
            controls: 控制因子名列表

        Returns:
            OrthogonalizationResult 正交化结果
        """
        start_time = time.time()

        if target not in self.factor_columns:
            raise ValueError(f"目标因子不存在: {target}")

        for ctrl in controls:
            if ctrl not in self.factor_columns:
                raise ValueError(f"控制因子不存在: {ctrl}")

        GLOG.INFO(f"开始残差化: target={target}, controls={controls}")

        # 准备数据
        y = self.factor_data[target].values
        X = self.factor_data[controls].values

        # 添加截距项
        X_with_intercept = np.column_stack([np.ones(len(y)), X])

        # OLS 回归
        try:
            beta = np.linalg.lstsq(X_with_intercept, y, rcond=None)[0]
        except np.linalg.LinAlgError:
            # 如果矩阵奇异，使用伪逆
            beta = np.linalg.pinv(X_with_intercept) @ y

        # 计算残差
        y_pred = X_with_intercept @ beta
        residual = y - y_pred

        # 创建结果 DataFrame
        result_df = self.factor_data[self.factor_columns].copy()
        result_df[f"{target}_residual"] = residual

        # 计算残差与控制因子的相关性
        residual_corr = np.corrcoef(residual, X.T)

        result = OrthogonalizationResult(
            method="residualize",
            n_factors=len(self.factor_columns),
            orthogonal_data=result_df,
            original_correlation=self._original_corr,
            metadata={
                "target": target,
                "controls": controls,
                "regression_coefficients": beta.tolist(),
            },
        )

        duration = time.time() - start_time
        GLOG.INFO(f"残差化完成: 耗时 {duration:.2f}s")

        return result

    def get_correlation_matrix(self) -> pd.DataFrame:
        """
        获取因子相关矩阵

        Returns:
            相关矩阵 DataFrame
        """
        return self.factor_data[self.factor_columns].corr()

    def standardize(self) -> pd.DataFrame:
        """
        标准化因子数据

        Returns:
            标准化后的 DataFrame
        """
        data = self.factor_data[self.factor_columns]
        return (data - data.mean()) / data.std()

    def compare_methods(
        self,
        methods: Optional[List[str]] = None,
    ) -> Dict[str, OrthogonalizationResult]:
        """
        比较不同正交化方法

        Args:
            methods: 方法列表 (可选，默认比较所有方法)

        Returns:
            方法名 -> 结果的字典
        """
        if methods is None:
            methods = ["gram_schmidt", "pca"]

        results = {}
        for method in methods:
            if method == "gram_schmidt":
                results[method] = self.gram_schmidt()
            elif method == "pca":
                results[method] = self.pca()
            elif method == "residualize":
                # 需要指定 target 和 controls
                if len(self.factor_columns) >= 2:
                    results[method] = self.residualize(
                        target=self.factor_columns[0],
                        controls=self.factor_columns[1:],
                    )

        return results
