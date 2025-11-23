"""
振荡器指标集合 - 配置式定义

将原backtest/computation/technical下的振荡器指标转换为表达式形式，
包括RSI、ATR等技术分析中的振荡器指标。
"""

from ginkgo.features.definitions.base import BaseDefinition


class OscillatorIndicators(BaseDefinition):
    """振荡器指标类 - 配置式定义"""
    
    NAME = "Oscillators"
    DESCRIPTION = "振荡器技术指标集合，包含RSI、ATR等振荡器指标及相关信号"
    
    # 振荡器指标表达式定义
    EXPRESSIONS = {
        # 相对强弱指数 (RSI) - 不同周期
        "RSI_6": "RSI($close, 6)",
        "RSI_12": "RSI($close, 12)", 
        "RSI_14": "RSI($close, 14)",  # 标准RSI周期
        "RSI_21": "RSI($close, 21)",
        "RSI_30": "RSI($close, 30)",
        
        # 平均真实波幅 (ATR) - 不同周期
        "ATR_7": "ATR($high, $low, $close, 7)",
        "ATR_14": "ATR($high, $low, $close, 14)",  # 标准ATR周期
        "ATR_21": "ATR($high, $low, $close, 21)",
        "ATR_30": "ATR($high, $low, $close, 30)",
        
        # RSI信号指标
        "RSI_OVERSOLD_30": "If(Less(RSI($close, 14), 30), 1, 0)",    # RSI超卖信号
        "RSI_OVERBOUGHT_70": "If(Greater(RSI($close, 14), 70), 1, 0)",  # RSI超买信号
        "RSI_OVERSOLD_20": "If(Less(RSI($close, 14), 20), 1, 0)",    # 极度超卖
        "RSI_OVERBOUGHT_80": "If(Greater(RSI($close, 14), 80), 1, 0)",  # 极度超买
        
        # ATR相关信号
        "ATR_VOLATILITY_HIGH": "If(Greater(ATR($high, $low, $close, 14), Mean(ATR($high, $low, $close, 14), 20)), 1, 0)",  # 波动率异常
        "ATR_SQUEEZE": "If(Less(ATR($high, $low, $close, 14), Multiply(Mean(ATR($high, $low, $close, 14), 50), 0.5)), 1, 0)",  # 低波动率
        
        # 复合振荡器信号
        "RSI_DIVERGENCE": "If(And(Less(RSI($close, 14), 30), Greater($close, Delay($close, 5))), 1, 0)",  # RSI背离
    }
    
    # 指标分类定义
    CATEGORIES = {
        "rsi": ["RSI_6", "RSI_12", "RSI_14", "RSI_21", "RSI_30"],
        "atr": ["ATR_7", "ATR_14", "ATR_21", "ATR_30"],
        "rsi_signals": ["RSI_OVERSOLD_30", "RSI_OVERBOUGHT_70", "RSI_OVERSOLD_20", 
                       "RSI_OVERBOUGHT_80", "RSI_DIVERGENCE"],
        "atr_signals": ["ATR_VOLATILITY_HIGH", "ATR_SQUEEZE"],
        "short_term": ["RSI_6", "RSI_12", "ATR_7"],
        "standard": ["RSI_14", "ATR_14"],
        "long_term": ["RSI_21", "RSI_30", "ATR_21", "ATR_30"]
    }