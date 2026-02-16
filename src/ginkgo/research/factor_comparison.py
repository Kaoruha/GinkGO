# Upstream: numpy, pandas, scipy, ginkgo.research.ic_analysis, ginkgo.research.layering
# Downstream: ginkgo.client.research_cli
# Role: 因子比较器 - 对比多个因子的表现

"""
FactorComparator - 因子比较器

对比多个因子的 IC、分层收益、换手率等指标，生成综合评分。

核心功能:
- 计算每个因子的 IC 统计指标
- 计算分层收益和多空收益
- 生成综合评分和排名
- 输出对比表格

Usage:
    from ginkgo.research.factor_comparison import FactorComparator
    import pandas as pd

    factor_data = pd.DataFrame({
        "date": [...],
        "code": [...],
        "factor1": [...],
        "factor2": [...],
        "return": [...],
    })

    comparator = FactorComparator(
        factor_data=factor_data,
        factor_columns=["factor1", "factor2"],
        return_col="return",
    )

    result = comparator.compare()
    print(result.get_best_factor())
"""

from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal
from typing import Optional, List, Dict, Any, Tuple
import time

import numpy as np
import pandas as pd
from scipy import stats as scipy_stats

from ginkgo.libs import GLOG


@dataclass
class FactorComparisonResult:
    """
    因子比较结果

    存储多因子对比的完整结果。

    Attributes:
        factor_names: 因子名称列表
        rankings: 各指标的因子排名
        metrics: 各因子的详细指标
    """

    factor_names: List[str]
    rankings: Dict[str, Dict[str, float]] = field(default_factory=dict)
    metrics: Dict[str, Dict[str, float]] = field(default_factory=dict)
    composite_scores: Dict[str, float] = field(default_factory=dict)
    created_at: Optional[datetime] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        """初始化后处理"""
        if self.created_at is None:
            self.created_at = datetime.now()

    def get_ranking(self, metric: str) -> List[str]:
        """
        获取指定指标的因子排名

        Args:
            metric: 指标名称

        Returns:
            排名后的因子列表
        """
        if metric not in self.rankings:
            return []

        ranking_dict = self.rankings[metric]
        return sorted(ranking_dict.keys(), key=lambda x: ranking_dict[x], reverse=True)

    def get_best_factor(self, metric: str = "composite_score") -> Optional[str]:
        """
        获取最佳因子

        Args:
            metric: 评价指标 (默认综合评分)

        Returns:
            最佳因子名称
        """
        if metric == "composite_score":
            if not self.composite_scores:
                return None
            return max(self.composite_scores.keys(), key=lambda x: self.composite_scores[x])

        ranking = self.get_ranking(metric)
        return ranking[0] if ranking else None

    def get_summary_table(self) -> pd.DataFrame:
        """
        获取摘要表格

        Returns:
            对比表格 DataFrame
        """
        if not self.metrics:
            return pd.DataFrame()

        rows = []
        for factor in self.factor_names:
            row = {"factor": factor}
            row.update(self.metrics.get(factor, {}))
            row["composite_score"] = self.composite_scores.get(factor, 0)
            rows.append(row)

        return pd.DataFrame(rows)

    def to_dict(self) -> Dict[str, Any]:
        """序列化为字典"""
        return {
            "factor_names": self.factor_names,
            "rankings": self.rankings,
            "metrics": self.metrics,
            "composite_scores": self.composite_scores,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "metadata": self.metadata,
        }


class FactorComparator:
    """
    因子比较器

    对比多个因子的表现指标。

    Attributes:
        factor_data: 因子数据 DataFrame
        factor_columns: 因子列名列表
    """

    def __init__(
        self,
        factor_data: pd.DataFrame,
        factor_columns: List[str],
        return_col: str = "return",
        date_col: str = "date",
        code_col: str = "code",
    ):
        """
        初始化因子比较器

        Args:
            factor_data: 因子数据，必须包含 date, code, 因子值, 收益列
            factor_columns: 因子列名列表
            return_col: 收益列名
            date_col: 日期列名
            code_col: 股票代码列名
        """
        # 验证数据
        required_cols = [date_col, code_col, return_col] + factor_columns
        missing = [c for c in required_cols if c not in factor_data.columns]
        if missing:
            raise ValueError(f"数据缺少必需列: {missing}")

        self.factor_data = factor_data.copy()
        self.factor_columns = factor_columns
        self.return_col = return_col
        self.date_col = date_col
        self.code_col = code_col

        self._result: Optional[FactorComparisonResult] = None

        GLOG.INFO(f"FactorComparator 初始化: {len(factor_columns)} 个因子")

    def compare(
        self,
        weights: Optional[Dict[str, float]] = None,
    ) -> FactorComparisonResult:
        """
        执行因子比较

        Args:
            weights: 各指标权重 (可选，默认等权)

        Returns:
            FactorComparisonResult 比较结果
        """
        start_time = time.time()

        result = FactorComparisonResult(factor_names=self.factor_columns)

        # 默认权重
        if weights is None:
            weights = {
                "ic_mean": 0.3,
                "icir": 0.3,
                "long_short_return": 0.2,
                "monotonicity": 0.2,
            }

        GLOG.INFO(f"开始因子比较: {len(self.factor_columns)} 个因子")

        # 计算每个因子的指标
        for factor in self.factor_columns:
            metrics = self._calculate_factor_metrics(factor)
            result.metrics[factor] = metrics

        # 生成各指标排名
        metric_names = set()
        for factor_metrics in result.metrics.values():
            metric_names.update(factor_metrics.keys())

        for metric in metric_names:
            ranking = {}
            for factor in self.factor_columns:
                if metric in result.metrics[factor]:
                    ranking[factor] = result.metrics[factor][metric]
            result.rankings[metric] = ranking

        # 计算综合评分
        result.composite_scores = self._calculate_composite_scores(
            result.metrics,
            weights,
        )

        duration = time.time() - start_time
        GLOG.INFO(f"因子比较完成: 耗时 {duration:.2f}s")

        self._result = result
        return result

    def _calculate_factor_metrics(self, factor: str) -> Dict[str, float]:
        """
        计算单个因子的指标

        Args:
            factor: 因子名

        Returns:
            指标字典
        """
        metrics = {}

        # 准备数据
        df = self.factor_data[[self.date_col, self.code_col, factor, self.return_col]].copy()
        df = df.dropna()

        # 计算 IC 序列
        ic_values = []
        for date, group in df.groupby(self.date_col):
            if len(group) < 5:
                continue

            x = group[factor].values
            y = group[self.return_col].values

            # 移除 NaN
            mask = ~(np.isnan(x) | np.isnan(y))
            x, y = x[mask], y[mask]

            if len(x) >= 5:
                ic, _ = scipy_stats.spearmanr(x, y)
                if not np.isnan(ic):
                    ic_values.append(ic)

        if ic_values:
            # IC 统计
            metrics["ic_mean"] = float(np.mean(ic_values))
            metrics["ic_std"] = float(np.std(ic_values))
            metrics["icir"] = float(np.mean(ic_values) / np.std(ic_values)) if np.std(ic_values) > 0 else 0
            metrics["ic_positive_ratio"] = float(np.sum(np.array(ic_values) > 0) / len(ic_values))

        # 计算分层收益 (简化版：按分位数分组)
        try:
            df["group"] = df.groupby(self.date_col)[factor].transform(
                lambda x: pd.qcut(x, q=5, labels=False, duplicates="drop")
            )

            # 多空收益
            top_returns = df[df["group"] == df["group"].max()].groupby(self.date_col)[self.return_col].mean()
            bottom_returns = df[df["group"] == df["group"].min()].groupby(self.date_col)[self.return_col].mean()

            if len(top_returns) > 0 and len(bottom_returns) > 0:
                long_short = top_returns.mean() - bottom_returns.mean()
                metrics["long_short_return"] = float(long_short)

                # 计算单调性
                group_returns = df.groupby("group")[self.return_col].mean()
                if len(group_returns) >= 2:
                    x = np.arange(len(group_returns))
                    y = group_returns.values
                    slope, intercept, r_value, p_value, std_err = scipy_stats.linregress(x, y)
                    metrics["monotonicity"] = float(r_value ** 2)
        except Exception:
            pass

        return metrics

    def _calculate_composite_scores(
        self,
        metrics: Dict[str, Dict[str, float]],
        weights: Dict[str, float],
    ) -> Dict[str, float]:
        """
        计算综合评分

        Args:
            metrics: 各因子指标
            weights: 指标权重

        Returns:
            因子综合评分
        """
        scores = {}

        # 归一化每个指标
        normalized = {}
        for metric in weights.keys():
            values = {}
            for factor, factor_metrics in metrics.items():
                if metric in factor_metrics:
                    values[factor] = factor_metrics[metric]

            if values:
                # Min-Max 归一化
                min_val = min(values.values())
                max_val = max(values.values())
                range_val = max_val - min_val

                for factor, val in values.items():
                    if factor not in normalized:
                        normalized[factor] = {}
                    if range_val > 0:
                        normalized[factor][metric] = (val - min_val) / range_val
                    else:
                        normalized[factor][metric] = 0.5

        # 计算加权得分
        for factor in metrics.keys():
            score = 0.0
            total_weight = 0.0

            for metric, weight in weights.items():
                if factor in normalized and metric in normalized[factor]:
                    score += normalized[factor][metric] * weight
                    total_weight += weight

            if total_weight > 0:
                scores[factor] = score / total_weight
            else:
                scores[factor] = 0.0

        return scores

    def get_result(self) -> Optional[FactorComparisonResult]:
        """获取比较结果"""
        return self._result
