# Upstream: External Applications
# Downstream: Trading Strategies, Analysis Tools
# Role: Registry引擎提供OperatorRegistry操作符注册表提供表达式操作符注册和查找功能计算和处理






"""
Operator Registry - 操作符注册中心

管理所有可用的函数和操作符：
- 函数注册和查找
- 函数执行和参数处理
- 内置操作符定义
"""

from typing import Dict, Callable, List, Any, Union
import pandas as pd
import numpy as np
from ginkgo.libs import GLOG


class OperatorRegistry:
    """操作符注册中心 - 管理所有表达式函数"""
    
    _operators: Dict[str, Callable] = {}
    _operator_metadata: Dict[str, Dict[str, Any]] = {}
    
    @classmethod
    def register(cls, name: str, function: Callable, description: str = "",
                 min_args: int = 0, max_args: int = None):
        """
        注册操作符函数

        Args:
            name: 函数名称
            function: 函数实现
            description: 函数描述
            min_args: 最少参数数量
            max_args: 最多参数数量

        Raises:
            ValueError: 同名操作符已注册时抛出。调用方须先 unregister() 或换名,
                避免静默覆盖(历史 bug:截面 Rank 被滚动 Rank 静默覆盖成死代码,#6479)。
        """
        if name in cls._operators:
            existing = cls._operators[name]
            raise ValueError(
                f"Operator '{name}' is already registered by "
                f"{existing.__module__}.{existing.__name__}; cannot register "
                f"duplicate from {function.__module__}.{function.__name__}. "
                f"Call unregister() first or use a distinct name."
            )
        cls._operators[name] = function
        cls._operator_metadata[name] = {
            "description": description,
            "min_args": min_args,
            "max_args": max_args or min_args
        }
        GLOG.DEBUG(f"Registered operator: {name}")
    
    @classmethod
    def unregister(cls, name: str):
        """注销操作符"""
        if name in cls._operators:
            del cls._operators[name]
            del cls._operator_metadata[name]
            GLOG.DEBUG(f"Unregistered operator: {name}")
    
    @classmethod
    def is_registered(cls, name: str) -> bool:
        """检查操作符是否已注册"""
        return name in cls._operators
    
    @classmethod
    def get_available_operators(cls) -> List[str]:
        """获取所有可用的操作符名称"""
        return list(cls._operators.keys())
    
    @classmethod
    def get_operator_info(cls, name: str) -> Dict[str, Any]:
        """获取操作符信息"""
        if name not in cls._operator_metadata:
            return {}
        return cls._operator_metadata[name].copy()
    
    @classmethod
    def execute_function(cls, function_name: str, args: List[pd.Series], 
                        data: pd.DataFrame) -> pd.Series:
        """
        执行注册的函数
        
        Args:
            function_name: 函数名称
            args: 参数序列列表
            data: 原始数据DataFrame
            
        Returns:
            pd.Series: 函数执行结果
        """
        try:
            if function_name not in cls._operators:
                raise ValueError(f"Unknown function: {function_name}")
            
            # 参数数量验证
            metadata = cls._operator_metadata.get(function_name, {})
            min_args = metadata.get("min_args", 0)
            max_args = metadata.get("max_args", len(args))
            
            if len(args) < min_args:
                raise ValueError(f"Function {function_name} requires at least {min_args} arguments, got {len(args)}")
            
            if max_args is not None and len(args) > max_args:
                raise ValueError(f"Function {function_name} accepts at most {max_args} arguments, got {len(args)}")
            
            # 调用注册的函数
            function = cls._operators[function_name]
            result = function(data, *args)
            
            # 确保返回值是pandas Series
            if not isinstance(result, pd.Series):
                if isinstance(result, (int, float)):
                    result = pd.Series([result] * len(data), index=data.index)
                elif isinstance(result, (list, np.ndarray)):
                    result = pd.Series(result, index=data.index)
                else:
                    raise ValueError(f"Function {function_name} returned invalid type: {type(result)}")
            
            return result
            
        except Exception as e:
            GLOG.ERROR(f"Function execution failed for {function_name}: {e}")
            # 返回NaN序列，不中断计算
            return pd.Series([np.nan] * len(data), index=data.index)
    
    @classmethod
    def validate_function_call(cls, function_name: str, arg_count: int) -> bool:
        """验证函数调用是否有效"""
        if function_name not in cls._operators:
            return False
        
        metadata = cls._operator_metadata.get(function_name, {})
        min_args = metadata.get("min_args", 0)
        max_args = metadata.get("max_args", arg_count)
        
        return min_args <= arg_count <= (max_args or arg_count)


# 装饰器用于简化操作符注册
def register_operator(name: str, description: str = "", min_args: int = 0, max_args: int = None):
    """
    操作符注册装饰器
    
    Usage:
        @register_operator("Mean", "Moving average", min_args=2, max_args=2)
        def mean_operator(data, series, window):
            ...
    """
    def decorator(func: Callable):
        OperatorRegistry.register(name, func, description, min_args, max_args)
        return func
    return decorator


# ============================================================================
# 操作符参数提取工具(供内置算子与 operators/* 共用,#6479 AC2)
# 放在 registry(叶子模块)以避免 operators/__init__ 急切加载造成的循环 import。
# ============================================================================
def _extract_window(series: pd.Series, default: int = 20) -> int:
    """从窗口参数 Series 提取整数:取首元素,空则用 default,<=0 抛 ValueError。

    替换原模板::

        window_size = int(window.iloc[0]) if len(window) > 0 else N
        if window_size <= 0:
            raise ValueError(f"Window size must be positive, got {window_size}")
    """
    window_size = int(series.iloc[0]) if len(series) > 0 else default
    if window_size <= 0:
        raise ValueError(f"Window size must be positive, got {window_size}")
    return window_size


def _extract_periods(series: pd.Series, default: int = 1, *, allow_negative: bool = True) -> int:
    """从周期/滞后参数 Series 提取整数:取首元素,空则用 default。

    - ``allow_negative=True``(默认):Ref/Delta/Shift_fill/Delay,允许负偏移。
    - ``allow_negative=False``:AutoCorr lag,要求非负,<0 抛 ValueError。
    """
    periods = int(series.iloc[0]) if len(series) > 0 else default
    if not allow_negative and periods < 0:
        raise ValueError(f"Lag must be non-negative, got {periods}")
    return periods


# ============================================================================
# 内置操作符定义
# ============================================================================

@register_operator("Mean", "Moving average", min_args=2, max_args=2)
def mean_operator(data: pd.DataFrame, series: pd.Series, window: pd.Series) -> pd.Series:
    """
    移动平均
    
    Args:
        series: 输入序列
        window: 窗口大小序列
    """
    window_size = _extract_window(window)
    
    return series.rolling(window=window_size, min_periods=1).mean()


@register_operator("Std", "Standard deviation", min_args=2, max_args=2)
def std_operator(data: pd.DataFrame, series: pd.Series, window: pd.Series) -> pd.Series:
    """标准差"""
    window_size = _extract_window(window)
    
    return series.rolling(window=window_size, min_periods=1).std()


@register_operator("Max", "Rolling maximum", min_args=2, max_args=2)
def max_operator(data: pd.DataFrame, series: pd.Series, window: pd.Series) -> pd.Series:
    """滚动最大值"""
    window_size = _extract_window(window)
    
    return series.rolling(window=window_size, min_periods=1).max()


@register_operator("Min", "Rolling minimum", min_args=2, max_args=2)
def min_operator(data: pd.DataFrame, series: pd.Series, window: pd.Series) -> pd.Series:
    """滚动最小值"""
    window_size = _extract_window(window)
    
    return series.rolling(window=window_size, min_periods=1).min()


@register_operator("Ref", "Time reference/lag", min_args=2, max_args=2)
def ref_operator(data: pd.DataFrame, series: pd.Series, periods: pd.Series) -> pd.Series:
    """时间偏移/滞后"""
    shift_periods = _extract_periods(periods)
    return series.shift(shift_periods)


@register_operator("Delta", "Difference", min_args=2, max_args=2)
def delta_operator(data: pd.DataFrame, series: pd.Series, periods: pd.Series) -> pd.Series:
    """差分"""
    diff_periods = _extract_periods(periods)
    return series.diff(diff_periods)


@register_operator("Sum", "Rolling sum", min_args=2, max_args=2)
def sum_operator(data: pd.DataFrame, series: pd.Series, window: pd.Series) -> pd.Series:
    """滚动求和"""
    window_size = _extract_window(window)
    
    return series.rolling(window=window_size, min_periods=1).sum()


@register_operator("Quantile", "Rolling quantile", min_args=3, max_args=3)
def quantile_operator(data: pd.DataFrame, series: pd.Series, window: pd.Series, q: pd.Series) -> pd.Series:
    """滚动分位数"""
    window_size = _extract_window(window)
    quantile = float(q.iloc[0]) if len(q) > 0 else 0.5

    if not 0 <= quantile <= 1:
        raise ValueError(f"Quantile must be between 0 and 1, got {quantile}")

    return series.rolling(window=window_size, min_periods=1).quantile(quantile)


@register_operator("Abs", "Absolute value", min_args=1, max_args=1)
def abs_operator(data: pd.DataFrame, series: pd.Series) -> pd.Series:
    """绝对值"""
    return series.abs()


@register_operator("Log", "Natural logarithm", min_args=1, max_args=1)
def log_operator(data: pd.DataFrame, series: pd.Series) -> pd.Series:
    """自然对数"""
    with np.errstate(divide='ignore', invalid='ignore'):
        result = np.log(series)
        return result.replace([np.inf, -np.inf], np.nan)


# 技术指标相关操作符会在indicators模块中定义和注册