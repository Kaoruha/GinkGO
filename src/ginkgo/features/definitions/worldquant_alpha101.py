"""
WorldQuant Alpha101因子集合 - 配置式定义

WorldQuant公开的101个Alpha因子表达式，
展现了实战导向的复杂因子构造方法和排名技术的应用。
"""

from .base import BaseDefinition


class WorldQuantAlpha101(BaseDefinition):
    """WorldQuant Alpha101因子表达式类 - 实战导向的复杂组合因子"""
    
    NAME = "WorldQuantAlpha101"
    DESCRIPTION = "WorldQuant公开的101个Alpha因子，展现实战级别的复杂因子构造和排名技术"
    
    # WorldQuant Alpha101因子表达式定义 (精选代表性因子)
    EXPRESSIONS = {
        # 经典Alpha因子 (前20个)
        "ALPHA_001": "Rank(Ts_ArgMax(SignedPower(If($returns < 0, Std($returns, 20), $close), 2), 5)) - 0.5",
        "ALPHA_002": "(-1 * Correlation(Rank($delta_close), Rank($volume), 6))",
        "ALPHA_003": "(-1 * Correlation(Rank($open), Rank($volume), 10))",
        "ALPHA_004": "(-1 * Ts_Rank(Rank($close), 9))",
        "ALPHA_005": "(Rank($open - Ts_Mean($vwap, 10)) * (-1 * Abs(Rank($close - $vwap))))",
        "ALPHA_006": "(-1 * Correlation($open, $volume, 10))",
        "ALPHA_007": "If(Adv20($volume) < $volume, (-1 * Ts_Rank(Abs($delta_close), 60)) * Sign($delta_close), -1)",
        "ALPHA_008": "(-1 * Rank(Ts_Rank($open, 5) + Ts_Rank($returns, 5)))",
        "ALPHA_009": "If(0 < Ts_Min($delta_close, 5), $delta_close, If(Ts_Max($delta_close, 5) < 0, $delta_close, (-1 * $delta_close)))",
        "ALPHA_010": "Rank(If(Ts_Min($delta_close, 4) > 0, $delta_close, If(Ts_Max($delta_close, 4) < 0, $delta_close, (-1 * $delta_close))))",
        
        "ALPHA_011": "((Rank(Ts_Max($vwap - $close, 3)) + Rank(Ts_Min($vwap - $close, 3))) * Rank($delta_volume))",
        "ALPHA_012": "(Sign($delta_volume) * (-1 * $delta_close))",
        "ALPHA_013": "(-1 * Rank(Covariance(Rank($close), Rank($volume), 5)))",
        "ALPHA_014": "((-1 * Rank($delta_returns)) * Correlation($open, $volume, 10))",
        "ALPHA_015": "(-1 * Sum(Rank(Correlation(Rank($high), Rank($volume), 3)), 3))",
        "ALPHA_016": "(-1 * Rank(Covariance(Rank($high), Rank($volume), 5)))",
        "ALPHA_017": "(((-1 * Rank(Ts_Rank($close, 10))) * Rank($delta_close / $close)) * Rank(Ts_Rank($volume, 5)))",
        "ALPHA_018": "(-1 * Rank((Std($abs_returns, 5) + $delta_close + Correlation($close, $volume, 2))))",
        "ALPHA_019": "((-1 * Sign($delta_close + $delta_open)) * (1 + Rank(1 + Sum($returns, 250))))",
        "ALPHA_020": "(((-1 * Rank($open - Delay($high, 1))) * Rank($open - Delay($close, 1))) * Rank($open - Delay($low, 1)))",
        
        # 中等复杂度Alpha因子 (21-50)
        "ALPHA_021": "If(Sum($close, 8) / 8 + Std($close, 8) < Sum($close, 2) / 2, (-1 * 1), If(Sum($close, 2) / 2 < Sum($close, 8) / 8 - Std($close, 8), 1, If(1 <= $volume / Adv20($volume), 1, (-1 * 1))))",
        "ALPHA_022": "(-1 * $delta_close * Correlation($close, $volume, 15))",
        "ALPHA_023": "If(Sum($high, 20) / 20 < $high, (-1 * $delta_high), 0)",
        "ALPHA_024": "If($delta_high <= 0, 0, $delta_high / Delay($close, 1))",
        "ALPHA_025": "Rank(((-1 * $returns) * Adv20($volume) * $vwap * ($high - $close)))",
        
        "ALPHA_030": "(1.0 - Rank((Sign($delta_close) + Sign(Delay($delta_close, 1)) + Sign(Delay($delta_close, 2)))))",
        "ALPHA_031": "(Rank(Rank(Rank($decay_linear))) + Rank((-1 * Rank($delta_close))))",
        "ALPHA_032": "(Scale(Sum(Correlation($high, $volume, 3), 10)) / 3)",
        "ALPHA_033": "Rank((-1 * Ts_Min($low, 5)) + Delay(Ts_Min($low, 5), 5))",
        "ALPHA_034": "Rank(((1 - Rank((Std($returns, 2) / Std($returns, 5)))) + (1 - Rank($delta_close))))",
        
        # 高复杂度Alpha因子 (51-80)
        "ALPHA_051": "(((Delay($close, 20) - Delay($close, 10)) / 10) - (($close - Delay($close, 10)) / 10))",
        "ALPHA_052": "((((-1 * Ts_Min($low, 5)) + Delay(Ts_Min($low, 5), 5)) * Rank(((Sum($returns, 240) - Sum($returns, 20)) / 220))) * Ts_Rank($volume, 5))",
        "ALPHA_053": "(-1 * $delta_close * Correlation($close, $volume, 10))",
        "ALPHA_054": "((-1 * (($low - $close) * ($open**5))) / (($low - $high) * ($close**5)))",
        "ALPHA_055": "(-1 * Correlation(Rank($close - Ts_Min($low, 12)), Rank(Adv20($volume)), 6))",
        
        "ALPHA_060": "(0 - (1 * (($close - $low) - ($high - $close)) / ($high - $low) * $volume))",
        "ALPHA_061": "(Rank($vwap - Ts_Min($vwap, 16)) < Rank(Correlation($vwap, Adv180($volume), 18)))",
        "ALPHA_062": "((Rank(Correlation($vwap, Sum(Adv20($volume), 22), 10)) < Rank(((Rank($open) + Rank($open)) < (Rank(($high + $low)) / 2)))) * -1)",
        "ALPHA_063": "((Rank($decay_linear) - Rank($decay_linear**$delta_volume)) / Rank($decay_linear**$delta_volume))",
        "ALPHA_064": "((Rank(Correlation(Sum($close, 10), Sum(Adv60($volume), 10), 10)) < Rank((-1 * Std($close, 10)))) * -1)",
        
        # 终极复杂Alpha因子 (81-101)
        "ALPHA_081": "((Rank(Log(Product(Rank((Rank(Correlation($vwap, Sum(Adv10($volume), 50), 8))**4)), 15))) < Rank(Correlation(Rank($vwap), Rank($volume), 5))) * -1)",
        "ALPHA_082": "((Min(Rank($decay_linear), Ts_Rank($decay_linear, 20)) + Ts_Rank((-1 * $delta_close), 8)) < Ts_Rank(((($high + $low) / 2) * 0.2 + $vwap * 0.8), 15))",
        "ALPHA_083": "((Rank(Delay(((($high - $low) / (Sum($close, 5) / 5)) * $volume), 2)) * Rank(Rank($volume))) / (((($high - $low) / (Sum($close, 5) / 5)) * $volume) / Adv20($volume)))",
        "ALPHA_084": "SignedPower(Ts_Rank($vwap - Ts_Max($vwap, 15), 21), $delta_close)",
        "ALPHA_085": "(Rank(Correlation(($high * 0.876703 + $close * 0.123297), Adv30($volume), 10))**Rank(Correlation(Ts_Rank(($high + $low) / 2, 4), Ts_Rank($volume, 10), 7)))",
        
        "ALPHA_090": "((Rank((($close - Ts_Max($close, 5)) / Ts_Max($close, 5))) * Rank(Correlation(IndNeutralize($adv40, $sector), $low, 5))) * -1)",
        "ALPHA_091": "((Ts_Rank(Delay($close, 5), 20) * Rank(((1 - Rank(($high * $low))) * (1 + Rank($volume))))) * -1)",
        "ALPHA_092": "Min(Ts_Rank($decay_linear, 30), Ts_Rank($decay_linear, 4))",
        "ALPHA_093": "(Ts_Rank($decay_linear, 73) / Ts_Rank($decay_linear, 11))",
        "ALPHA_094": "((Rank(($vwap - Ts_Min($vwap, 11)))**Ts_Rank(Correlation(Ts_Rank($vwap, 20), Ts_Rank(Adv60($volume), 4), 18), 3)) * -1)",
        
        "ALPHA_095": "(Rank(($open - Ts_Min($open, 12))) < Ts_Rank(Rank(Correlation(Sum(($high + $low) / 2, 19), Sum(Adv40($volume), 19), 13)), 5))",
        "ALPHA_096": "((Correlation(Rank($vwap), Rank($volume), 4) < Rank(Ts_Rank(Ts_ArgMax($close, 7), 5))) * -1)",
        "ALPHA_097": "((Rank($decay_linear) - Rank(Correlation(IndNeutralize($adv20, $sector), $low, 7))) / Rank(Ts_Rank($delta_close, 14)))",
        "ALPHA_098": "(Rank($decay_linear)**Rank(Correlation(Sum($adv5, 26), Sum($adv15, 26), 4)))",
        "ALPHA_099": "((Rank(Correlation(Sum($high, 5), Sum($volume, 5), 5)) < Rank(Ts_Rank(Ts_ArgMin($high, 30), 4))) * -1)",
        "ALPHA_100": "(0 - (1 * (((1.5 * Scale(IndNeutralize($close, $sector))) - Scale(IndNeutralize(Delay($close, 1), $sector))) * (($volume / Adv20($volume)) / 2))))",
        "ALPHA_101": "((Correlation(Rank($close), Rank(Adv20($volume)), 9) < Rank(((9.5 - Ts_Rank(Ts_ArgMax(DecayLinear($high, 2), 4), 14)) / 9))) * -1)",
        
        # 基于排名的衍生因子
        "RANK_VOLUME_PRICE": "Rank($volume) / Rank($close)",
        "RANK_MOMENTUM_VOLATILITY": "Rank($momentum_20) / Rank($volatility_20)",
        "CROSS_RANK_CORRELATION": "Correlation(Rank($close), Rank($volume), 10)",
        "RANK_MEAN_REVERSION": "Rank($close) - Rank(Ts_Mean($close, 20))",
        
        # 时间序列排名因子
        "TS_RANK_CLOSE": "Ts_Rank($close, 20)",
        "TS_RANK_VOLUME": "Ts_Rank($volume, 20)", 
        "TS_RANK_RETURNS": "Ts_Rank($returns, 20)",
        "TS_RANK_VWAP": "Ts_Rank($vwap, 20)",
        
        # 复合排名因子
        "COMPOSITE_RANK_1": "Rank(Ts_Rank($close, 10) + Ts_Rank($volume, 10))",
        "COMPOSITE_RANK_2": "Rank(Correlation($close, $volume, 5) + $momentum_10)",
    }
    
    # 因子分类定义
    CATEGORIES = {
        # 按复杂度分类
        "simple": ["ALPHA_001", "ALPHA_002", "ALPHA_003", "ALPHA_004", "ALPHA_005"],
        "basic": ["ALPHA_006", "ALPHA_007", "ALPHA_008", "ALPHA_009", "ALPHA_010"],
        "intermediate": ["ALPHA_011", "ALPHA_012", "ALPHA_013", "ALPHA_014", "ALPHA_015",
                        "ALPHA_016", "ALPHA_017", "ALPHA_018", "ALPHA_019", "ALPHA_020"],
        "advanced": ["ALPHA_021", "ALPHA_022", "ALPHA_023", "ALPHA_024", "ALPHA_025",
                    "ALPHA_030", "ALPHA_031", "ALPHA_032", "ALPHA_033", "ALPHA_034"],
        "complex": ["ALPHA_051", "ALPHA_052", "ALPHA_053", "ALPHA_054", "ALPHA_055",
                   "ALPHA_060", "ALPHA_061", "ALPHA_062", "ALPHA_063", "ALPHA_064"],
        "ultimate": ["ALPHA_081", "ALPHA_082", "ALPHA_083", "ALPHA_084", "ALPHA_085",
                    "ALPHA_090", "ALPHA_091", "ALPHA_092", "ALPHA_093", "ALPHA_094",
                    "ALPHA_095", "ALPHA_096", "ALPHA_097", "ALPHA_098", "ALPHA_099",
                    "ALPHA_100", "ALPHA_101"],
        
        # 按技术特征分类
        "correlation_based": ["ALPHA_002", "ALPHA_003", "ALPHA_006", "ALPHA_013", "ALPHA_014"],
        "rank_based": ["ALPHA_001", "ALPHA_004", "ALPHA_005", "ALPHA_008", "RANK_VOLUME_PRICE", 
                      "RANK_MOMENTUM_VOLATILITY"],
        "time_series": ["TS_RANK_CLOSE", "TS_RANK_VOLUME", "TS_RANK_RETURNS", "TS_RANK_VWAP"],
        "volume_price": ["ALPHA_007", "ALPHA_012", "ALPHA_015", "ALPHA_016", "ALPHA_017"],
        "momentum_reversal": ["ALPHA_009", "ALPHA_010", "ALPHA_019", "ALPHA_022"],
        "volatility": ["ALPHA_018", "ALPHA_034"],
        
        # 按数据依赖分类
        "price_only": ["ALPHA_004", "ALPHA_009", "ALPHA_010", "ALPHA_051"],
        "price_volume": ["ALPHA_002", "ALPHA_003", "ALPHA_006", "ALPHA_007", "ALPHA_012"],
        "vwap_dependent": ["ALPHA_005", "ALPHA_011", "ALPHA_060", "ALPHA_061", "ALPHA_081"],
        "sector_neutral": ["ALPHA_090", "ALPHA_097", "ALPHA_100"],
        
        # 按投资策略分类
        "momentum": ["ALPHA_019", "ALPHA_022", "ALPHA_051", "RANK_MOMENTUM_VOLATILITY"],
        "mean_reversion": ["ALPHA_009", "ALPHA_010", "ALPHA_053", "RANK_MEAN_REVERSION"],
        "volume_analysis": ["ALPHA_007", "ALPHA_012", "ALPHA_015", "ALPHA_021"],
        "cross_sectional": ["CROSS_RANK_CORRELATION", "ALPHA_090", "ALPHA_097"],
        
        # 按时间窗口分类
        "short_term": ["ALPHA_002", "ALPHA_003", "ALPHA_006", "ALPHA_013"],  # <=10天
        "medium_term": ["ALPHA_001", "ALPHA_004", "ALPHA_051", "TS_RANK_CLOSE"],  # 10-30天
        "long_term": ["ALPHA_019", "ALPHA_081", "ALPHA_094"],  # >30天
        
        # 实战应用分类
        "high_frequency": ["ALPHA_002", "ALPHA_003", "ALPHA_012", "ALPHA_053"],
        "swing_trading": ["ALPHA_001", "ALPHA_009", "ALPHA_010", "ALPHA_051"],
        "portfolio_construction": ["ALPHA_090", "ALPHA_097", "ALPHA_100"],
        "risk_management": ["ALPHA_034", "ALPHA_064", "ALPHA_082"],
        
        # 核心推荐因子
        "top_performers": ["ALPHA_001", "ALPHA_002", "ALPHA_009", "ALPHA_051", "ALPHA_101"],
        "beginner_friendly": ["ALPHA_002", "ALPHA_003", "ALPHA_012", "RANK_VOLUME_PRICE"],
        "advanced_users": ["ALPHA_081", "ALPHA_094", "ALPHA_101", "COMPOSITE_RANK_1"],
        
        # 复合因子
        "composite": ["COMPOSITE_RANK_1", "COMPOSITE_RANK_2", "RANK_VOLUME_PRICE", "RANK_MOMENTUM_VOLATILITY"]
    }