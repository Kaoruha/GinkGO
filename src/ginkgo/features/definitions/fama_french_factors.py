"""
Fama-French因子集合 - 配置式定义

Eugene Fama和Kenneth French提出的经典因子模型，
包含市场、规模、价值、盈利能力、投资模式等学术界公认的风险因子。
"""

from ginkgo.features.definitions.base import BaseDefinition


class FamaFrenchFactors(BaseDefinition):
    """Fama-French因子表达式类 - 学术界金标准因子模型"""
    
    NAME = "FamaFrench"
    DESCRIPTION = "Fama-French多因子模型，包含市场、规模、价值、盈利能力、投资模式等经典学术因子"
    
    # Fama-French因子表达式定义
    EXPRESSIONS = {
        # 经典三因子模型 (Fama-French 1993)
        "MKT_RF": "Subtract($market_return, $risk_free_rate)",                    # 市场因子 - 超额收益
        "SMB": "Subtract($small_cap_return, $large_cap_return)",                  # 规模因子 - 小盘股溢价
        "HML": "Subtract($high_bm_return, $low_bm_return)",                       # 价值因子 - 高账面市值比溢价
        
        # 五因子模型扩展 (Fama-French 2015)
        "RMW": "Subtract($robust_profit_return, $weak_profit_return)",            # 盈利能力因子 - 稳健减弱盈利
        "CMA": "Subtract($conservative_invest_return, $aggressive_invest_return)", # 投资模式因子 - 保守减激进投资
        
        # 动量因子 (Carhart 1997 - 四因子模型)
        "MOM": "Subtract($winner_return, $loser_return)",                         # 动量因子 - 赢家减输家组合
        "UMD": "MomentumPortfolio($monthly_returns, 12, 1)",                      # Up Minus Down - 动量组合
        
        # 短期反转因子
        "ST_REV": "Subtract($losers_1m_return, $winners_1m_return)",              # 短期反转 - 1个月反转效应
        
        # 长期反转因子  
        "LT_REV": "Subtract($losers_5y_return, $winners_5y_return)",              # 长期反转 - 5年反转效应
        
        # 质量因子 (近期扩展)
        "QMJ": "Subtract($quality_return, $junk_return)",                         # 质量减垃圾股
        
        # 低风险异象
        "BAB": "Subtract($low_beta_return, $high_beta_return)",                   # Betting Against Beta
        
        # 规模因子细分
        "SMB_B": "SmallMinusBig($book_to_market, 'balanced')",                    # 规模因子(账面市值比平衡)
        "SMB_N": "SmallMinusBig($neutral, 'neutral')",                            # 规模因子(中性)
        
        # 价值因子细分
        "HML_S": "HighMinusLow($small_caps, 'small')",                            # 价值因子(小盘股)
        "HML_B": "HighMinusLow($big_caps, 'big')",                                # 价值因子(大盘股)
        
        # 运营盈利能力 (Alternative to RMW)
        "RMW_OP": "ProfitabilityFactor($operating_profit, $book_equity)",         # 基于运营利润的盈利能力
        
        # 资产增长 (Alternative to CMA)  
        "CMA_AG": "AssetGrowthFactor($asset_growth_rate)",                        # 基于资产增长的投资因子
        
        # 股息收益率因子
        "DIV": "DividendYieldFactor($dividend_yield, $market_return)",            # 股息因子
        
        # 波动率因子
        "VOL": "VolatilityFactor($realized_volatility, $expected_volatility)",    # 波动率因子
        
        # 流动性因子
        "LIQ": "LiquidityFactor($trading_volume, $market_cap)",                   # 流动性因子
    }
    
    # 因子分类定义
    CATEGORIES = {
        # 经典模型
        "ff3": ["MKT_RF", "SMB", "HML"],                                          # 三因子模型
        "carhart4": ["MKT_RF", "SMB", "HML", "MOM"],                             # 四因子模型(含动量)
        "ff5": ["MKT_RF", "SMB", "HML", "RMW", "CMA"],                           # 五因子模型
        "ff6": ["MKT_RF", "SMB", "HML", "RMW", "CMA", "MOM"],                    # 六因子模型
        
        # 按因子类型分类
        "market": ["MKT_RF"],                                                     # 市场因子
        "size": ["SMB", "SMB_B", "SMB_N"],                                       # 规模因子
        "value": ["HML", "HML_S", "HML_B"],                                      # 价值因子
        "profitability": ["RMW", "RMW_OP"],                                      # 盈利能力因子
        "investment": ["CMA", "CMA_AG"],                                          # 投资因子
        "momentum": ["MOM", "UMD"],                                               # 动量因子
        "reversal": ["ST_REV", "LT_REV"],                                        # 反转因子
        "quality": ["QMJ"],                                                       # 质量因子
        "low_risk": ["BAB", "VOL"],                                              # 低风险因子
        "income": ["DIV"],                                                        # 收益因子
        "liquidity": ["LIQ"],                                                     # 流动性因子
        
        # 时间维度分类
        "short_term": ["ST_REV", "MOM"],                                          # 短期因子
        "long_term": ["LT_REV", "HML", "RMW", "CMA"],                           # 长期因子
        
        # 风险属性分类
        "systematic": ["MKT_RF", "SMB", "HML"],                                   # 系统性风险因子
        "behavioral": ["MOM", "ST_REV", "LT_REV"],                               # 行为金融因子
        "fundamental": ["RMW", "CMA", "QMJ", "DIV"],                             # 基本面因子
        
        # 核心因子 (最重要的因子)
        "core": ["MKT_RF", "SMB", "HML", "RMW", "CMA", "MOM"]                    # 核心六因子
    }