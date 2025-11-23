"""
模式识别指标集合 - 配置式定义

基于表达式引擎的K线模式和价格模式识别，
包括Pin Bar、Gap等经典技术分析模式。
"""

from ginkgo.features.definitions.base import BaseDefinition


class PatternDetectionIndicators(BaseDefinition):
    """模式识别指标类 - 配置式定义"""
    
    NAME = "Patterns"
    DESCRIPTION = "模式识别技术指标集合，包含K线模式、Gap、趋势模式等技术分析模式"
    
    # 模式识别指标表达式定义
    EXPRESSIONS = {
        # Pin Bar模式检测
        "PINBAR_BULLISH": "If(And(Greater(Subtract($close, $open), 0), Greater(Subtract($open, $low), Multiply(Subtract($high, $low), 0.6))), 1, 0)",  # 看涨Pin Bar
        "PINBAR_BEARISH": "If(And(Less(Subtract($close, $open), 0), Greater(Subtract($high, $close), Multiply(Subtract($high, $low), 0.6))), 1, 0)",  # 看跌Pin Bar
        
        # Gap模式检测
        "GAP_UP": "If(Greater($low, Delay($high, 1)), 1, 0)",  # 向上跳空
        "GAP_DOWN": "If(Less($high, Delay($low, 1)), 1, 0)",  # 向下跳空
        "GAP_FILLED_UP": "If(And(Greater(Delay($low, 1), Delay($high, 2)), Less($low, Delay($high, 2))), 1, 0)",  # 向上跳空回补
        "GAP_FILLED_DOWN": "If(And(Less(Delay($high, 1), Delay($low, 2)), Greater($high, Delay($low, 2))), 1, 0)",  # 向下跳空回补
        
        # 吞没模式
        "BULLISH_ENGULFING": "If(And(Less(Delay($open, 1), Delay($close, 1)), Greater($open, $close), Greater($open, Delay($close, 1)), Less($close, Delay($open, 1))), 1, 0)",
        "BEARISH_ENGULFING": "If(And(Greater(Delay($open, 1), Delay($close, 1)), Less($open, $close), Less($open, Delay($close, 1)), Greater($close, Delay($open, 1))), 1, 0)",
        
        # 十字星模式
        "DOJI": "If(Less(Abs(Subtract($close, $open)), Multiply(Subtract($high, $low), 0.1)), 1, 0)",  # 十字星
        "DOJI_DRAGONFLY": "If(And(Less(Abs(Subtract($close, $open)), Multiply(Subtract($high, $low), 0.1)), Less(Subtract($high, $close), Multiply(Subtract($high, $low), 0.1))), 1, 0)",  # 蜻蜓十字星
        
        # 锤子线模式
        "HAMMER": "If(And(Less(Abs(Subtract($close, $open)), Multiply(Subtract($high, $low), 0.3)), Greater(Subtract(Min($close, $open), $low), Multiply(Subtract($high, $low), 0.6))), 1, 0)",
        "INVERTED_HAMMER": "If(And(Less(Abs(Subtract($close, $open)), Multiply(Subtract($high, $low), 0.3)), Greater(Subtract($high, Max($close, $open)), Multiply(Subtract($high, $low), 0.6))), 1, 0)",
        
        # 趋势模式
        "HIGHER_HIGH": "If(And(Greater($high, Delay($high, 1)), Greater(Delay($high, 1), Delay($high, 2))), 1, 0)",  # 更高高点
        "LOWER_LOW": "If(And(Less($low, Delay($low, 1)), Less(Delay($low, 1), Delay($low, 2))), 1, 0)",  # 更低低点
        "DOUBLE_TOP": "If(And(Less(Abs(Subtract($high, Delay($high, 5))), Multiply($high, 0.02)), Less(Min(Delay($high, 1), Delay($high, 2)), Multiply($high, 0.95))), 1, 0)",  # 双顶模式
        "DOUBLE_BOTTOM": "If(And(Less(Abs(Subtract($low, Delay($low, 5))), Multiply($low, 0.02)), Greater(Max(Delay($low, 1), Delay($low, 2)), Multiply($low, 1.05))), 1, 0)",  # 双底模式
    }
    
    # 指标分类定义
    CATEGORIES = {
        "pinbar": ["PINBAR_BULLISH", "PINBAR_BEARISH"],
        "gaps": ["GAP_UP", "GAP_DOWN", "GAP_FILLED_UP", "GAP_FILLED_DOWN"],
        "engulfing": ["BULLISH_ENGULFING", "BEARISH_ENGULFING"],
        "doji": ["DOJI", "DOJI_DRAGONFLY"],
        "hammer": ["HAMMER", "INVERTED_HAMMER"],
        "trend_patterns": ["HIGHER_HIGH", "LOWER_LOW", "DOUBLE_TOP", "DOUBLE_BOTTOM"],
        "bullish": ["PINBAR_BULLISH", "GAP_UP", "BULLISH_ENGULFING", "HAMMER", "HIGHER_HIGH", "DOUBLE_BOTTOM"],
        "bearish": ["PINBAR_BEARISH", "GAP_DOWN", "BEARISH_ENGULFING", "INVERTED_HAMMER", "LOWER_LOW", "DOUBLE_TOP"],
        "reversal": ["PINBAR_BULLISH", "PINBAR_BEARISH", "BULLISH_ENGULFING", "BEARISH_ENGULFING", 
                    "DOJI", "HAMMER", "INVERTED_HAMMER", "DOUBLE_TOP", "DOUBLE_BOTTOM"],
        "continuation": ["GAP_UP", "GAP_DOWN", "HIGHER_HIGH", "LOWER_LOW"]
    }