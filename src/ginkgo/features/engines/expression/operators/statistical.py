# Upstream: External Applications
# Downstream: Trading Strategies, Analysis Tools
# Role: 定义统计学表达式操作符提供variance_operator/stddev_operator/skew_operator等方法






"""
Statistical Operators - 统计函数操作符

提供各种统计分析函数，用于时间序列数据的统计计算。
"""

import pandas as pd
import numpy as np
from ginkgo.features.engines.expression.registry import register_operator, _extract_window, _extract_periods
from ginkgo.libs import GLOG


@register_operator("Variance", "Rolling variance", min_args=2, max_args=2)
def variance_operator(data: pd.DataFrame, series: pd.Series, window: pd.Series) -> pd.Series:
    """滚动方差"""
    window_size = _extract_window(window)
    
    return series.rolling(window=window_size, min_periods=1).var()


@register_operator("Skew", "Rolling skewness", min_args=2, max_args=2)
def skew_operator(data: pd.DataFrame, series: pd.Series, window: pd.Series) -> pd.Series:
    """滚动偏度"""
    window_size = _extract_window(window)
    
    return series.rolling(window=window_size, min_periods=3).skew()


@register_operator("Kurt", "Rolling kurtosis", min_args=2, max_args=2)
def kurt_operator(data: pd.DataFrame, series: pd.Series, window: pd.Series) -> pd.Series:
    """滚动峰度"""
    window_size = _extract_window(window)
    
    return series.rolling(window=window_size, min_periods=4).kurt()


@register_operator("Median", "Rolling median", min_args=2, max_args=2)
def median_operator(data: pd.DataFrame, series: pd.Series, window: pd.Series) -> pd.Series:
    """滚动中位数"""
    window_size = _extract_window(window)
    
    return series.rolling(window=window_size, min_periods=1).median()


@register_operator("Count", "Rolling count of non-null values", min_args=2, max_args=2)
def count_operator(data: pd.DataFrame, series: pd.Series, window: pd.Series) -> pd.Series:
    """滚动非空值计数"""
    window_size = _extract_window(window)
    
    return series.rolling(window=window_size).count()


@register_operator("Zscore", "Rolling z-score", min_args=2, max_args=2)
def zscore_operator(data: pd.DataFrame, series: pd.Series, window: pd.Series) -> pd.Series:
    """滚动Z分数标准化"""
    window_size = _extract_window(window)
    
    rolling_mean = series.rolling(window=window_size, min_periods=1).mean()
    rolling_std = series.rolling(window=window_size, min_periods=1).std()
    
    # 避免除零
    with np.errstate(divide='ignore', invalid='ignore'):
        zscore = (series - rolling_mean) / rolling_std
        return zscore.replace([np.inf, -np.inf], np.nan)
        


@register_operator("Percentile", "Rolling percentile", min_args=3, max_args=3)
def percentile_operator(data: pd.DataFrame, series: pd.Series, window: pd.Series, percentile: pd.Series) -> pd.Series:
    """滚动百分位数"""
    window_size = _extract_window(window)
    pct = float(percentile.iloc[0]) if len(percentile) > 0 else 50

    if not 0 <= pct <= 100:
        raise ValueError(f"Percentile must be between 0 and 100, got {pct}")

    return series.rolling(window=window_size, min_periods=1).quantile(pct / 100.0)


@register_operator("Corr", "Rolling correlation", min_args=3, max_args=3)
def corr_operator(data: pd.DataFrame, series1: pd.Series, series2: pd.Series, window: pd.Series) -> pd.Series:
    """滚动相关系数"""
    window_size = _extract_window(window)
    
    return series1.rolling(window=window_size, min_periods=2).corr(series2)


@register_operator("Cov", "Rolling covariance", min_args=3, max_args=3)
def cov_operator(data: pd.DataFrame, series1: pd.Series, series2: pd.Series, window: pd.Series) -> pd.Series:
    """滚动协方差"""
    window_size = _extract_window(window)
    
    return series1.rolling(window=window_size, min_periods=2).cov(series2)


@register_operator("AutoCorr", "Rolling autocorrelation", min_args=3, max_args=3)
def autocorr_operator(data: pd.DataFrame, series: pd.Series, lag: pd.Series, window: pd.Series) -> pd.Series:
    """滚动自相关"""
    lag_periods = _extract_periods(lag, allow_negative=False)
    window_size = _extract_window(window)

    lagged_series = series.shift(lag_periods)
    return series.rolling(window=window_size, min_periods=2).corr(lagged_series)


@register_operator("Rank", "Rolling rank calculation", min_args=2, max_args=2)
def rank_operator(data: pd.DataFrame, series: pd.Series, window: pd.Series) -> pd.Series:
    """滚动排名计算"""
    window_size = _extract_window(window)
    
    # 计算滚动排名（百分位）
    result = series.rolling(window=window_size).rank(pct=True)
    return result
    


@register_operator("QTLU", "Upper quantile (75th percentile)", min_args=2, max_args=2)
def qtlu_operator(data: pd.DataFrame, series: pd.Series, window: pd.Series) -> pd.Series:
    """上分位数（75%分位数）"""
    window_size = _extract_window(window)
    
    return series.rolling(window=window_size).quantile(0.75)
    


@register_operator("QTLD", "Lower quantile (25th percentile)", min_args=2, max_args=2)
def qtld_operator(data: pd.DataFrame, series: pd.Series, window: pd.Series) -> pd.Series:
    """下分位数（25%分位数）"""
    window_size = _extract_window(window)
    
    return series.rolling(window=window_size).quantile(0.25)
    


@register_operator("IMAX", "Index of maximum value", min_args=2, max_args=2)
def imax_operator(data: pd.DataFrame, series: pd.Series, window: pd.Series) -> pd.Series:
    """最大值位置索引"""
    window_size = _extract_window(window)
    
    # 计算滚动窗口内最大值的位置索引
    result = series.rolling(window=window_size).apply(lambda x: len(x) - 1 - np.argmax(x.values) if len(x) > 0 and not np.isnan(x.values).all() else np.nan)
    return result
    


@register_operator("IMIN", "Index of minimum value", min_args=2, max_args=2)
def imin_operator(data: pd.DataFrame, series: pd.Series, window: pd.Series) -> pd.Series:
    """最小值位置索引"""
    window_size = _extract_window(window)
    
    # 计算滚动窗口内最小值的位置索引
    result = series.rolling(window=window_size).apply(lambda x: len(x) - 1 - np.argmin(x.values) if len(x) > 0 and not np.isnan(x.values).all() else np.nan)
    return result
    