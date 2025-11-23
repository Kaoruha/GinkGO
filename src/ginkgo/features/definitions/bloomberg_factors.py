"""
Bloomberg因子库 - 配置式定义

Bloomberg Terminal提供的机构级因子和指标，
涵盖基本面、技术面、风险管理、ESG等专业投资分析维度。

数据来源: Bloomberg Terminal - 全球领先的金融数据和分析平台
"""

from ginkgo.features.definitions.base import BaseDefinition


class BloombergFactors(BaseDefinition):
    """Bloomberg因子库 - 机构级专业投资因子"""
    
    NAME = "Bloomberg Professional Factors"
    DESCRIPTION = "Bloomberg Terminal提供的机构级因子，涵盖基本面、技术面、风险、ESG等专业投资分析维度"
    
    # Bloomberg因子表达式定义
    EXPRESSIONS = {
        # ===== 基本面因子 (Fundamental Factors) =====
        "pe_ratio": "PX_TO_BOOK_RATIO",  # 市盈率
        "pb_ratio": "PX_TO_BOOK_RATIO",  # 市净率
        "ps_ratio": "PX_TO_SALES_RATIO",  # 市销率
        "pcf_ratio": "PX_TO_CF_RATIO",  # 市现率
        "ev_ebitda": "EV_TO_T12M_EBITDA",  # 企业价值/EBITDA
        "ev_sales": "EV_TO_T12M_SALES",  # 企业价值/销售额
        "price_to_tangible_book": "PX_TO_TANG_BV_PER_SH",  # 价格/有形账面价值
        
        # 盈利能力指标
        "roe": "RETURN_ON_EQUITY",  # 净资产收益率
        "roa": "RETURN_ON_ASSET",  # 总资产收益率
        "roic": "RETURN_ON_INVESTED_CAPITAL",  # 投入资本回报率
        "gross_margin": "GROSS_MARGIN",  # 毛利率
        "operating_margin": "OPER_MARGIN",  # 营业利润率
        "net_margin": "NET_INCOME_MARGIN",  # 净利润率
        "ebitda_margin": "EBITDA_MARGIN",  # EBITDA利润率
        
        # 成长性指标
        "revenue_growth_1y": "SALES_GROWTH",  # 营收增长率
        "revenue_growth_3y": "SALES_GROWTH_3Y",  # 3年营收增长率
        "earnings_growth_1y": "EARN_GROWTH",  # 盈利增长率
        "earnings_growth_3y": "EARN_GROWTH_3Y",  # 3年盈利增长率
        "book_value_growth": "BOOK_VAL_GROWTH",  # 账面价值增长率
        "dividend_growth": "DVD_GROWTH",  # 股息增长率
        
        # 财务健康度
        "debt_to_equity": "TOT_DEBT_TO_TOT_EQY",  # 债务股本比
        "debt_to_assets": "TOT_DEBT_TO_TOT_ASSET",  # 债务资产比
        "current_ratio": "CUR_RATIO",  # 流动比率
        "quick_ratio": "QUICK_RATIO",  # 速动比率
        "cash_ratio": "CASH_RATIO",  # 现金比率
        "interest_coverage": "EBIT_TO_INTEREST_EXPENSE",  # 利息保障倍数
        "debt_service_coverage": "DEBT_SERVICE_COVERAGE",  # 偿债覆盖率
        
        # 运营效率
        "asset_turnover": "ASSET_TURNOVER",  # 资产周转率
        "inventory_turnover": "INVENTORY_TURNOVER",  # 存货周转率
        "receivables_turnover": "RECEIVABLE_TURNOVER",  # 应收账款周转率
        "working_capital_turnover": "WC_TURNOVER",  # 营运资金周转率
        "cash_conversion_cycle": "CASH_CONVERSION_CYCLE",  # 现金转换周期
        
        # ===== 技术面因子 (Technical Factors) =====
        "beta_1y": "BETA_1YR",  # 1年Beta
        "beta_2y": "BETA_2YR",  # 2年Beta
        "beta_adj": "BETA_ADJ_OVERWEIGHT",  # 调整Beta
        "volatility_30d": "VOLATILITY_30D",  # 30天波动率
        "volatility_90d": "VOLATILITY_90D",  # 90天波动率
        "volatility_1y": "VOLATILITY_260D",  # 1年波动率
        "historical_volatility": "HIST_VOLATILITY",  # 历史波动率
        
        # 动量因子
        "momentum_1m": "TOT_RETURN_INDEX_1M",  # 1个月动量
        "momentum_3m": "TOT_RETURN_INDEX_3M",  # 3个月动量
        "momentum_6m": "TOT_RETURN_INDEX_6M",  # 6个月动量
        "momentum_12m": "TOT_RETURN_INDEX_12M",  # 12个月动量
        "price_momentum": "PRICE_MOMENTUM",  # 价格动量
        "earnings_momentum": "EARNINGS_MOMENTUM",  # 盈利动量
        
        # 反转因子
        "short_term_reversal": "ST_REVERSAL",  # 短期反转
        "long_term_reversal": "LT_REVERSAL",  # 长期反转
        
        # 相对强度
        "relative_strength": "RELATIVE_STRENGTH",  # 相对强度
        "rs_rating": "RS_RATING",  # 相对强度评级
        
        # ===== 风险因子 (Risk Factors) =====
        "value_at_risk_1d": "VAR_1D_95",  # 1天95% VaR
        "value_at_risk_10d": "VAR_10D_95",  # 10天95% VaR
        "expected_shortfall": "ES_1D_95",  # 预期损失
        "maximum_drawdown": "MAX_DRAWDOWN",  # 最大回撤
        "downside_volatility": "DOWNSIDE_VOLATILITY",  # 下行波动率
        "upside_volatility": "UPSIDE_VOLATILITY",  # 上行波动率
        "downside_beta": "DOWNSIDE_BETA",  # 下行Beta
        "upside_beta": "UPSIDE_BETA",  # 上行Beta
        
        # 风险调整收益
        "sharpe_ratio": "SHARPE_RATIO",  # 夏普比率
        "treynor_ratio": "TREYNOR_RATIO",  # 特雷诺比率
        "information_ratio": "INFORMATION_RATIO",  # 信息比率
        "sortino_ratio": "SORTINO_RATIO",  # 索提诺比率
        "calmar_ratio": "CALMAR_RATIO",  # 卡尔玛比率
        
        # ===== 分析师因子 (Analyst Factors) =====
        "analyst_rating": "ANALYST_RATING",  # 分析师评级
        "analyst_target_price": "ANALYST_TARGET_PRICE",  # 分析师目标价
        "price_target_upside": "PX_TGT_UPSIDE",  # 目标价上涨空间
        "earnings_revision": "EARNINGS_REVISION",  # 盈利预测修正
        "recommendation_change": "REC_CHANGE",  # 评级变化
        "consensus_eps": "CONSENSUS_EPS",  # 一致预期EPS
        "eps_surprise": "EPS_SURPRISE",  # EPS意外
        "revenue_surprise": "REV_SURPRISE",  # 营收意外
        
        # ===== 流动性因子 (Liquidity Factors) =====
        "trading_volume": "VOLUME",  # 交易量
        "dollar_volume": "DOLLAR_VOLUME",  # 美元交易量
        "volume_ratio": "VOLUME_RATIO",  # 成交量比率
        "turnover_ratio": "TURNOVER_RATIO",  # 换手率
        "bid_ask_spread": "BID_ASK_SPREAD",  # 买卖价差
        "market_impact": "MARKET_IMPACT",  # 市场冲击
        "liquidity_ratio": "LIQUIDITY_RATIO",  # 流动性比率
        "amihud_illiquidity": "AMIHUD_ILLIQ",  # Amihud非流动性指标
        
        # ===== 市场微观结构因子 =====
        "order_flow": "ORDER_FLOW",  # 订单流
        "order_imbalance": "ORDER_IMBALANCE",  # 订单不平衡
        "trade_size": "AVERAGE_TRADE_SIZE",  # 平均交易规模
        "price_impact": "PRICE_IMPACT",  # 价格冲击
        "market_depth": "MARKET_DEPTH",  # 市场深度
        
        # ===== ESG因子 (ESG Factors) =====
        "esg_score": "ESG_DISCLOSURE_SCORE",  # ESG评分
        "environmental_score": "ENVIRON_DISCLOSURE_SCORE",  # 环境评分
        "social_score": "SOCIAL_DISCLOSURE_SCORE",  # 社会责任评分
        "governance_score": "GOVNCE_DISCLOSURE_SCORE",  # 治理评分
        "carbon_emissions": "CARBON_EMISSIONS",  # 碳排放
        "water_usage": "WATER_USAGE",  # 水资源使用
        "waste_production": "WASTE_PRODUCTION",  # 废料产生
        "board_diversity": "BOARD_DIVERSITY",  # 董事会多样性
        
        # ===== 另类数据因子 =====
        "news_sentiment": "NEWS_SENTIMENT",  # 新闻情绪
        "social_sentiment": "SOCIAL_SENTIMENT",  # 社交媒体情绪
        "search_volume": "SEARCH_VOLUME",  # 搜索量
        "satellite_data": "SATELLITE_ACTIVITY",  # 卫星数据
        "patent_count": "PATENT_COUNT",  # 专利数量
        "insider_trading": "INSIDER_TRADING",  # 内部交易
        
        # ===== 期权因子 (Options Factors) =====
        "implied_volatility": "IMPLIED_VOLATILITY",  # 隐含波动率
        "option_volume": "OPTION_VOLUME",  # 期权成交量
        "put_call_ratio": "PUT_CALL_RATIO",  # 认沽认购比
        "option_skew": "OPTION_SKEW",  # 期权偏斜
        "volatility_surface": "VOL_SURFACE",  # 波动率曲面
        "delta_hedged_gains": "DELTA_HEDGED_GAINS",  # Delta对冲收益
        
        # ===== 宏观敏感性因子 =====
        "interest_rate_sensitivity": "DURATION",  # 利率敏感性
        "currency_exposure": "CURRENCY_EXPOSURE",  # 汇率暴露
        "commodity_exposure": "COMMODITY_EXPOSURE",  # 大宗商品暴露
        "inflation_sensitivity": "INFLATION_BETA",  # 通胀敏感性
        "economic_sensitivity": "ECONOMIC_BETA",  # 经济敏感性
        
        # ===== 行业和风格因子 =====
        "sector_momentum": "SECTOR_MOMENTUM",  # 行业动量
        "industry_relative": "INDUSTRY_REL_RETURN",  # 行业相对收益
        "size_factor": "SIZE_FACTOR",  # 规模因子
        "value_factor": "VALUE_FACTOR",  # 价值因子
        "growth_factor": "GROWTH_FACTOR",  # 成长因子
        "quality_factor": "QUALITY_FACTOR",  # 质量因子
        "momentum_factor": "MOMENTUM_FACTOR",  # 动量因子
        "volatility_factor": "VOLATILITY_FACTOR",  # 波动率因子
        
        # ===== 复合因子和评分 =====
        "fundamental_score": "FundamentalScore([roe, pe_ratio, debt_to_equity, revenue_growth_1y])",
        "technical_score": "TechnicalScore([momentum_3m, volatility_30d, beta_1y, relative_strength])",
        "risk_score": "RiskScore([value_at_risk_1d, maximum_drawdown, sharpe_ratio, beta_1y])",
        "analyst_score": "AnalystScore([analyst_rating, price_target_upside, earnings_revision])",
        "liquidity_score": "LiquidityScore([turnover_ratio, bid_ask_spread, market_impact])",
        "esg_composite": "ESGComposite([esg_score, carbon_emissions, board_diversity])",
        "bloomberg_composite": "BloombergComposite([fundamental_score, technical_score, risk_score, analyst_score])"
    }
    
    # 因子分类定义
    CATEGORIES = {
        # 核心Bloomberg因子
        "bloomberg_core": [
            "pe_ratio", "roe", "momentum_3m", "volatility_30d", "analyst_rating", 
            "esg_score", "beta_1y", "sharpe_ratio"
        ],
        
        # 基本面分析
        "fundamental": [
            "pe_ratio", "pb_ratio", "ps_ratio", "pcf_ratio", "ev_ebitda", "ev_sales",
            "roe", "roa", "roic", "gross_margin", "operating_margin", "net_margin"
        ],
        
        # 估值指标
        "valuation": [
            "pe_ratio", "pb_ratio", "ps_ratio", "pcf_ratio", "ev_ebitda", "ev_sales",
            "price_to_tangible_book"
        ],
        
        # 盈利能力
        "profitability": [
            "roe", "roa", "roic", "gross_margin", "operating_margin", 
            "net_margin", "ebitda_margin"
        ],
        
        # 成长性
        "growth": [
            "revenue_growth_1y", "revenue_growth_3y", "earnings_growth_1y", 
            "earnings_growth_3y", "book_value_growth", "dividend_growth"
        ],
        
        # 财务健康
        "financial_health": [
            "debt_to_equity", "debt_to_assets", "current_ratio", "quick_ratio",
            "cash_ratio", "interest_coverage", "debt_service_coverage"
        ],
        
        # 运营效率
        "efficiency": [
            "asset_turnover", "inventory_turnover", "receivables_turnover",
            "working_capital_turnover", "cash_conversion_cycle"
        ],
        
        # 技术分析
        "technical": [
            "beta_1y", "volatility_30d", "momentum_1m", "momentum_3m", "momentum_6m",
            "momentum_12m", "relative_strength", "short_term_reversal"
        ],
        
        # 风险指标
        "risk": [
            "beta_1y", "volatility_1y", "value_at_risk_1d", "maximum_drawdown",
            "downside_volatility", "downside_beta"
        ],
        
        # 风险调整收益
        "risk_adjusted": [
            "sharpe_ratio", "treynor_ratio", "information_ratio", 
            "sortino_ratio", "calmar_ratio"
        ],
        
        # 分析师研究
        "analyst": [
            "analyst_rating", "analyst_target_price", "price_target_upside",
            "earnings_revision", "consensus_eps", "eps_surprise", "revenue_surprise"
        ],
        
        # 流动性
        "liquidity": [
            "trading_volume", "dollar_volume", "turnover_ratio", "bid_ask_spread",
            "market_impact", "liquidity_ratio", "amihud_illiquidity"
        ],
        
        # 市场微观结构
        "microstructure": [
            "order_flow", "order_imbalance", "trade_size", "price_impact", "market_depth"
        ],
        
        # ESG可持续性
        "esg": [
            "esg_score", "environmental_score", "social_score", "governance_score",
            "carbon_emissions", "water_usage", "board_diversity"
        ],
        
        # 另类数据
        "alternative_data": [
            "news_sentiment", "social_sentiment", "search_volume", 
            "satellite_data", "patent_count", "insider_trading"
        ],
        
        # 期权衍生
        "options": [
            "implied_volatility", "option_volume", "put_call_ratio", 
            "option_skew", "volatility_surface", "delta_hedged_gains"
        ],
        
        # 宏观敏感性
        "macro_sensitivity": [
            "interest_rate_sensitivity", "currency_exposure", "commodity_exposure",
            "inflation_sensitivity", "economic_sensitivity"
        ],
        
        # 行业和风格
        "sector_style": [
            "sector_momentum", "industry_relative", "size_factor", "value_factor",
            "growth_factor", "quality_factor", "momentum_factor", "volatility_factor"
        ],
        
        # 复合评分
        "composite_scores": [
            "fundamental_score", "technical_score", "risk_score", "analyst_score",
            "liquidity_score", "esg_composite", "bloomberg_composite"
        ],
        
        # 短期因子
        "short_term": [
            "momentum_1m", "volatility_30d", "short_term_reversal", "order_flow",
            "news_sentiment", "option_volume"
        ],
        
        # 中期因子
        "medium_term": [
            "momentum_3m", "momentum_6m", "volatility_90d", "earnings_revision",
            "relative_strength"
        ],
        
        # 长期因子
        "long_term": [
            "momentum_12m", "beta_1y", "volatility_1y", "revenue_growth_3y",
            "long_term_reversal", "esg_score"
        ],
        
        # 机构投资者关注
        "institutional": [
            "beta_1y", "sharpe_ratio", "tracking_error", "information_ratio",
            "analyst_rating", "esg_score", "liquidity_ratio"
        ],
        
        # 量化因子
        "quantitative": [
            "momentum_factor", "value_factor", "quality_factor", "volatility_factor",
            "beta_1y", "amihud_illiquidity", "relative_strength"
        ]
    }