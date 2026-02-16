# Upstream: ginkgo.data.cruds, pandas, numpy, scipy
# Downstream: ginkgo.client, ginkgo.trading.strategies
# Role: IC 分析器 - 计算因子 IC，生成统计指标

"""
ICAnalyzer - IC 分析器

计算因子与未来收益的相关性 (IC)，生成统计指标。

核心功能:
- 计算 Pearson IC (线性相关)
- 计算 Rank IC (Spearman 相关系数)
- 计算 IC 统计指标: mean, std, ICIR, t-stat, p-value
- 支持多周期分析

Usage:
    from ginkgo.research.ic_analysis import ICAnalyzer
    import pandas as pd

    factor_df = pd.DataFrame({
        "date": [...], "code": [...], "factor_value": [...]
    })
    return_df = pd.DataFrame({
        "date": [...], "code": [...], "return_1d": [...], "return_5d": [...]
    })

    analyzer = ICAnalyzer(factor_df, return_df)
    result = analyzer.analyze(periods=[1, 5, 10], method="spearman")
    stats = analyzer.get_statistics(period=5)
    print(f"ICIR: {stats.icir}")
"""

from datetime import datetime
from decimal import Decimal
from typing import Optional, List, Dict, Any, Tuple, Union
import uuid

import pandas as pd
import numpy as np
from scipy import stats as scipy_stats

from ginkgo.research.models import ICStatistics, ICAnalysisResult
from ginkgo.libs import GLOG


class ICAnalyzer:
    """
    IC 分析器

    计算因子 IC，生成统计指标。

    Attributes:
        factor_data: 因子数据 DataFrame
        return_data: 收益数据 DataFrame
        factor_col: 因子列名
        return_col_template: 收益列模板
    """

    def __init__(
        self,
        factor_data: pd.DataFrame,
        return_data: pd.DataFrame,
        factor_col: str = "factor_value",
        return_col: str = None,
        date_col: str = "date",
        code_col: str = "code",
    ):
        """
        初始化 IC 分析器

        Args:
            factor_data: 因子数据，必须包含 date, code, factor_value 列
            return_data: 收益数据，必须包含 date, code, return_Nd 列
            factor_col: 因子值列名
            return_col: 收益列名 (可选，用于单周期分析)
            date_col: 日期列名
            code_col: 股票代码列名

        Raises:
            ValueError: 如果缺少必需列
        """
        # 验证因子数据
        required_factor_cols = [date_col, code_col, factor_col]
        missing = [c for c in required_factor_cols if c not in factor_data.columns]
        if missing:
            raise ValueError(f"因子数据缺少必需列: {missing}")

        # 验证收益数据
        required_return_cols = [date_col, code_col]
        missing = [c for c in required_return_cols if c not in return_data.columns]
        if missing:
            raise ValueError(f"收益数据缺少必需列: {missing}")

        self.factor_data = factor_data.copy()
        self.return_data = return_data.copy()
        self.factor_col = factor_col
        self.date_col = date_col
        self.code_col = code_col
        self._return_col = return_col

        # 缓存分析结果
        self._result: Optional[ICAnalysisResult] = None

        GLOG.INFO(f"ICAnalyzer 初始化: 因子数据 {len(factor_data)} 行, 收益数据 {len(return_data)} 行")

    def analyze(
        self,
        periods: List[int] = [1, 5, 10, 20],
        method: str = "spearman",
    ) -> ICAnalysisResult:
        """
        执行 IC 分析

        Args:
            periods: 分析周期列表 (天数)
            method: IC 计算方法 ("pearson" 或 "spearman")

        Returns:
            ICAnalysisResult 分析结果
        """
        result = ICAnalysisResult(periods=periods)

        ic_series: Dict[int, List[float]] = {}
        rank_ic_series: Dict[int, List[float]] = {}

        for period in periods:
            return_col = self._return_col or f"return_{period}d"

            if return_col not in self.return_data.columns:
                GLOG.WARN(f"缺少收益列: {return_col}，跳过周期 {period}")
                continue

            # 计算每期的 IC
            ic_values, rank_ic_values = self._calculate_ic_series(
                period=period,
                return_col=return_col,
                method=method,
            )

            ic_series[period] = ic_values
            if rank_ic_values:
                rank_ic_series[period] = rank_ic_values

            # 计算统计指标 - 使用 IC 或 Rank IC
            values_to_use = ic_values if ic_values else rank_ic_values
            if values_to_use:
                stats = self._calculate_statistics(values_to_use)
                result.statistics[period] = stats

        result.ic_series = ic_series
        result.rank_ic_series = rank_ic_series

        # 设置日期范围
        dates = self.factor_data[self.date_col].unique()
        if len(dates) > 0:
            dates_sorted = sorted(dates)
            result.date_range = (str(dates_sorted[0]), str(dates_sorted[-1]))

        self._result = result
        GLOG.INFO(f"IC 分析完成: {len(periods)} 个周期, {len(ic_series)} 个有效周期")
        return result

    def _calculate_ic_series(
        self,
        period: int,
        return_col: str,
        method: str,
    ) -> Tuple[List[float], List[float]]:
        """
        计算 IC 序列

        Args:
            period: 周期
            return_col: 收益列名
            method: 计算方法

        Returns:
            (IC 序列, Rank IC 序列)
        """
        ic_values = []
        rank_ic_values = []

        # 合并因子和收益数据
        merged = pd.merge(
            self.factor_data[[self.date_col, self.code_col, self.factor_col]],
            self.return_data[[self.date_col, self.code_col, return_col]],
            on=[self.date_col, self.code_col],
            how="inner",
        )

        # 按日期分组计算 IC
        for date, group in merged.groupby(self.date_col):
            factor_vals = group[self.factor_col].values
            return_vals = group[return_col].values

            # 移除 NaN
            mask = ~(np.isnan(factor_vals) | np.isnan(return_vals))
            factor_vals = factor_vals[mask]
            return_vals = return_vals[mask]

            if len(factor_vals) < 5:  # 样本太少
                continue

            try:
                # Pearson IC
                if method in ("pearson", "both"):
                    ic, _ = scipy_stats.pearsonr(factor_vals, return_vals)
                    if not np.isnan(ic):
                        ic_values.append(float(ic))

                # Spearman IC (Rank IC)
                if method in ("spearman", "both"):
                    rank_ic, _ = scipy_stats.spearmanr(factor_vals, return_vals)
                    if not np.isnan(rank_ic):
                        rank_ic_values.append(float(rank_ic))

            except Exception as e:
                GLOG.WARN(f"计算 IC 失败 ({date}): {e}")
                continue

        return ic_values, rank_ic_values

    def _calculate_statistics(self, ic_values: List[float]) -> ICStatistics:
        """
        计算统计指标

        Args:
            ic_values: IC 值列表

        Returns:
            ICStatistics 统计指标
        """
        if not ic_values:
            return ICStatistics()

        ic_array = np.array(ic_values)
        n = len(ic_array)

        mean_val = np.mean(ic_array)
        std_val = np.std(ic_array, ddof=1) if n > 1 else 0
        abs_mean = np.mean(np.abs(ic_array))

        # ICIR
        icir = mean_val / std_val if std_val != 0 else 0

        # t 统计量
        t_stat = mean_val / (std_val / np.sqrt(n)) if std_val != 0 else 0

        # p 值 (双尾检验)
        p_value = 2 * (1 - scipy_stats.t.cdf(abs(t_stat), df=n - 1)) if n > 1 else 1

        # 正向 IC 比例
        pos_ratio = np.sum(ic_array > 0) / n

        return ICStatistics(
            mean=Decimal(str(round(mean_val, 6))),
            std=Decimal(str(round(std_val, 6))),
            icir=Decimal(str(round(icir, 4))),
            t_stat=Decimal(str(round(t_stat, 4))),
            p_value=Decimal(str(round(p_value, 4))),
            pos_ratio=Decimal(str(round(pos_ratio, 4))),
            abs_mean=Decimal(str(round(abs_mean, 6))),
            count=n,
        )

    def get_statistics(self, period: int) -> Optional[ICStatistics]:
        """
        获取指定周期的统计指标

        Args:
            period: 周期

        Returns:
            ICStatistics 或 None
        """
        if self._result is None:
            GLOG.WARN("请先调用 analyze() 方法")
            return None

        return self._result.statistics.get(period)

    def get_ic_series(self, period: int) -> Optional[List[float]]:
        """
        获取指定周期的 IC 序列

        Args:
            period: 周期

        Returns:
            IC 序列或 None
        """
        if self._result is None:
            return None

        return self._result.ic_series.get(period)

    def get_summary(self) -> Dict[str, Any]:
        """
        获取分析摘要

        Returns:
            摘要字典
        """
        if self._result is None:
            return {"status": "not_analyzed"}

        return self._result.get_statistics_summary()

    def to_dataframe(self) -> Optional[pd.DataFrame]:
        """
        转换为 DataFrame

        Returns:
            IC 序列 DataFrame
        """
        if self._result is None:
            return None

        return self._result.to_dataframe()
