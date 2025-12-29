# Upstream: External Applications
# Downstream: Trading Strategies, Analysis Tools
# Role: Moving Averages因子定义继承FactorBase提供Moving Averages计算






"""
移动平均指标集合 - 配置式定义

将原backtest/computation/technical下的移动平均指标转换为表达式形式，
支持通过FactorEngine进行动态计算。
"""

from ginkgo.features.definitions.base import BaseDefinition


class MovingAverageIndicators(BaseDefinition):
    """移动平均指标类 - 配置式定义"""
    
    NAME = "MovingAverages"
    DESCRIPTION = "移动平均技术指标集合，包含SMA、EMA、WMA等移动平均指标及交叉信号"
    
    # 移动平均指标表达式定义
    EXPRESSIONS = {
        # 简单移动平均 (SMA)
        "SMA_5": "Mean($close, 5)",
        "SMA_10": "Mean($close, 10)",
        "SMA_20": "Mean($close, 20)",
        "SMA_30": "Mean($close, 30)",
        "SMA_60": "Mean($close, 60)",
        "SMA_120": "Mean($close, 120)",
        "SMA_250": "Mean($close, 250)",
        
        # 指数移动平均 (EMA)
        "EMA_5": "EWM($close, 5)",
        "EMA_10": "EWM($close, 10)",
        "EMA_12": "EWM($close, 12)",
        "EMA_20": "EWM($close, 20)",
        "EMA_26": "EWM($close, 26)",
        "EMA_30": "EWM($close, 30)",
        "EMA_60": "EWM($close, 60)",
        
        # 加权移动平均 (WMA)
        "WMA_5": "WMA($close, 5)",
        "WMA_10": "WMA($close, 10)",
        "WMA_20": "WMA($close, 20)",
        "WMA_30": "WMA($close, 30)",
        
        # 移动平均交叉信号
        "MA_CROSS_5_20": "If(Greater(Mean($close, 5), Mean($close, 20)), 1, 0)",
        "MA_CROSS_10_30": "If(Greater(Mean($close, 10), Mean($close, 30)), 1, 0)",
        "EMA_CROSS_12_26": "If(Greater(EWM($close, 12), EWM($close, 26)), 1, 0)",
        
        # 价格与均线关系
        "PRICE_ABOVE_SMA20": "If(Greater($close, Mean($close, 20)), 1, 0)",
        "PRICE_ABOVE_SMA60": "If(Greater($close, Mean($close, 60)), 1, 0)",
        "PRICE_DEVIATION_SMA20": "Divide(Subtract($close, Mean($close, 20)), Mean($close, 20))",
    }
    
    # 指标分类定义
    CATEGORIES = {
        "sma": ["SMA_5", "SMA_10", "SMA_20", "SMA_30", "SMA_60", "SMA_120", "SMA_250"],
        "ema": ["EMA_5", "EMA_10", "EMA_12", "EMA_20", "EMA_26", "EMA_30", "EMA_60"],
        "wma": ["WMA_5", "WMA_10", "WMA_20", "WMA_30"],
        "signals": ["MA_CROSS_5_20", "MA_CROSS_10_30", "EMA_CROSS_12_26", 
                   "PRICE_ABOVE_SMA20", "PRICE_ABOVE_SMA60", "PRICE_DEVIATION_SMA20"],
        "short_term": ["SMA_5", "SMA_10", "EMA_5", "EMA_10", "EMA_12", "WMA_5", "WMA_10"],
        "medium_term": ["SMA_20", "SMA_30", "EMA_20", "EMA_26", "EMA_30", "WMA_20", "WMA_30"],
        "long_term": ["SMA_60", "SMA_120", "SMA_250", "EMA_60"]
    }