# Upstream: External Applications
# Downstream: Trading Strategies, Analysis Tools
# Role: 定义时序分析表达式操作符提供returns_operator/delay_operator/delta_operator等方法






"""
Temporal Operators - 时序操作符

提供时间序列相关的操作函数，包括时间偏移、差分、趋势分析等。
"""

import pandas as pd
import numpy as np
from ginkgo.features.engines.expression.registry import register_operator, with_error_handling, _extract_scalar
from ginkgo.libs import GLOG


@register_operator("Returns", "Calculate returns", min_args=1, max_args=2)
@with_error_handling()
def returns_operator(data: pd.DataFrame, series: pd.Series, periods: pd.Series = None) -> pd.Series:
    """收益率计算"""
    shift_periods = 1
    if periods is not None and len(periods) > 0:
        shift_periods = int(periods.iloc[0])
        
    if shift_periods <= 0:
        raise ValueError(f"Periods must be positive, got {shift_periods}")
        
    prev_values = series.shift(shift_periods)
    with np.errstate(divide='ignore', invalid='ignore'):
        returns = (series - prev_values) / prev_values
        return returns.replace([np.inf, -np.inf], np.nan)
            


@register_operator("LogReturns", "Calculate log returns", min_args=1, max_args=2)
@with_error_handling()
def log_returns_operator(data: pd.DataFrame, series: pd.Series, periods: pd.Series = None) -> pd.Series:
    """对数收益率计算"""
    shift_periods = 1
    if periods is not None and len(periods) > 0:
        shift_periods = int(periods.iloc[0])
        
    if shift_periods <= 0:
        raise ValueError(f"Periods must be positive, got {shift_periods}")
        
    prev_values = series.shift(shift_periods)
    with np.errstate(divide='ignore', invalid='ignore'):
        log_returns = np.log(series / prev_values)
        return pd.Series(log_returns, index=series.index).replace([np.inf, -np.inf], np.nan)
            


@register_operator("Pct_change", "Percentage change", min_args=1, max_args=2)
@with_error_handling()
def pct_change_operator(data: pd.DataFrame, series: pd.Series, periods: pd.Series = None) -> pd.Series:
    """百分比变化"""
    shift_periods = 1
    if periods is not None and len(periods) > 0:
        shift_periods = int(periods.iloc[0])
        
    return series.pct_change(periods=shift_periods)


@register_operator("CumSum", "Cumulative sum", min_args=1, max_args=1)
@with_error_handling()
def cumsum_operator(data: pd.DataFrame, series: pd.Series) -> pd.Series:
    """累积求和"""
    return series.cumsum()


@register_operator("WMA", "Weighted Moving Average", min_args=2, max_args=2)
@with_error_handling()
def wma_operator(data: pd.DataFrame, series: pd.Series, window: pd.Series) -> pd.Series:
    """加权移动平均"""
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
        


@register_operator("CumProd", "Cumulative product", min_args=1, max_args=1)
@with_error_handling()
def cumprod_operator(data: pd.DataFrame, series: pd.Series) -> pd.Series:
    """累积乘积"""
    return series.cumprod()


@register_operator("CumMax", "Cumulative maximum", min_args=1, max_args=1)
@with_error_handling()
def cummax_operator(data: pd.DataFrame, series: pd.Series) -> pd.Series:
    """累积最大值"""
    return series.cummax()


@register_operator("CumMin", "Cumulative minimum", min_args=1, max_args=1)
@with_error_handling()
def cummin_operator(data: pd.DataFrame, series: pd.Series) -> pd.Series:
    """累积最小值"""
    return series.cummin()


@register_operator("Expanding_mean", "Expanding mean", min_args=1, max_args=1)
@with_error_handling()
def expanding_mean_operator(data: pd.DataFrame, series: pd.Series) -> pd.Series:
    """扩展窗口均值"""
    return series.expanding(min_periods=1).mean()


@register_operator("Expanding_std", "Expanding standard deviation", min_args=1, max_args=1)
@with_error_handling()
def expanding_std_operator(data: pd.DataFrame, series: pd.Series) -> pd.Series:
    """扩展窗口标准差"""
    return series.expanding(min_periods=2).std()


@register_operator("EWM", "Exponentially weighted moving average", min_args=2, max_args=2)
@with_error_handling()
def ewm_operator(data: pd.DataFrame, series: pd.Series, span: pd.Series) -> pd.Series:
    """指数加权移动平均"""
    span_value = _extract_scalar(span, 20, cast=float)
    if span_value <= 0:
        raise ValueError(f"Span must be positive, got {span_value}")
        
    return series.ewm(span=span_value, adjust=False).mean()


@register_operator("EWMSTD", "Exponentially weighted moving standard deviation", min_args=2, max_args=2)
@with_error_handling()
def ewmstd_operator(data: pd.DataFrame, series: pd.Series, span: pd.Series) -> pd.Series:
    """指数加权移动标准差"""
    span_value = _extract_scalar(span, 20, cast=float)
    if span_value <= 0:
        raise ValueError(f"Span must be positive, got {span_value}")
        
    return series.ewm(span=span_value, adjust=False).std()


@register_operator("Shift_fill", "Shift with fill value", min_args=2, max_args=3)
@with_error_handling()
def shift_fill_operator(data: pd.DataFrame, series: pd.Series, periods: pd.Series, fill_value: pd.Series = None) -> pd.Series:
    """带填充值的时间偏移"""
    shift_periods = _extract_scalar(periods, 1)
    fill_val = 0
    if fill_value is not None and len(fill_value) > 0:
        fill_val = float(fill_value.iloc[0])
        
    return series.shift(shift_periods, fill_value=fill_val)


@register_operator("Rolling_apply", "Rolling custom function", min_args=3, max_args=3)
@with_error_handling()
def rolling_apply_operator(data: pd.DataFrame, series: pd.Series, window: pd.Series, func_name: pd.Series) -> pd.Series:
    """滚动自定义函数应用"""
    window_size = _extract_scalar(window, 20)
    function_name = _extract_scalar(func_name, "mean", cast=str)
        
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


@register_operator("Delay", "Delay series (alias for Shift)", min_args=2, max_args=2)
@with_error_handling()
def delay_operator(data: pd.DataFrame, series: pd.Series, periods: pd.Series) -> pd.Series:
    """数据延迟（Shift的别名）"""
    delay_periods = _extract_scalar(periods, 1)
    return series.shift(delay_periods)


@register_operator("Ts_Rank", "Time series rank", min_args=2, max_args=2)
@with_error_handling()
def ts_rank_operator(data: pd.DataFrame, series: pd.Series, window: pd.Series) -> pd.Series:
    """
    时序排名 - 在时间窗口内的排名
    
    Args:
        series: 输入序列
        window: 时间窗口大小
        
    Returns:
        pd.Series: 在窗口内的排名 (0-1之间，1为最大值)
    """
    window_size = _extract_scalar(window, 20)
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
        


@register_operator("Ts_ArgMax", "Time series argmax", min_args=2, max_args=2)
@with_error_handling()
def ts_argmax_operator(data: pd.DataFrame, series: pd.Series, window: pd.Series) -> pd.Series:
    """
    时序最大值索引 - 返回窗口内最大值的相对位置
    
    Args:
        series: 输入序列
        window: 时间窗口大小
        
    Returns:
        pd.Series: 最大值在窗口内的位置 (0为最早，window-1为最新)
    """
    window_size = _extract_scalar(window, 20)
    if window_size <= 0:
        raise ValueError(f"Window size must be positive, got {window_size}")
        
    def rolling_argmax(x):
        """计算窗口内最大值的索引"""
        if len(x) == 0:
            return np.nan
        return x.argmax()
        
    result = series.rolling(window=window_size, min_periods=1).apply(rolling_argmax)
    return result
        


@register_operator("Ts_ArgMin", "Time series argmin", min_args=2, max_args=2)
@with_error_handling()
def ts_argmin_operator(data: pd.DataFrame, series: pd.Series, window: pd.Series) -> pd.Series:
    """
    时序最小值索引 - 返回窗口内最小值的相对位置
    
    Args:
        series: 输入序列
        window: 时间窗口大小
        
    Returns:
        pd.Series: 最小值在窗口内的位置 (0为最早，window-1为最新)
    """
    window_size = _extract_scalar(window, 20)
    if window_size <= 0:
        raise ValueError(f"Window size must be positive, got {window_size}")
        
    def rolling_argmin(x):
        """计算窗口内最小值的索引"""
        if len(x) == 0:
            return np.nan
        return x.argmin()
        
    result = series.rolling(window=window_size, min_periods=1).apply(rolling_argmin)
    return result
        


@register_operator("Ts_Max", "Time series rolling maximum", min_args=2, max_args=2)
@with_error_handling()
def ts_max_operator(data: pd.DataFrame, series: pd.Series, window: pd.Series) -> pd.Series:
    """时序滚动最大值"""
    window_size = _extract_scalar(window, 20)
    if window_size <= 0:
        raise ValueError(f"Window size must be positive, got {window_size}")
        
    return series.rolling(window=window_size, min_periods=1).max()


@register_operator("Ts_Min", "Time series rolling minimum", min_args=2, max_args=2)
@with_error_handling()
def ts_min_operator(data: pd.DataFrame, series: pd.Series, window: pd.Series) -> pd.Series:
    """时序滚动最小值"""
    window_size = _extract_scalar(window, 20)
    if window_size <= 0:
        raise ValueError(f"Window size must be positive, got {window_size}")
        
    return series.rolling(window=window_size, min_periods=1).min()


@register_operator("Ts_Mean", "Time series rolling mean", min_args=2, max_args=2)
@with_error_handling()
def ts_mean_operator(data: pd.DataFrame, series: pd.Series, window: pd.Series) -> pd.Series:
    """时序滚动平均值"""
    window_size = _extract_scalar(window, 20)
    if window_size <= 0:
        raise ValueError(f"Window size must be positive, got {window_size}")
        
    return series.rolling(window=window_size, min_periods=1).mean()