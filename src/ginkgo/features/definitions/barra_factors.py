"""
MSCI Barra因子集合 - 配置式定义

MSCI Barra全球股票风险模型的标准因子，
包含风格因子、行业因子等工业界广泛应用的风险因子体系。
"""

from ginkgo.features.definitions.base import BaseDefinition


class BarraFactors(BaseDefinition):
    """MSCI Barra因子表达式类 - 全球风险管理工业标准"""
    
    NAME = "Barra"
    DESCRIPTION = "MSCI Barra全球股票风险模型，包含风格因子、行业因子等工业标准风险因子"
    
    # Barra因子表达式定义
    EXPRESSIONS = {
        # 核心风格因子 (Style Factors)
        "SIZE": "Log($market_cap)",                                              # 规模因子 - 对数市值
        "BETA": "MarketBeta($returns, $market_returns, 252)",                    # 市场Beta - 252日回归Beta
        "MOMENTUM": "RelativeStrength($returns, 252, 21)",                       # 动量因子 - 相对强度
        "RESIDUAL_VOLATILITY": "ResidualVolatility($residual_returns, 252)",     # 残差波动率
        "SIZE_NONLINEAR": "Power(SIZE, 3)",                                      # 非线性规模因子
        
        # 价值类因子
        "BOOK_TO_PRICE": "BookToPrice($book_value, $market_cap)",                # 账面市值比
        "EARNINGS_YIELD": "EarningsYield($earnings, $market_cap)",               # 盈利收益率
        "CASH_EARNINGS_TO_PRICE": "CashEarningsToPrice($cash_earnings, $market_cap)", # 现金盈利价格比
        
        # 成长类因子
        "GROWTH": "EarningsGrowth($earnings, 5)",                                # 盈利增长率
        "SALES_GROWTH": "SalesGrowth($sales, 5)",                                # 销售增长率
        "EARNINGS_REVISION": "EarningsRevision($estimates, 3)",                  # 盈利预期修正
        
        # 质量类因子
        "LEVERAGE": "FinancialLeverage($total_debt, $total_assets)",             # 财务杠杆
        "LIQUIDITY": "ShareTurnover($volume, $shares_outstanding, 252)",          # 股票流动性
        "EARNINGS_VARIABILITY": "EarningsVariability($quarterly_earnings, 20)",   # 盈利变异性
        
        # 分红类因子
        "DIVIDEND_YIELD": "DividendYield($dividends, $market_cap)",              # 股息收益率
        "DIVIDEND_GROWTH": "DividendGrowth($dividends, 5)",                      # 股息增长率
        
        # 行业因子 (基于GICS分类)
        "ENERGY": "IndustryDummy('10')",                                         # 能源行业
        "MATERIALS": "IndustryDummy('15')",                                      # 原材料行业  
        "INDUSTRIALS": "IndustryDummy('20')",                                    # 工业行业
        "CONSUMER_DISCRETIONARY": "IndustryDummy('25')",                         # 消费者自由选择行业
        "CONSUMER_STAPLES": "IndustryDummy('30')",                               # 消费者必需品行业
        "HEALTHCARE": "IndustryDummy('35')",                                     # 医疗保健行业
        "FINANCIALS": "IndustryDummy('40')",                                     # 金融行业
        "INFORMATION_TECHNOLOGY": "IndustryDummy('45')",                         # 信息技术行业
        "COMMUNICATION_SERVICES": "IndustryDummy('50')",                         # 通信服务行业
        "UTILITIES": "IndustryDummy('55')",                                      # 公用事业行业
        "REAL_ESTATE": "IndustryDummy('60')",                                    # 房地产行业
        
        # 国家/地区因子
        "COUNTRY_CHINA": "CountryDummy('CN')",                                   # 中国
        "COUNTRY_USA": "CountryDummy('US')",                                     # 美国
        "COUNTRY_JAPAN": "CountryDummy('JP')",                                   # 日本
        "COUNTRY_EUROPE": "RegionDummy('EU')",                                   # 欧洲
        
        # 市值细分因子
        "LARGE_CAP": "MarketCapSegment('large')",                                # 大盘股
        "MID_CAP": "MarketCapSegment('mid')",                                    # 中盘股
        "SMALL_CAP": "MarketCapSegment('small')",                                # 小盘股
        
        # 风险调整因子
        "VOLATILITY": "RealizedVolatility($returns, 252)",                       # 已实现波动率
        "SKEWNESS": "ReturnSkewness($returns, 252)",                             # 收益率偏度
        "KURTOSIS": "ReturnKurtosis($returns, 252)",                             # 收益率峰度
        
        # 交易行为因子
        "TURNOVER": "AverageTurnover($turnover, 252)",                           # 平均换手率
        "PRICE_TREND": "PriceTrend($price, 126)",                                # 价格趋势
        "VOLUME_TREND": "VolumeTrend($volume, 63)",                              # 成交量趋势
        
        # 分析师因子
        "ANALYST_COVERAGE": "AnalystCoverage($analyst_count)",                   # 分析师覆盖度
        "ANALYST_DISPERSION": "AnalystDispersion($estimates_std, $estimates_mean)", # 分析师分歧度
        "RECOMMENDATION": "AnalystRecommendation($recommendation_score)",         # 分析师推荐
        
        # 公司治理因子
        "BOARD_INDEPENDENCE": "BoardIndependence($independent_directors, $total_directors)", # 董事会独立性
        "INSIDER_OWNERSHIP": "InsiderOwnership($insider_shares, $total_shares)",  # 内部人持股
        "INSTITUTIONAL_OWNERSHIP": "InstitutionalOwnership($institutional_shares, $total_shares)", # 机构持股
    }
    
    # 因子分类定义
    CATEGORIES = {
        # 核心风格因子 (Barra经典10因子)
        "core_style": ["SIZE", "BETA", "MOMENTUM", "RESIDUAL_VOLATILITY", "SIZE_NONLINEAR",
                      "BOOK_TO_PRICE", "LIQUIDITY", "EARNINGS_YIELD", "GROWTH", "LEVERAGE"],
        
        # 按投资风格分类
        "value": ["BOOK_TO_PRICE", "EARNINGS_YIELD", "CASH_EARNINGS_TO_PRICE", "DIVIDEND_YIELD"],
        "growth": ["GROWTH", "SALES_GROWTH", "EARNINGS_REVISION"],
        "quality": ["LEVERAGE", "EARNINGS_VARIABILITY", "DIVIDEND_GROWTH"],
        "momentum": ["MOMENTUM", "PRICE_TREND"],
        "size": ["SIZE", "SIZE_NONLINEAR", "LARGE_CAP", "MID_CAP", "SMALL_CAP"],
        "low_vol": ["RESIDUAL_VOLATILITY", "VOLATILITY", "BETA"],
        
        # 行业分类 (GICS一级行业)
        "sectors": ["ENERGY", "MATERIALS", "INDUSTRIALS", "CONSUMER_DISCRETIONARY", "CONSUMER_STAPLES",
                   "HEALTHCARE", "FINANCIALS", "INFORMATION_TECHNOLOGY", "COMMUNICATION_SERVICES", 
                   "UTILITIES", "REAL_ESTATE"],
        
        # 地区分类
        "regions": ["COUNTRY_CHINA", "COUNTRY_USA", "COUNTRY_JAPAN", "COUNTRY_EUROPE"],
        
        # 风险相关
        "risk_factors": ["BETA", "RESIDUAL_VOLATILITY", "VOLATILITY", "LEVERAGE", "LIQUIDITY"],
        
        # 交易相关
        "trading": ["LIQUIDITY", "TURNOVER", "VOLUME_TREND"],
        
        # 基本面相关
        "fundamentals": ["BOOK_TO_PRICE", "EARNINGS_YIELD", "GROWTH", "LEVERAGE", "DIVIDEND_YIELD"],
        
        # 市场行为
        "market_behavior": ["MOMENTUM", "PRICE_TREND", "VOLUME_TREND", "TURNOVER"],
        
        # 分析师相关
        "analyst": ["ANALYST_COVERAGE", "ANALYST_DISPERSION", "RECOMMENDATION", "EARNINGS_REVISION"],
        
        # 公司治理
        "governance": ["BOARD_INDEPENDENCE", "INSIDER_OWNERSHIP", "INSTITUTIONAL_OWNERSHIP"],
        
        # 统计特征
        "statistical": ["VOLATILITY", "SKEWNESS", "KURTOSIS", "RESIDUAL_VOLATILITY"],
        
        # 核心风险因子 (风险管理必备)
        "risk_core": ["SIZE", "BETA", "MOMENTUM", "BOOK_TO_PRICE", "RESIDUAL_VOLATILITY", "LIQUIDITY"]
    }