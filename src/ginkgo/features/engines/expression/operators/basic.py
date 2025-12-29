# Upstream: External Applications
# Downstream: Trading Strategies, Analysis Tools
# Role: 定义基础数学表达式操作符提供pow_operator/log_operator/sqrt_operator等方法






"""
Basic Operators - 基础运算操作符

提供基础的数学运算函数，主要通过AST的BinaryOpNode处理，
这里提供一些扩展的数学函数。
"""

import pandas as pd
import numpy as np
from ginkgo.features.engines.expression.registry import register_operator
from ginkgo.libs import GLOG


@register_operator("Pow", "Power function", min_args=2, max_args=2)
def pow_operator(data: pd.DataFrame, base: pd.Series, exponent: pd.Series) -> pd.Series:
    """幂运算"""
    try:
        with np.errstate(over='ignore', invalid='ignore'):
            result = np.power(base, exponent)
            return pd.Series(result, index=base.index).replace([np.inf, -np.inf], np.nan)
    except Exception as e:
        GLOG.ERROR(f"Pow operator failed: {e}")
        return pd.Series([np.nan] * len(base), index=base.index)


@register_operator("Sqrt", "Square root", min_args=1, max_args=1)
def sqrt_operator(data: pd.DataFrame, series: pd.Series) -> pd.Series:
    """平方根"""
    try:
        with np.errstate(invalid='ignore'):
            result = np.sqrt(series)
            return pd.Series(result, index=series.index)
    except Exception as e:
        GLOG.ERROR(f"Sqrt operator failed: {e}")
        return pd.Series([np.nan] * len(series), index=series.index)


@register_operator("Exp", "Exponential function", min_args=1, max_args=1)
def exp_operator(data: pd.DataFrame, series: pd.Series) -> pd.Series:
    """指数函数"""
    try:
        with np.errstate(over='ignore'):
            result = np.exp(series)
            return pd.Series(result, index=series.index).replace([np.inf, -np.inf], np.nan)
    except Exception as e:
        GLOG.ERROR(f"Exp operator failed: {e}")
        return pd.Series([np.nan] * len(series), index=series.index)


@register_operator("Round", "Round to decimal places", min_args=1, max_args=2)
def round_operator(data: pd.DataFrame, series: pd.Series, decimals: pd.Series = None) -> pd.Series:
    """四舍五入"""
    try:
        decimal_places = 0
        if decimals is not None and len(decimals) > 0:
            decimal_places = int(decimals.iloc[0])
        
        return series.round(decimal_places)
    except Exception as e:
        GLOG.ERROR(f"Round operator failed: {e}")
        return pd.Series([np.nan] * len(series), index=series.index)


@register_operator("Floor", "Floor function", min_args=1, max_args=1)
def floor_operator(data: pd.DataFrame, series: pd.Series) -> pd.Series:
    """向下取整"""
    try:
        return series.apply(np.floor)
    except Exception as e:
        GLOG.ERROR(f"Floor operator failed: {e}")
        return pd.Series([np.nan] * len(series), index=series.index)


@register_operator("Ceil", "Ceiling function", min_args=1, max_args=1)
def ceil_operator(data: pd.DataFrame, series: pd.Series) -> pd.Series:
    """向上取整"""
    try:
        return series.apply(np.ceil)
    except Exception as e:
        GLOG.ERROR(f"Ceil operator failed: {e}")
        return pd.Series([np.nan] * len(series), index=series.index)


@register_operator("Sign", "Sign function", min_args=1, max_args=1)
def sign_operator(data: pd.DataFrame, series: pd.Series) -> pd.Series:
    """符号函数"""
    try:
        return series.apply(np.sign)
    except Exception as e:
        GLOG.ERROR(f"Sign operator failed: {e}")
        return pd.Series([np.nan] * len(series), index=series.index)


@register_operator("Add", "Addition", min_args=2, max_args=2)
def add_operator(data: pd.DataFrame, left: pd.Series, right: pd.Series) -> pd.Series:
    """加法运算"""
    try:
        return left + right
    except Exception as e:
        GLOG.ERROR(f"Add operator failed: {e}")
        return pd.Series([np.nan] * len(left), index=left.index)


@register_operator("Subtract", "Subtraction", min_args=2, max_args=2)
def subtract_operator(data: pd.DataFrame, left: pd.Series, right: pd.Series) -> pd.Series:
    """减法运算"""
    try:
        return left - right
    except Exception as e:
        GLOG.ERROR(f"Subtract operator failed: {e}")
        return pd.Series([np.nan] * len(left), index=left.index)


@register_operator("Multiply", "Multiplication", min_args=2, max_args=2)
def multiply_operator(data: pd.DataFrame, left: pd.Series, right: pd.Series) -> pd.Series:
    """乘法运算"""
    try:
        return left * right
    except Exception as e:
        GLOG.ERROR(f"Multiply operator failed: {e}")
        return pd.Series([np.nan] * len(left), index=left.index)


@register_operator("Divide", "Division", min_args=2, max_args=2)
def divide_operator(data: pd.DataFrame, left: pd.Series, right: pd.Series) -> pd.Series:
    """除法运算"""
    try:
        with np.errstate(divide='ignore', invalid='ignore'):
            result = left / right
            return result.replace([np.inf, -np.inf], np.nan)
    except Exception as e:
        GLOG.ERROR(f"Divide operator failed: {e}")
        return pd.Series([np.nan] * len(left), index=left.index)


@register_operator("If", "Conditional if-then-else", min_args=3, max_args=3)
def if_operator(data: pd.DataFrame, condition: pd.Series, true_value: pd.Series, false_value: pd.Series) -> pd.Series:
    """
    条件判断运算符 - 三元运算符
    
    Args:
        condition: 条件序列，非零值为True
        true_value: 条件为True时的返回值
        false_value: 条件为False时的返回值
        
    Returns:
        pd.Series: 根据条件选择的值序列
    """
    try:
        # 将条件转换为布尔值
        bool_condition = condition.fillna(False).astype(bool)
        
        # 使用pandas的where方法进行条件选择
        result = true_value.where(bool_condition, false_value)
        
        return result
        
    except Exception as e:
        GLOG.ERROR(f"If operator failed: {e}")
        return pd.Series([np.nan] * len(condition), index=condition.index)


@register_operator("SignedPower", "Signed power function", min_args=2, max_args=2)
def signed_power_operator(data: pd.DataFrame, base: pd.Series, exponent: pd.Series) -> pd.Series:
    """
    带符号幂运算 - 保持底数符号的幂运算
    
    Args:
        base: 底数序列
        exponent: 指数序列
        
    Returns:
        pd.Series: 带符号的幂运算结果
    """
    try:
        with np.errstate(over='ignore', invalid='ignore'):
            # 获取底数的符号
            signs = np.sign(base)
            
            # 对绝对值进行幂运算
            abs_base = np.abs(base)
            abs_result = np.power(abs_base, exponent)
            
            # 应用原始符号
            result = signs * abs_result
            
            return pd.Series(result, index=base.index).replace([np.inf, -np.inf], np.nan)
            
    except Exception as e:
        GLOG.ERROR(f"SignedPower operator failed: {e}")
        return pd.Series([np.nan] * len(base), index=base.index)