"""
Temporal Operators - 时序操作符

提供时间序列相关的操作函数，包括时间偏移、差分、趋势分析等。
"""

import pandas as pd
import numpy as np
from ginkgo.features.engines.expression.registry import register_operator
from ginkgo.libs import GLOG


@register_operator("Returns", "Calculate returns", min_args=1, max_args=2)
def returns_operator(data: pd.DataFrame, series: pd.Series, periods: pd.Series = None) -> pd.Series:
    """收益率计算"""
    try:
        shift_periods = 1
        if periods is not None and len(periods) > 0:
            shift_periods = int(periods.iloc[0])
        
        if shift_periods <= 0:
            raise ValueError(f"Periods must be positive, got {shift_periods}")
        
        prev_values = series.shift(shift_periods)
        with np.errstate(divide='ignore', invalid='ignore'):
            returns = (series - prev_values) / prev_values
            return returns.replace([np.inf, -np.inf], np.nan)
            
    except Exception as e:
        GLOG.ERROR(f"Returns operator failed: {e}")
        return pd.Series([np.nan] * len(series), index=series.index)


@register_operator("LogReturns", "Calculate log returns", min_args=1, max_args=2)
def log_returns_operator(data: pd.DataFrame, series: pd.Series, periods: pd.Series = None) -> pd.Series:
    """对数收益率计算"""
    try:
        shift_periods = 1
        if periods is not None and len(periods) > 0:
            shift_periods = int(periods.iloc[0])
        
        if shift_periods <= 0:
            raise ValueError(f"Periods must be positive, got {shift_periods}")
        
        prev_values = series.shift(shift_periods)
        with np.errstate(divide='ignore', invalid='ignore'):
            log_returns = np.log(series / prev_values)
            return pd.Series(log_returns, index=series.index).replace([np.inf, -np.inf], np.nan)
            
    except Exception as e:
        GLOG.ERROR(f"LogReturns operator failed: {e}")
        return pd.Series([np.nan] * len(series), index=series.index)


@register_operator("Pct_change", "Percentage change", min_args=1, max_args=2)
def pct_change_operator(data: pd.DataFrame, series: pd.Series, periods: pd.Series = None) -> pd.Series:
    """百分比变化"""
    try:
        shift_periods = 1
        if periods is not None and len(periods) > 0:
            shift_periods = int(periods.iloc[0])
        
        return series.pct_change(periods=shift_periods)
    except Exception as e:
        GLOG.ERROR(f"Pct_change operator failed: {e}")
        return pd.Series([np.nan] * len(series), index=series.index)


@register_operator("CumSum", "Cumulative sum", min_args=1, max_args=1)
def cumsum_operator(data: pd.DataFrame, series: pd.Series) -> pd.Series:
    """累积求和"""
    try:
        return series.cumsum()
    except Exception as e:
        GLOG.ERROR(f"CumSum operator failed: {e}")
        return pd.Series([np.nan] * len(series), index=series.index)


@register_operator("WMA", "Weighted Moving Average", min_args=2, max_args=2)
def wma_operator(data: pd.DataFrame, series: pd.Series, window: pd.Series) -> pd.Series:
    """加权移动平均"""
    try:
        window_size = int(window.iloc[0])
        if window_size <= 0:
            raise ValueError(f"Window size must be positive, got {window_size}")
        
        # 生成线性权重：最新数据权重最大
        weights = np.arange(1, window_size + 1)
        weights = weights / weights.sum()  # 标准化权重
        
        result = []
        for i in range(len(series)):
            if i < window_size - 1:
                # 数据不足，返回NaN
                result.append(np.nan)
            else:
                # 获取窗口数据
                window_data = series.iloc[i - window_size + 1:i + 1].values
                # 计算加权平均
                wma_value = np.sum(window_data * weights)
                result.append(wma_value)
        
        return pd.Series(result, index=series.index)
        
    except Exception as e:
        GLOG.ERROR(f"WMA operator failed: {e}")
        return pd.Series([np.nan] * len(series), index=series.index)


@register_operator("CumProd", "Cumulative product", min_args=1, max_args=1)
def cumprod_operator(data: pd.DataFrame, series: pd.Series) -> pd.Series:
    """累积乘积"""
    try:
        return series.cumprod()
    except Exception as e:
        GLOG.ERROR(f"CumProd operator failed: {e}")
        return pd.Series([np.nan] * len(series), index=series.index)


@register_operator("CumMax", "Cumulative maximum", min_args=1, max_args=1)
def cummax_operator(data: pd.DataFrame, series: pd.Series) -> pd.Series:
    """累积最大值"""
    try:
        return series.cummax()
    except Exception as e:
        GLOG.ERROR(f"CumMax operator failed: {e}")
        return pd.Series([np.nan] * len(series), index=series.index)


@register_operator("CumMin", "Cumulative minimum", min_args=1, max_args=1)
def cummin_operator(data: pd.DataFrame, series: pd.Series) -> pd.Series:
    """累积最小值"""
    try:
        return series.cummin()
    except Exception as e:
        GLOG.ERROR(f"CumMin operator failed: {e}")
        return pd.Series([np.nan] * len(series), index=series.index)


@register_operator("Expanding_mean", "Expanding mean", min_args=1, max_args=1)
def expanding_mean_operator(data: pd.DataFrame, series: pd.Series) -> pd.Series:
    """扩展窗口均值"""
    try:
        return series.expanding(min_periods=1).mean()
    except Exception as e:
        GLOG.ERROR(f"Expanding_mean operator failed: {e}")
        return pd.Series([np.nan] * len(series), index=series.index)


@register_operator("Expanding_std", "Expanding standard deviation", min_args=1, max_args=1)
def expanding_std_operator(data: pd.DataFrame, series: pd.Series) -> pd.Series:
    """扩展窗口标准差"""
    try:
        return series.expanding(min_periods=2).std()
    except Exception as e:
        GLOG.ERROR(f"Expanding_std operator failed: {e}")
        return pd.Series([np.nan] * len(series), index=series.index)


@register_operator("EWM", "Exponentially weighted moving average", min_args=2, max_args=2)
def ewm_operator(data: pd.DataFrame, series: pd.Series, span: pd.Series) -> pd.Series:
    """指数加权移动平均"""
    try:
        span_value = float(span.iloc[0]) if len(span) > 0 else 20
        if span_value <= 0:
            raise ValueError(f"Span must be positive, got {span_value}")
        
        return series.ewm(span=span_value, adjust=False).mean()
    except Exception as e:
        GLOG.ERROR(f"EWM operator failed: {e}")
        return pd.Series([np.nan] * len(series), index=series.index)


@register_operator("EWMSTD", "Exponentially weighted moving standard deviation", min_args=2, max_args=2)
def ewmstd_operator(data: pd.DataFrame, series: pd.Series, span: pd.Series) -> pd.Series:
    """指数加权移动标准差"""
    try:
        span_value = float(span.iloc[0]) if len(span) > 0 else 20
        if span_value <= 0:
            raise ValueError(f"Span must be positive, got {span_value}")
        
        return series.ewm(span=span_value, adjust=False).std()
    except Exception as e:
        GLOG.ERROR(f"EWMSTD operator failed: {e}")
        return pd.Series([np.nan] * len(series), index=series.index)


@register_operator("Shift_fill", "Shift with fill value", min_args=2, max_args=3)
def shift_fill_operator(data: pd.DataFrame, series: pd.Series, periods: pd.Series, fill_value: pd.Series = None) -> pd.Series:
    """带填充值的时间偏移"""
    try:
        shift_periods = int(periods.iloc[0]) if len(periods) > 0 else 1
        fill_val = 0
        if fill_value is not None and len(fill_value) > 0:
            fill_val = float(fill_value.iloc[0])
        
        return series.shift(shift_periods, fill_value=fill_val)
    except Exception as e:
        GLOG.ERROR(f"Shift_fill operator failed: {e}")
        return pd.Series([np.nan] * len(series), index=series.index)


@register_operator("Rolling_apply", "Rolling custom function", min_args=3, max_args=3)
def rolling_apply_operator(data: pd.DataFrame, series: pd.Series, window: pd.Series, func_name: pd.Series) -> pd.Series:
    """滚动自定义函数应用"""
    try:
        window_size = int(window.iloc[0]) if len(window) > 0 else 20
        function_name = str(func_name.iloc[0]) if len(func_name) > 0 else "mean"
        
        if window_size <= 0:
            raise ValueError(f"Window size must be positive, got {window_size}")
        
        # 支持的函数映射
        func_mapping = {
            "mean": lambda x: x.mean(),
            "std": lambda x: x.std(),
            "var": lambda x: x.var(),
            "min": lambda x: x.min(),
            "max": lambda x: x.max(),
            "median": lambda x: x.median(),
            "sum": lambda x: x.sum(),
            "prod": lambda x: x.prod(),
            "first": lambda x: x.iloc[0] if len(x) > 0 else np.nan,
            "last": lambda x: x.iloc[-1] if len(x) > 0 else np.nan,
        }
        
        if function_name not in func_mapping:
            raise ValueError(f"Unsupported function: {function_name}")
        
        return series.rolling(window=window_size, min_periods=1).apply(func_mapping[function_name])
    except Exception as e:
        GLOG.ERROR(f"Rolling_apply operator failed: {e}")
        return pd.Series([np.nan] * len(series), index=series.index)


@register_operator("Delay", "Delay series (alias for Shift)", min_args=2, max_args=2)
def delay_operator(data: pd.DataFrame, series: pd.Series, periods: pd.Series) -> pd.Series:
    """数据延迟（Shift的别名）"""
    try:
        delay_periods = int(periods.iloc[0]) if len(periods) > 0 else 1
        return series.shift(delay_periods)
    except Exception as e:
        GLOG.ERROR(f"Delay operator failed: {e}")
        return pd.Series([np.nan] * len(series), index=series.index)


@register_operator("Ts_Rank", "Time series rank", min_args=2, max_args=2)
def ts_rank_operator(data: pd.DataFrame, series: pd.Series, window: pd.Series) -> pd.Series:
    """
    时序排名 - 在时间窗口内的排名
    
    Args:
        series: 输入序列
        window: 时间窗口大小
        
    Returns:
        pd.Series: 在窗口内的排名 (0-1之间，1为最大值)
    """
    try:
        window_size = int(window.iloc[0]) if len(window) > 0 else 20
        if window_size <= 0:
            raise ValueError(f"Window size must be positive, got {window_size}")
        
        def rolling_rank(x):
            """计算窗口内的排名"""
            if len(x) == 0:
                return np.nan
            # 使用rank方法，method='min'处理重复值
            ranks = x.rank(method='min')
            # 标准化到0-1之间
            return (ranks.iloc[-1] - 1) / (len(x) - 1) if len(x) > 1 else 0.5
        
        result = series.rolling(window=window_size, min_periods=1).apply(rolling_rank)
        return result
        
    except Exception as e:
        GLOG.ERROR(f"Ts_Rank operator failed: {e}")
        return pd.Series([np.nan] * len(series), index=series.index)


@register_operator("Ts_ArgMax", "Time series argmax", min_args=2, max_args=2)
def ts_argmax_operator(data: pd.DataFrame, series: pd.Series, window: pd.Series) -> pd.Series:
    """
    时序最大值索引 - 返回窗口内最大值的相对位置
    
    Args:
        series: 输入序列
        window: 时间窗口大小
        
    Returns:
        pd.Series: 最大值在窗口内的位置 (0为最早，window-1为最新)
    """
    try:
        window_size = int(window.iloc[0]) if len(window) > 0 else 20
        if window_size <= 0:
            raise ValueError(f"Window size must be positive, got {window_size}")
        
        def rolling_argmax(x):
            """计算窗口内最大值的索引"""
            if len(x) == 0:
                return np.nan
            return x.argmax()
        
        result = series.rolling(window=window_size, min_periods=1).apply(rolling_argmax)
        return result
        
    except Exception as e:
        GLOG.ERROR(f"Ts_ArgMax operator failed: {e}")
        return pd.Series([np.nan] * len(series), index=series.index)


@register_operator("Ts_ArgMin", "Time series argmin", min_args=2, max_args=2)
def ts_argmin_operator(data: pd.DataFrame, series: pd.Series, window: pd.Series) -> pd.Series:
    """
    时序最小值索引 - 返回窗口内最小值的相对位置
    
    Args:
        series: 输入序列
        window: 时间窗口大小
        
    Returns:
        pd.Series: 最小值在窗口内的位置 (0为最早，window-1为最新)
    """
    try:
        window_size = int(window.iloc[0]) if len(window) > 0 else 20
        if window_size <= 0:
            raise ValueError(f"Window size must be positive, got {window_size}")
        
        def rolling_argmin(x):
            """计算窗口内最小值的索引"""
            if len(x) == 0:
                return np.nan
            return x.argmin()
        
        result = series.rolling(window=window_size, min_periods=1).apply(rolling_argmin)
        return result
        
    except Exception as e:
        GLOG.ERROR(f"Ts_ArgMin operator failed: {e}")
        return pd.Series([np.nan] * len(series), index=series.index)


@register_operator("Ts_Max", "Time series rolling maximum", min_args=2, max_args=2)
def ts_max_operator(data: pd.DataFrame, series: pd.Series, window: pd.Series) -> pd.Series:
    """时序滚动最大值"""
    try:
        window_size = int(window.iloc[0]) if len(window) > 0 else 20
        if window_size <= 0:
            raise ValueError(f"Window size must be positive, got {window_size}")
        
        return series.rolling(window=window_size, min_periods=1).max()
    except Exception as e:
        GLOG.ERROR(f"Ts_Max operator failed: {e}")
        return pd.Series([np.nan] * len(series), index=series.index)


@register_operator("Ts_Min", "Time series rolling minimum", min_args=2, max_args=2)
def ts_min_operator(data: pd.DataFrame, series: pd.Series, window: pd.Series) -> pd.Series:
    """时序滚动最小值"""
    try:
        window_size = int(window.iloc[0]) if len(window) > 0 else 20
        if window_size <= 0:
            raise ValueError(f"Window size must be positive, got {window_size}")
        
        return series.rolling(window=window_size, min_periods=1).min()
    except Exception as e:
        GLOG.ERROR(f"Ts_Min operator failed: {e}")
        return pd.Series([np.nan] * len(series), index=series.index)


@register_operator("Ts_Mean", "Time series rolling mean", min_args=2, max_args=2)
def ts_mean_operator(data: pd.DataFrame, series: pd.Series, window: pd.Series) -> pd.Series:
    """时序滚动平均值"""
    try:
        window_size = int(window.iloc[0]) if len(window) > 0 else 20
        if window_size <= 0:
            raise ValueError(f"Window size must be positive, got {window_size}")
        
        return series.rolling(window=window_size, min_periods=1).mean()
    except Exception as e:
        GLOG.ERROR(f"Ts_Mean operator failed: {e}")
        return pd.Series([np.nan] * len(series), index=series.index)