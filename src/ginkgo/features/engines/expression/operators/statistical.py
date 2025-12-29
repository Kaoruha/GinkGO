# Upstream: External Applications
# Downstream: Trading Strategies, Analysis Tools
# Role: 定义统计学表达式操作符提供variance_operator/stddev_operator/skew_operator等方法






"""
Statistical Operators - 统计函数操作符

提供各种统计分析函数，用于时间序列数据的统计计算。
"""

import pandas as pd
import numpy as np
from ginkgo.features.engines.expression.registry import register_operator
from ginkgo.libs import GLOG


@register_operator("Variance", "Rolling variance", min_args=2, max_args=2)
def variance_operator(data: pd.DataFrame, series: pd.Series, window: pd.Series) -> pd.Series:
    """滚动方差"""
    try:
        window_size = int(window.iloc[0]) if len(window) > 0 else 20
        if window_size <= 0:
            raise ValueError(f"Window size must be positive, got {window_size}")
        
        return series.rolling(window=window_size, min_periods=1).var()
    except Exception as e:
        GLOG.ERROR(f"Variance operator failed: {e}")
        return pd.Series([np.nan] * len(series), index=series.index)


@register_operator("Skew", "Rolling skewness", min_args=2, max_args=2)
def skew_operator(data: pd.DataFrame, series: pd.Series, window: pd.Series) -> pd.Series:
    """滚动偏度"""
    try:
        window_size = int(window.iloc[0]) if len(window) > 0 else 20
        if window_size <= 0:
            raise ValueError(f"Window size must be positive, got {window_size}")
        
        return series.rolling(window=window_size, min_periods=3).skew()
    except Exception as e:
        GLOG.ERROR(f"Skew operator failed: {e}")
        return pd.Series([np.nan] * len(series), index=series.index)


@register_operator("Kurt", "Rolling kurtosis", min_args=2, max_args=2)
def kurt_operator(data: pd.DataFrame, series: pd.Series, window: pd.Series) -> pd.Series:
    """滚动峰度"""
    try:
        window_size = int(window.iloc[0]) if len(window) > 0 else 20
        if window_size <= 0:
            raise ValueError(f"Window size must be positive, got {window_size}")
        
        return series.rolling(window=window_size, min_periods=4).kurt()
    except Exception as e:
        GLOG.ERROR(f"Kurt operator failed: {e}")
        return pd.Series([np.nan] * len(series), index=series.index)


@register_operator("Median", "Rolling median", min_args=2, max_args=2)
def median_operator(data: pd.DataFrame, series: pd.Series, window: pd.Series) -> pd.Series:
    """滚动中位数"""
    try:
        window_size = int(window.iloc[0]) if len(window) > 0 else 20
        if window_size <= 0:
            raise ValueError(f"Window size must be positive, got {window_size}")
        
        return series.rolling(window=window_size, min_periods=1).median()
    except Exception as e:
        GLOG.ERROR(f"Median operator failed: {e}")
        return pd.Series([np.nan] * len(series), index=series.index)


@register_operator("Count", "Rolling count of non-null values", min_args=2, max_args=2)
def count_operator(data: pd.DataFrame, series: pd.Series, window: pd.Series) -> pd.Series:
    """滚动非空值计数"""
    try:
        window_size = int(window.iloc[0]) if len(window) > 0 else 20
        if window_size <= 0:
            raise ValueError(f"Window size must be positive, got {window_size}")
        
        return series.rolling(window=window_size).count()
    except Exception as e:
        GLOG.ERROR(f"Count operator failed: {e}")
        return pd.Series([np.nan] * len(series), index=series.index)


@register_operator("Zscore", "Rolling z-score", min_args=2, max_args=2)
def zscore_operator(data: pd.DataFrame, series: pd.Series, window: pd.Series) -> pd.Series:
    """滚动Z分数标准化"""
    try:
        window_size = int(window.iloc[0]) if len(window) > 0 else 20
        if window_size <= 0:
            raise ValueError(f"Window size must be positive, got {window_size}")
        
        rolling_mean = series.rolling(window=window_size, min_periods=1).mean()
        rolling_std = series.rolling(window=window_size, min_periods=1).std()
        
        # 避免除零
        with np.errstate(divide='ignore', invalid='ignore'):
            zscore = (series - rolling_mean) / rolling_std
            return zscore.replace([np.inf, -np.inf], np.nan)
            
    except Exception as e:
        GLOG.ERROR(f"Zscore operator failed: {e}")
        return pd.Series([np.nan] * len(series), index=series.index)


@register_operator("Percentile", "Rolling percentile", min_args=3, max_args=3)
def percentile_operator(data: pd.DataFrame, series: pd.Series, window: pd.Series, percentile: pd.Series) -> pd.Series:
    """滚动百分位数"""
    try:
        window_size = int(window.iloc[0]) if len(window) > 0 else 20
        pct = float(percentile.iloc[0]) if len(percentile) > 0 else 50
        
        if window_size <= 0:
            raise ValueError(f"Window size must be positive, got {window_size}")
        if not 0 <= pct <= 100:
            raise ValueError(f"Percentile must be between 0 and 100, got {pct}")
        
        return series.rolling(window=window_size, min_periods=1).quantile(pct / 100.0)
    except Exception as e:
        GLOG.ERROR(f"Percentile operator failed: {e}")
        return pd.Series([np.nan] * len(series), index=series.index)


@register_operator("Corr", "Rolling correlation", min_args=3, max_args=3)
def corr_operator(data: pd.DataFrame, series1: pd.Series, series2: pd.Series, window: pd.Series) -> pd.Series:
    """滚动相关系数"""
    try:
        window_size = int(window.iloc[0]) if len(window) > 0 else 20
        if window_size <= 0:
            raise ValueError(f"Window size must be positive, got {window_size}")
        
        return series1.rolling(window=window_size, min_periods=2).corr(series2)
    except Exception as e:
        GLOG.ERROR(f"Corr operator failed: {e}")
        return pd.Series([np.nan] * len(series1), index=series1.index)


@register_operator("Cov", "Rolling covariance", min_args=3, max_args=3)
def cov_operator(data: pd.DataFrame, series1: pd.Series, series2: pd.Series, window: pd.Series) -> pd.Series:
    """滚动协方差"""
    try:
        window_size = int(window.iloc[0]) if len(window) > 0 else 20
        if window_size <= 0:
            raise ValueError(f"Window size must be positive, got {window_size}")
        
        return series1.rolling(window=window_size, min_periods=2).cov(series2)
    except Exception as e:
        GLOG.ERROR(f"Cov operator failed: {e}")
        return pd.Series([np.nan] * len(series1), index=series1.index)


@register_operator("AutoCorr", "Rolling autocorrelation", min_args=3, max_args=3)
def autocorr_operator(data: pd.DataFrame, series: pd.Series, lag: pd.Series, window: pd.Series) -> pd.Series:
    """滚动自相关"""
    try:
        lag_periods = int(lag.iloc[0]) if len(lag) > 0 else 1
        window_size = int(window.iloc[0]) if len(window) > 0 else 20
        
        if window_size <= 0:
            raise ValueError(f"Window size must be positive, got {window_size}")
        if lag_periods < 0:
            raise ValueError(f"Lag must be non-negative, got {lag_periods}")
        
        lagged_series = series.shift(lag_periods)
        return series.rolling(window=window_size, min_periods=2).corr(lagged_series)
    except Exception as e:
        GLOG.ERROR(f"AutoCorr operator failed: {e}")
        return pd.Series([np.nan] * len(series), index=series.index)


@register_operator("Rank", "Rolling rank calculation", min_args=2, max_args=2)
def rank_operator(data: pd.DataFrame, series: pd.Series, window: pd.Series) -> pd.Series:
    """滚动排名计算"""
    try:
        window_size = int(window.iloc[0]) if len(window) > 0 else 20
        if window_size <= 0:
            raise ValueError(f"Window size must be positive, got {window_size}")
        
        # 计算滚动排名（百分位）
        result = series.rolling(window=window_size).rank(pct=True)
        return result
        
    except Exception as e:
        GLOG.ERROR(f"Rank operator failed: {e}")
        return pd.Series([np.nan] * len(series), index=series.index)


@register_operator("QTLU", "Upper quantile (75th percentile)", min_args=2, max_args=2)
def qtlu_operator(data: pd.DataFrame, series: pd.Series, window: pd.Series) -> pd.Series:
    """上分位数（75%分位数）"""
    try:
        window_size = int(window.iloc[0]) if len(window) > 0 else 20
        if window_size <= 0:
            raise ValueError(f"Window size must be positive, got {window_size}")
        
        return series.rolling(window=window_size).quantile(0.75)
        
    except Exception as e:
        GLOG.ERROR(f"QTLU operator failed: {e}")
        return pd.Series([np.nan] * len(series), index=series.index)


@register_operator("QTLD", "Lower quantile (25th percentile)", min_args=2, max_args=2)
def qtld_operator(data: pd.DataFrame, series: pd.Series, window: pd.Series) -> pd.Series:
    """下分位数（25%分位数）"""
    try:
        window_size = int(window.iloc[0]) if len(window) > 0 else 20
        if window_size <= 0:
            raise ValueError(f"Window size must be positive, got {window_size}")
        
        return series.rolling(window=window_size).quantile(0.25)
        
    except Exception as e:
        GLOG.ERROR(f"QTLD operator failed: {e}")
        return pd.Series([np.nan] * len(series), index=series.index)


@register_operator("IMAX", "Index of maximum value", min_args=2, max_args=2)
def imax_operator(data: pd.DataFrame, series: pd.Series, window: pd.Series) -> pd.Series:
    """最大值位置索引"""
    try:
        window_size = int(window.iloc[0]) if len(window) > 0 else 20
        if window_size <= 0:
            raise ValueError(f"Window size must be positive, got {window_size}")
        
        # 计算滚动窗口内最大值的位置索引
        result = series.rolling(window=window_size).apply(lambda x: len(x) - 1 - np.argmax(x.values) if len(x) > 0 and not np.isnan(x.values).all() else np.nan)
        return result
        
    except Exception as e:
        GLOG.ERROR(f"IMAX operator failed: {e}")
        return pd.Series([np.nan] * len(series), index=series.index)


@register_operator("IMIN", "Index of minimum value", min_args=2, max_args=2)
def imin_operator(data: pd.DataFrame, series: pd.Series, window: pd.Series) -> pd.Series:
    """最小值位置索引"""
    try:
        window_size = int(window.iloc[0]) if len(window) > 0 else 20
        if window_size <= 0:
            raise ValueError(f"Window size must be positive, got {window_size}")
        
        # 计算滚动窗口内最小值的位置索引
        result = series.rolling(window=window_size).apply(lambda x: len(x) - 1 - np.argmin(x.values) if len(x) > 0 and not np.isnan(x.values).all() else np.nan)
        return result
        
    except Exception as e:
        GLOG.ERROR(f"IMIN operator failed: {e}")
        return pd.Series([np.nan] * len(series), index=series.index)