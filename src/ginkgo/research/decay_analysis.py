# Upstream: numpy, pandas, scipy, ginkgo.research.models
# Downstream: ginkgo.client.research_cli
# Role: 因子衰减分析 - 计算滞后 IC 和半衰期

"""
FactorDecayAnalyzer - 因子衰减分析

计算不同滞后期的 IC，分析因子信息衰减特征。

核心功能:
- 计算不同滞后期的 IC
- 计算半衰期 (IC 衰减到一半的时间)
- 生成衰减曲线

Usage:
    from ginkgo.research.decay_analysis import FactorDecayAnalyzer
    import pandas as pd

    factor_data = pd.DataFrame({
        "date": [...], "code": [...], "factor_value": [...]
    })
    return_data = pd.DataFrame({
        "date": [...], "code": [...], "return": [...]
    })

    analyzer = FactorDecayAnalyzer(factor_data, return_data)
    result = analyzer.analyze(max_lag=20)
    print(f"半衰期: {result.half_life:.1f} 天")
"""

from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal
from typing import Optional, List, Dict, Any, Tuple
import time

import numpy as np
import pandas as pd
from scipy import stats as scipy_stats
from scipy.optimize import curve_fit

from ginkgo.libs import GLOG


@dataclass
class DecayAnalysisResult:
    """
    因子衰减分析结果

    存储因子衰减分析的完整结果。

    Attributes:
        factor_name: 因子名称
        lag_ic: 滞后期 IC 字典 {lag: ic_value}
        half_life: 半衰期
    """

    factor_name: str
    lag_ic: Dict[int, float] = field(default_factory=dict)
    half_life: Optional[float] = None
    decay_rate: Optional[float] = None
    optimal_lag: Optional[int] = None
    created_at: Optional[datetime] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        """初始化后处理"""
        if self.created_at is None:
            self.created_at = datetime.now()

    def to_dict(self) -> Dict[str, Any]:
        """序列化为字典"""
        return {
            "factor_name": self.factor_name,
            "lag_ic": self.lag_ic,
            "half_life": self.half_life,
            "decay_rate": self.decay_rate,
            "optimal_lag": self.optimal_lag,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "metadata": self.metadata,
        }


class FactorDecayAnalyzer:
    """
    因子衰减分析器

    分析因子 IC 随时间的衰减特征。

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
        初始化因子衰减分析器

        Args:
            factor_data: 因子数据
            return_data: 收益数据
            factor_col: 因子列名
            return_col: 收益列名
            date_col: 日期列名
            code_col: 股票代码列名
        """
        self.factor_data = factor_data.copy()
        self.return_data = return_data.copy()
        self.factor_col = factor_col
        self.return_col = return_col
        self.date_col = date_col
        self.code_col = code_col

        self._result: Optional[DecayAnalysisResult] = None
        self._lag_ic_cache: Dict[int, float] = {}

        GLOG.INFO("FactorDecayAnalyzer 初始化")

    def calculate_lag_ic(self, max_lag: int = 20) -> Dict[int, float]:
        """
        计算不同滞后期的 IC

        Args:
            max_lag: 最大滞后期

        Returns:
            滞后期 IC 字典
        """
        if self._lag_ic_cache and max(self._lag_ic_cache.keys()) >= max_lag:
            return {k: v for k, v in self._lag_ic_cache.items() if k <= max_lag}

        GLOG.INFO(f"计算滞后 IC: 最大滞后期 {max_lag}")

        # 确保日期是日期类型
        factor_copy = self.factor_data.copy()
        return_copy = self.return_data.copy()

        factor_copy[self.date_col] = pd.to_datetime(factor_copy[self.date_col])
        return_copy[self.date_col] = pd.to_datetime(return_copy[self.date_col])

        # 获取唯一日期并排序
        factor_dates = sorted(factor_copy[self.date_col].unique())

        lag_ic = {}

        for lag in range(1, max_lag + 1):
            ic_values = []

            for i, date in enumerate(factor_dates[:-lag]):
                # 获取当日因子值
                factor_day = factor_copy[factor_copy[self.date_col] == date]

                # 获取滞后 lag 天的收益
                future_date = factor_dates[i + lag] if i + lag < len(factor_dates) else None
                if future_date is None:
                    continue

                return_day = return_copy[return_copy[self.date_col] == future_date]

                # 合并
                merged = pd.merge(
                    factor_day[[self.code_col, self.factor_col]],
                    return_day[[self.code_col, self.return_col]],
                    on=self.code_col,
                    how="inner",
                )

                if len(merged) < 5:
                    continue

                # 计算 Spearman IC
                x = merged[self.factor_col].values
                y = merged[self.return_col].values

                mask = ~(np.isnan(x) | np.isnan(y))
                x, y = x[mask], y[mask]

                if len(x) >= 5:
                    ic, _ = scipy_stats.spearmanr(x, y)
                    if not np.isnan(ic):
                        ic_values.append(ic)

            if ic_values:
                lag_ic[lag] = float(np.mean(ic_values))
                self._lag_ic_cache[lag] = lag_ic[lag]

        return lag_ic

    def analyze(self, max_lag: int = 20) -> DecayAnalysisResult:
        """
        执行因子衰减分析

        Args:
            max_lag: 最大滞后期

        Returns:
            DecayAnalysisResult 分析结果
        """
        start_time = time.time()

        GLOG.INFO(f"开始因子衰减分析: 最大滞后期 {max_lag}")

        # 计算滞后 IC
        lag_ic = self.calculate_lag_ic(max_lag)

        result = DecayAnalysisResult(
            factor_name=self.factor_col,
            lag_ic=lag_ic,
        )

        # 计算半衰期
        if lag_ic:
            result.half_life = self._calculate_half_life(lag_ic)
            result.decay_rate = self._estimate_decay_rate(lag_ic)

            # 找到最优滞后期 (IC 绝对值最大)
            optimal_lag = max(lag_ic.keys(), key=lambda k: abs(lag_ic[k]))
            result.optimal_lag = optimal_lag

        duration = time.time() - start_time
        GLOG.INFO(
            f"因子衰减分析完成: 半衰期 {result.half_life}, "
            f"最优滞后期 {result.optimal_lag}, 耗时 {duration:.2f}s"
        )

        self._result = result
        return result

    def _calculate_half_life(self, lag_ic: Dict[int, float]) -> Optional[float]:
        """
        计算半衰期

        使用指数衰减模型拟合 IC 序列。

        Args:
            lag_ic: 滞后期 IC 字典

        Returns:
            半衰期 (天数)
        """
        if len(lag_ic) < 3:
            return None

        lags = np.array(sorted(lag_ic.keys()))
        ics = np.array([lag_ic[lag] for lag in lags])

        # 取绝对值
        abs_ics = np.abs(ics)

        # 初始 IC
        initial_ic = abs_ics[0]
        if initial_ic <= 0:
            return None

        # 寻找 IC 衰减到一半的滞后期
        half_ic = initial_ic / 2

        for i, (lag, ic) in enumerate(zip(lags, abs_ics)):
            if ic <= half_ic:
                # 线性插值
                if i > 0:
                    prev_lag = lags[i - 1]
                    prev_ic = abs_ics[i - 1]
                    slope = (ic - prev_ic) / (lag - prev_lag)
                    if slope != 0:
                        interpolated_lag = prev_lag + (half_ic - prev_ic) / slope
                        return float(interpolated_lag)
                return float(lag)

        # 如果没有衰减到一半，使用指数拟合外推
        try:
            def decay_func(t, a, b):
                return a * np.exp(-b * t)

            # 只使用正 IC 值进行拟合
            positive_mask = abs_ics > 0
            if np.sum(positive_mask) >= 3:
                popt, _ = curve_fit(
                    decay_func,
                    lags[positive_mask],
                    abs_ics[positive_mask],
                    p0=[initial_ic, 0.1],
                    maxfev=1000,
                )
                a, b = popt
                if b > 0:
                    half_life = np.log(2) / b
                    return float(half_life)
        except Exception:
            pass

        return None

    def _estimate_decay_rate(self, lag_ic: Dict[int, float]) -> Optional[float]:
        """
        估计衰减率

        Args:
            lag_ic: 滞后期 IC 字典

        Returns:
            衰减率
        """
        if len(lag_ic) < 2:
            return None

        lags = np.array(sorted(lag_ic.keys()))
        ics = np.array([abs(lag_ic[lag]) for lag in lags])

        # 使用线性回归估计衰减
        slope, intercept, r_value, p_value, std_err = scipy_stats.linregress(lags, ics)

        # 衰减率 = 斜率 / 截距 (归一化)
        if intercept > 0:
            return float(-slope / intercept)

        return None

    def get_decay_curve(self) -> pd.DataFrame:
        """
        获取衰减曲线

        Returns:
            滞后期 IC DataFrame
        """
        if self._result is None:
            return pd.DataFrame()

        return pd.DataFrame({
            "lag": list(self._result.lag_ic.keys()),
            "ic": list(self._result.lag_ic.values()),
        }).sort_values("lag")
