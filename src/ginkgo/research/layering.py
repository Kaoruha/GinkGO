# Upstream: ginkgo.data.cruds, pandas, numpy, scipy
# Downstream: ginkgo.client, ginkgo.trading.strategies
# Role: 因子分层分析 - 按因子值分组，计算各组收益

"""
FactorLayering - 因子分层分析

按因子值分位数分组，计算各组收益，评估因子区分度。

核心功能:
- 按因子值分位数分组 (等分或自定义)
- 计算各组平均收益
- 计算多空收益 (最高组 - 最低组)
- 计算单调性 (R²)

Usage:
    from ginkgo.research.layering import FactorLayering
    import pandas as pd

    factor_df = pd.DataFrame({
        "date": [...], "code": [...], "factor_value": [...]
    })
    return_df = pd.DataFrame({
        "date": [...], "code": [...], "return": [...]
    })

    layering = FactorLayering(factor_df, return_df)
    result = layering.run(n_groups=5)
    print(f"多空收益: {result.spread}")
    print(f"单调性: {result.get_monotonicity()}")
"""

from datetime import datetime
from decimal import Decimal
from typing import Optional, List, Dict, Any, Tuple
import uuid

import pandas as pd
import numpy as np
from scipy import stats as scipy_stats

from ginkgo.research.models import LayerGroup, LayeringResult, LayeringStatistics
from ginkgo.libs import GLOG


class FactorLayering:
    """
    因子分层分析

    按因子值分位数分组，计算各组收益，评估因子区分度。

    Attributes:
        factor_data: 因子数据 DataFrame
        return_data: 收益数据 DataFrame
    """

    def __init__(
        self,
        factor_data: pd.DataFrame,
        return_data: pd.DataFrame,
        factor_col: str = "factor_value",
        return_col: str = "return",
        date_col: str = "date",
        code_col: str = "code",
    ):
        """
        初始化因子分层分析

        Args:
            factor_data: 因子数据，必须包含 date, code, factor_value 列
            return_data: 收益数据，必须包含 date, code, return 列
            factor_col: 因子值列名
            return_col: 收益列名
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
        required_return_cols = [date_col, code_col, return_col]
        missing = [c for c in required_return_cols if c not in return_data.columns]
        if missing:
            raise ValueError(f"收益数据缺少必需列: {missing}")

        self.factor_data = factor_data.copy()
        self.return_data = return_data.copy()
        self.factor_col = factor_col
        self.return_col = return_col
        self.date_col = date_col
        self.code_col = code_col

        # 缓存结果
        self._result: Optional[LayeringResult] = None
        self._group_returns: Dict[int, List[float]] = {}

        GLOG.INFO(f"FactorLayering 初始化: 因子数据 {len(factor_data)} 行, 收益数据 {len(return_data)} 行")

    def run(
        self,
        n_groups: int = 5,
        rebalance_freq: int = 20,
    ) -> LayeringResult:
        """
        执行因子分层分析

        Args:
            n_groups: 分组数 (默认 5 组)
            rebalance_freq: 调仓频率 (天数，默认 20)

        Returns:
            LayeringResult 分层结果
        """
        result = LayeringResult(n_groups=n_groups)

        # 合并因子和收益数据
        merged = pd.merge(
            self.factor_data[[self.date_col, self.code_col, self.factor_col]],
            self.return_data[[self.date_col, self.code_col, self.return_col]],
            on=[self.date_col, self.code_col],
            how="inner",
        )

        if merged.empty:
            GLOG.WARN("合并后数据为空")
            return result

        # 初始化各组
        for i in range(1, n_groups + 1):
            result.groups[i] = LayerGroup(
                group_id=i,
                name=f"Q{i}",
            )

        # 按日期分组处理
        dates = sorted(merged[self.date_col].unique())
        group_returns_all: Dict[int, List[float]] = {i: [] for i in range(1, n_groups + 1)}

        for date in dates:
            day_data = merged[merged[self.date_col] == date].copy()

            if len(day_data) < n_groups:
                continue

            # 按因子值分组
            try:
                day_data["group"] = pd.qcut(
                    day_data[self.factor_col],
                    q=n_groups,
                    labels=False,
                    duplicates="drop",
                )
            except ValueError:
                # 如果分位数相同，跳过
                continue

            # 计算各组收益
            for group_id in range(n_groups):
                group_mask = day_data["group"] == group_id
                group_data = day_data[group_mask]

                if not group_data.empty:
                    group_return = group_data[self.return_col].mean()
                    group_returns_all[group_id + 1].append(group_return)

        # 计算各组统计
        for group_id in range(1, n_groups + 1):
            returns = group_returns_all[group_id]
            if returns:
                result.groups[group_id].mean_return = Decimal(str(round(np.mean(returns), 6)))
                result.groups[group_id].std_return = Decimal(str(round(np.std(returns), 6))) if len(returns) > 1 else Decimal("0")
                result.groups[group_id].count = len(returns)
                result.groups[group_id].returns = returns

        # 计算多空收益差
        if n_groups >= 2:
            top_return = result.groups[n_groups].mean_return
            bottom_return = result.groups[1].mean_return
            result.spread = top_return - bottom_return

        # 设置日期范围
        if dates:
            result.date_range = (str(dates[0]), str(dates[-1]))

        # 计算统计指标
        result.statistics = self._calculate_statistics(result, group_returns_all)

        self._result = result
        self._group_returns = group_returns_all

        GLOG.INFO(f"因子分层完成: {n_groups} 组")
        return result

    def _calculate_statistics(
        self,
        result: LayeringResult,
        group_returns: Dict[int, List[float]],
    ) -> LayeringStatistics:
        """
        计算分层统计指标

        Args:
            result: 分层结果
            group_returns: 各组收益序列

        Returns:
            LayeringStatistics 统计指标
        """
        stats = LayeringStatistics()

        # 多空收益
        stats.long_short_total_return = result.spread

        # 计算多空收益序列
        n_groups = result.n_groups
        if n_groups >= 2 and group_returns.get(n_groups) and group_returns.get(1):
            top_returns = group_returns[n_groups]
            bottom_returns = group_returns[1]

            # 对齐长度
            min_len = min(len(top_returns), len(bottom_returns))
            if min_len > 0:
                long_short_returns = [
                    top_returns[i] - bottom_returns[i]
                    for i in range(min_len)
                ]

                # 夏普比率
                if len(long_short_returns) > 1 and np.std(long_short_returns) > 0:
                    stats.long_short_sharpe = Decimal(str(round(
                        np.mean(long_short_returns) / np.std(long_short_returns) * np.sqrt(252),
                        4
                    )))

                # 胜率
                wins = sum(1 for r in long_short_returns if r > 0)
                stats.win_rate = Decimal(str(round(wins / len(long_short_returns), 4)))

        # 单调性 R²
        stats.monotonicity_r2 = Decimal(str(round(self.calculate_monotonicity(), 4)))

        return stats

    def calculate_monotonicity(self) -> float:
        """
        计算单调性 R²

        Returns:
            R² 值 (0-1)
        """
        if self._result is None or not self._result.groups:
            return 0.0

        groups = self._result.groups
        n_groups = len(groups)

        if n_groups < 2:
            return 0.0

        # 获取各组平均收益
        sorted_groups = sorted(groups.items(), key=lambda x: x[0])
        x = np.array(range(1, n_groups + 1))
        y = np.array([float(g.mean_return) for _, g in sorted_groups])

        # 线性回归计算 R²
        try:
            slope, intercept, r_value, p_value, std_err = scipy_stats.linregress(x, y)
            return r_value ** 2
        except Exception:
            return 0.0

    def get_group_statistics(self) -> Dict[str, Any]:
        """
        获取分组统计信息

        Returns:
            统计信息字典
        """
        if self._result is None:
            return {}

        stats = {
            "mean_returns": {},
            "std_returns": {},
            "counts": {},
        }

        for group_id, group in self._result.groups.items():
            stats["mean_returns"][group_id] = float(group.mean_return)
            stats["std_returns"][group_id] = float(group.std_return)
            stats["counts"][group_id] = group.count

        return stats

    def to_dataframe(self) -> Optional[pd.DataFrame]:
        """
        转换为 DataFrame

        Returns:
            分组收益 DataFrame
        """
        if not self._group_returns:
            return None

        try:
            import pandas as pd
        except ImportError:
            return None

        # 找到最长的序列
        max_len = max(len(v) for v in self._group_returns.values())

        data = {}
        for group_id in sorted(self._group_returns.keys()):
            values = self._group_returns[group_id]
            padded = values + [None] * (max_len - len(values))
            data[f"Group_{group_id}"] = padded

        return pd.DataFrame(data)
