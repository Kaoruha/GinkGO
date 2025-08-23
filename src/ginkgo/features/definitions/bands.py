"""
布林带指标集合 - 配置式定义

基于表达式引擎的布林带指标实现，
包括标准布林带及相关信号指标。
"""

from .base import BaseDefinition


class BandIndicators(BaseDefinition):
    """布林带指标类 - 配置式定义"""
    
    NAME = "Bands"
    DESCRIPTION = "布林带技术指标集合，包含布林带上下轨及相关压缩扩张信号"
    
    # 布林带指标表达式定义
    EXPRESSIONS = {
        # 标准布林带 (20日，2倍标准差)
        "BB_UPPER_20_2": "Add(Mean($close, 20), Multiply(Std($close, 20), 2))",
        "BB_MIDDLE_20": "Mean($close, 20)",
        "BB_LOWER_20_2": "Subtract(Mean($close, 20), Multiply(Std($close, 20), 2))",
        "BB_WIDTH_20_2": "Multiply(Std($close, 20), 4)",  # 简化的宽度计算
        
        # 其他参数的布林带
        "BB_UPPER_10_2": "Add(Mean($close, 10), Multiply(Std($close, 10), 2))",
        "BB_LOWER_10_2": "Subtract(Mean($close, 10), Multiply(Std($close, 10), 2))",
        "BB_UPPER_30_2": "Add(Mean($close, 30), Multiply(Std($close, 30), 2))",
        "BB_LOWER_30_2": "Subtract(Mean($close, 30), Multiply(Std($close, 30), 2))",
        
        # 布林带信号
        "BB_SQUEEZE": "If(Less(Multiply(Std($close, 20), 4), Mean(Multiply(Std($close, 20), 4), 50)), 1, 0)",  # 压缩
        "BB_EXPANSION": "If(Greater(Multiply(Std($close, 20), 4), Mean(Multiply(Std($close, 20), 4), 50)), 1, 0)",  # 扩张
        "BB_UPPER_TOUCH": "If(Greater($close, Add(Mean($close, 20), Multiply(Std($close, 20), 2))), 1, 0)",  # 触及上轨
        "BB_LOWER_TOUCH": "If(Less($close, Subtract(Mean($close, 20), Multiply(Std($close, 20), 2))), 1, 0)",  # 触及下轨
        "BB_POSITION": "Divide(Subtract($close, Subtract(Mean($close, 20), Multiply(Std($close, 20), 2))), Multiply(Std($close, 20), 4))",  # 在带内位置
    }
    
    # 指标分类定义
    CATEGORIES = {
        "standard": ["BB_UPPER_20_2", "BB_MIDDLE_20", "BB_LOWER_20_2", "BB_WIDTH_20_2"],
        "bands_10": ["BB_UPPER_10_2", "BB_LOWER_10_2"],
        "bands_30": ["BB_UPPER_30_2", "BB_LOWER_30_2"],
        "signals": ["BB_SQUEEZE", "BB_EXPANSION", "BB_UPPER_TOUCH", "BB_LOWER_TOUCH", "BB_POSITION"],
        "width_signals": ["BB_SQUEEZE", "BB_EXPANSION"],
        "touch_signals": ["BB_UPPER_TOUCH", "BB_LOWER_TOUCH"],
        "short_term": ["BB_UPPER_10_2", "BB_LOWER_10_2"],
        "long_term": ["BB_UPPER_30_2", "BB_LOWER_30_2"]
    }