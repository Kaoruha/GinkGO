"""
AQR因子集合 - 配置式定义

AQR Capital Management开发的经典因子，
包含Quality、Momentum、Value、Low Risk等在实战中表现优异的因子。
"""

from ginkgo.features.definitions.base import BaseDefinition


class AQRFactors(BaseDefinition):
    """AQR因子表达式类 - 量化巨头实战验证的经典因子"""
    
    NAME = "AQR"
    DESCRIPTION = "AQR Capital经典因子集合，包含Quality、Momentum、Value、Low Risk等实战验证的有效因子"
    
    # AQR因子表达式定义
    EXPRESSIONS = {
        # Quality因子 - AQR的招牌因子
        "QMJ": "QualityMinusJunk($quality_score, $junk_score)",                  # 质量减垃圾股
        "PROF": "Profitability($roe, $roa, $gross_profit_margin)",               # 盈利能力
        "GROW": "GrowthQuality($revenue_growth, $earnings_growth, $asset_growth)", # 成长质量
        "SAFE": "SafetyQuality($debt_equity, $earnings_volatility, $leverage)",   # 安全性质量
        "PAYOUT": "PayoutQuality($dividend_payout, $share_buyback)",             # 分红质量
        
        # Quality子因子 - 盈利能力维度
        "ROE": "ReturnOnEquity($net_income, $shareholders_equity)",               # 净资产收益率
        "ROA": "ReturnOnAssets($net_income, $total_assets)",                     # 总资产收益率
        "ROIC": "ReturnOnInvestedCapital($nopat, $invested_capital)",            # 投入资本回报率
        "GROSS_PROFIT_MARGIN": "GrossProfitMargin($gross_profit, $revenue)",     # 毛利率
        "OPERATING_MARGIN": "OperatingMargin($operating_income, $revenue)",      # 营业利润率
        
        # Quality子因子 - 成长质量维度
        "REVENUE_GROWTH_QUALITY": "RevenueGrowthQuality($revenue_growth, 5)",    # 营收增长质量
        "EARNINGS_GROWTH_QUALITY": "EarningsGrowthQuality($earnings_growth, 5)", # 盈利增长质量
        "CAPEX_EFFICIENCY": "CapexEfficiency($capex, $revenue_growth)",          # 资本开支效率
        
        # Quality子因子 - 安全性维度
        "DEBT_TO_EQUITY": "DebtToEquity($total_debt, $shareholders_equity)",      # 债务股本比
        "CURRENT_RATIO": "CurrentRatio($current_assets, $current_liabilities)",   # 流动比率
        "INTEREST_COVERAGE": "InterestCoverage($ebit, $interest_expense)",        # 利息保障倍数
        "ALTMAN_Z_SCORE": "AltmanZScore($working_capital, $retained_earnings, $ebit, $market_cap, $sales, $total_liabilities)", # Altman Z-Score
        
        # Time Series Momentum - AQR经典策略
        "TSMOM_1M": "TimeSeriesMomentum($returns, 21)",                          # 1个月时间序列动量
        "TSMOM_3M": "TimeSeriesMomentum($returns, 63)",                          # 3个月时间序列动量
        "TSMOM_12M": "TimeSeriesMomentum($returns, 252)",                        # 12个月时间序列动量
        "TSMOM_COMBO": "CombinedTimeSeriesMomentum($returns, [21, 63, 252])",    # 组合时间序列动量
        
        # Cross-Sectional Momentum
        "CSMOM_1M": "CrossSectionalMomentum($returns, 21)",                      # 1个月横截面动量
        "CSMOM_6M": "CrossSectionalMomentum($returns, 126)",                     # 6个月横截面动量
        "CSMOM_12M": "CrossSectionalMomentum($returns, 252)",                    # 12个月横截面动量
        
        # Betting Against Beta - 低Beta异象
        "BAB": "BettingAgainstBeta($beta, $market_cap)",                         # 做多低Beta，做空高Beta
        "LOW_BETA": "LowBetaFactor($beta, $volatility)",                         # 低Beta因子
        "LOW_VOL": "LowVolatilityFactor($volatility, $market_cap)",              # 低波动率因子
        
        # Value因子 - AQR改进版
        "HML_DEVIL": "ValueFactorDevil($book_to_market, $quality_adjustment)",    # 质量调整的价值因子
        "EARNINGS_TO_PRICE": "EarningsToPrice($earnings, $market_cap)",          # 盈利价格比
        "CASH_FLOW_TO_PRICE": "CashFlowToPrice($operating_cash_flow, $market_cap)", # 现金流价格比
        "SALES_TO_PRICE": "SalesToPrice($sales, $market_cap)",                   # 销售价格比
        "COMPOSITE_VALUE": "CompositeValue($book_to_market, $earnings_to_price, $cash_flow_to_price)", # 复合价值因子
        
        # Carry因子 - 套利交易
        "CARRY_FX": "CarryFactor($interest_rate_diff, $exchange_rate)",          # 外汇套利
        "CARRY_BOND": "BondCarry($yield_curve, $duration)",                      # 债券套利
        "CARRY_COMMODITY": "CommodityCarry($spot_price, $futures_price)",        # 商品套利
        
        # Defensive因子 - 防御性投资
        "DEFENSIVE": "DefensiveFactor($beta, $volatility, $earnings_volatility)", # 防御性因子
        "LOW_RISK": "LowRiskFactor($volatility, $beta, $leverage)",              # 低风险因子
        "QUALITY_DEFENSIVE": "QualityDefensive($quality_score, $defensive_score)", # 质量防御因子
        
        # Volatility Risk Premium
        "IVOL": "IdiosyncraticVolatility($residual_returns, 252)",               # 特异波动率
        "VOL_TERM_STRUCTURE": "VolatilityTermStructure($vol_short, $vol_long)",  # 波动率期限结构
        "VOL_SURFACE": "VolatilitySurface($implied_vol, $realized_vol)",         # 波动率曲面
        
        # Trend Following
        "TREND_1M": "TrendFollowing($price, 21)",                                # 1个月趋势跟踪
        "TREND_3M": "TrendFollowing($price, 63)",                                # 3个月趋势跟踪
        "TREND_12M": "TrendFollowing($price, 252)",                              # 12个月趋势跟踪
        "TREND_COMBO": "CombinedTrend($price, [21, 63, 252])",                   # 组合趋势因子
        
        # Mean Reversion
        "MEAN_REVERSION_ST": "MeanReversion($price, 5)",                         # 短期均值回归
        "MEAN_REVERSION_LT": "MeanReversion($price, 252)",                       # 长期均值回归
        
        # Risk Parity相关
        "RISK_PARITY": "RiskParityFactor($returns, $volatilities)",              # 风险平价因子
        "EQUAL_RISK_CONTRIB": "EqualRiskContribution($correlation_matrix, $volatilities)", # 等风险贡献
    }
    
    # 因子分类定义
    CATEGORIES = {
        # AQR核心策略
        "aqr_core": ["QMJ", "TSMOM_12M", "BAB", "HML_DEVIL"],                   # AQR四大核心因子
        
        # Quality因子族
        "quality": ["QMJ", "PROF", "GROW", "SAFE", "PAYOUT"],
        "profitability": ["ROE", "ROA", "ROIC", "GROSS_PROFIT_MARGIN", "OPERATING_MARGIN"],
        "growth_quality": ["REVENUE_GROWTH_QUALITY", "EARNINGS_GROWTH_QUALITY", "CAPEX_EFFICIENCY"],
        "safety": ["DEBT_TO_EQUITY", "CURRENT_RATIO", "INTEREST_COVERAGE", "ALTMAN_Z_SCORE"],
        
        # Momentum因子族
        "momentum": ["TSMOM_1M", "TSMOM_3M", "TSMOM_12M", "TSMOM_COMBO"],
        "cross_sectional_momentum": ["CSMOM_1M", "CSMOM_6M", "CSMOM_12M"],
        "trend": ["TREND_1M", "TREND_3M", "TREND_12M", "TREND_COMBO"],
        
        # Low Risk因子族
        "low_risk": ["BAB", "LOW_BETA", "LOW_VOL", "DEFENSIVE", "LOW_RISK"],
        "low_volatility": ["LOW_VOL", "IVOL", "VOL_TERM_STRUCTURE"],
        
        # Value因子族
        "value": ["HML_DEVIL", "EARNINGS_TO_PRICE", "CASH_FLOW_TO_PRICE", "SALES_TO_PRICE", "COMPOSITE_VALUE"],
        
        # Carry因子族
        "carry": ["CARRY_FX", "CARRY_BOND", "CARRY_COMMODITY"],
        
        # 防御性因子
        "defensive": ["DEFENSIVE", "QUALITY_DEFENSIVE", "LOW_RISK"],
        
        # 波动率相关
        "volatility": ["IVOL", "VOL_TERM_STRUCTURE", "VOL_SURFACE", "LOW_VOL"],
        
        # 均值回归
        "mean_reversion": ["MEAN_REVERSION_ST", "MEAN_REVERSION_LT"],
        
        # 风险管理
        "risk_managements": ["RISK_PARITY", "EQUAL_RISK_CONTRIB", "LOW_RISK"],
        
        # 时间维度
        "short_term": ["TSMOM_1M", "CSMOM_1M", "TREND_1M", "MEAN_REVERSION_ST"],
        "medium_term": ["TSMOM_3M", "TREND_3M"],
        "long_term": ["TSMOM_12M", "CSMOM_12M", "TREND_12M", "MEAN_REVERSION_LT"],
        
        # 策略类型
        "systematic": ["TSMOM_COMBO", "TREND_COMBO", "COMPOSITE_VALUE"],
        "factor_timing": ["VOL_TERM_STRUCTURE", "CARRY_FX"],
        
        # 核心实战因子
        "practical_core": ["QMJ", "TSMOM_12M", "BAB", "HML_DEVIL", "LOW_VOL", "DEFENSIVE"]
    }