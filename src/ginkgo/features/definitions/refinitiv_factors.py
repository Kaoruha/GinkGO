"""
Refinitiv因子库 - 配置式定义

Refinitiv (原Thomson Reuters)提供的专业金融因子，
涵盖StarMine模型、基本面分析、信用评级、ESG评分等机构级数据。

数据来源: Refinitiv - 专业金融数据和分析解决方案提供商
"""

from .base import BaseDefinition


class RefinitivFactors(BaseDefinition):
    """Refinitiv因子库 - 专业金融数据和分析因子"""
    
    NAME = "Refinitiv Professional Factors"
    DESCRIPTION = "Refinitiv专业因子库，包含StarMine模型、基本面分析、信用评级、ESG等机构级因子"
    
    # Refinitiv因子表达式定义
    EXPRESSIONS = {
        # ===== StarMine模型因子 =====
        "starmine_arm": "STARMINE_ARM",  # StarMine分析师修正模型
        "starmine_si": "STARMINE_SI",  # StarMine结构信用指标
        "starmine_pct": "STARMINE_PCT",  # StarMine价格目标准确性
        "starmine_afr": "STARMINE_AFR",  # StarMine分析师预测修正
        "starmine_relval": "STARMINE_RELVAL",  # StarMine相对估值
        "starmine_creditrisk": "STARMINE_CREDIT",  # StarMine信用风险
        "starmine_esg": "STARMINE_ESG",  # StarMine ESG评分
        "starmine_smartest": "STARMINE_SMARTEST",  # StarMine最聪明金钱
        
        # ===== 基本面因子 =====
        # 估值指标
        "pe_ratio_current": "TR_PE_RATIO",  # 当前市盈率
        "pe_ratio_forward": "TR_PE_FWD",  # 前瞻市盈率
        "peg_ratio": "TR_PEG_RATIO",  # PEG比率
        "pb_ratio_current": "TR_PB_RATIO",  # 市净率
        "ps_ratio_current": "TR_PS_RATIO",  # 市销率
        "pcf_ratio_current": "TR_PCF_RATIO",  # 市现率
        "ev_ebitda_current": "TR_EV_EBITDA",  # 企业价值/EBITDA
        "ev_sales_current": "TR_EV_SALES",  # 企业价值/销售额
        "dividend_yield": "TR_DVD_YLD",  # 股息收益率
        "fcf_yield": "TR_FCF_YIELD",  # 自由现金流收益率
        
        # 盈利能力
        "roe_trailing": "TR_ROE_TTM",  # 净资产收益率(TTM)
        "roa_trailing": "TR_ROA_TTM",  # 总资产收益率(TTM)
        "roic_trailing": "TR_ROIC_TTM",  # 投入资本回报率(TTM)
        "gross_margin_ttm": "TR_GROSS_MARGIN_TTM",  # 毛利率(TTM)
        "operating_margin_ttm": "TR_OPER_MARGIN_TTM",  # 营业利润率(TTM)
        "net_margin_ttm": "TR_NET_MARGIN_TTM",  # 净利润率(TTM)
        "ebitda_margin_ttm": "TR_EBITDA_MARGIN_TTM",  # EBITDA利润率(TTM)
        
        # 成长性
        "revenue_growth_1y": "TR_REV_GROWTH_1Y",  # 营收增长率(1年)
        "revenue_growth_3y": "TR_REV_GROWTH_3Y",  # 营收增长率(3年)
        "revenue_growth_5y": "TR_REV_GROWTH_5Y",  # 营收增长率(5年)
        "earnings_growth_1y": "TR_EPS_GROWTH_1Y",  # 盈利增长率(1年)
        "earnings_growth_3y": "TR_EPS_GROWTH_3Y",  # 盈利增长率(3年)
        "earnings_growth_5y": "TR_EPS_GROWTH_5Y",  # 盈利增长率(5年)
        "book_value_growth": "TR_BV_GROWTH",  # 账面价值增长率
        "dividend_growth": "TR_DVD_GROWTH",  # 股息增长率
        
        # 财务质量
        "debt_to_equity": "TR_DEBT_EQUITY",  # 债务股本比
        "debt_to_capital": "TR_DEBT_CAPITAL",  # 债务资本比
        "debt_to_assets": "TR_DEBT_ASSETS",  # 债务资产比
        "current_ratio": "TR_CURRENT_RATIO",  # 流动比率
        "quick_ratio": "TR_QUICK_RATIO",  # 速动比率
        "cash_ratio": "TR_CASH_RATIO",  # 现金比率
        "interest_coverage": "TR_INT_COVERAGE",  # 利息保障倍数
        "altman_z_score": "TR_ALTMAN_Z",  # Altman Z评分
        "piotroski_f_score": "TR_PIOTROSKI_F",  # Piotroski F评分
        
        # 运营效率
        "asset_turnover": "TR_ASSET_TURNOVER",  # 资产周转率
        "inventory_turnover": "TR_INV_TURNOVER",  # 存货周转率
        "receivables_turnover": "TR_REC_TURNOVER",  # 应收账款周转率
        "payables_turnover": "TR_PAY_TURNOVER",  # 应付账款周转率
        "working_capital_turnover": "TR_WC_TURNOVER",  # 营运资金周转率
        "cash_conversion_cycle": "TR_CCC",  # 现金转换周期
        
        # ===== 分析师因子 =====
        "analyst_rating_mean": "TR_ANALYST_RATING",  # 分析师平均评级
        "analyst_count": "TR_ANALYST_COUNT",  # 分析师覆盖数量
        "target_price_mean": "TR_TARGET_PRICE",  # 平均目标价
        "target_price_high": "TR_TARGET_HIGH",  # 最高目标价
        "target_price_low": "TR_TARGET_LOW",  # 最低目标价
        "price_target_return": "TR_PX_TGT_RETURN",  # 目标价回报率
        "eps_estimate_mean": "TR_EPS_EST_MEAN",  # 平均EPS预估
        "eps_estimate_change": "TR_EPS_EST_CHG",  # EPS预估变化
        "recommendation_change": "TR_REC_CHANGE",  # 评级变化
        "estimate_revision": "TR_EST_REVISION",  # 预估修正
        "earnings_surprise": "TR_EPS_SURPRISE",  # 盈利意外
        "revenue_surprise": "TR_REV_SURPRISE",  # 营收意外
        
        # ===== 风险因子 =====
        "beta_5y": "TR_BETA_5Y",  # 5年Beta
        "beta_3y": "TR_BETA_3Y",  # 3年Beta
        "beta_1y": "TR_BETA_1Y",  # 1年Beta
        "volatility_1m": "TR_VOL_1M",  # 1个月波动率
        "volatility_3m": "TR_VOL_3M",  # 3个月波动率
        "volatility_1y": "TR_VOL_1Y",  # 1年波动率
        "volatility_3y": "TR_VOL_3Y",  # 3年波动率
        "downside_volatility": "TR_DOWNSIDE_VOL",  # 下行波动率
        "tracking_error": "TR_TRACKING_ERROR",  # 跟踪误差
        "information_ratio": "TR_INFO_RATIO",  # 信息比率
        "sharpe_ratio": "TR_SHARPE",  # 夏普比率
        "sortino_ratio": "TR_SORTINO",  # 索提诺比率
        "maximum_drawdown": "TR_MAX_DRAWDOWN",  # 最大回撤
        "value_at_risk": "TR_VAR_95",  # 风险价值
        
        # ===== 技术面因子 =====
        "momentum_1m": "TR_MOMENTUM_1M",  # 1个月动量
        "momentum_3m": "TR_MOMENTUM_3M",  # 3个月动量
        "momentum_6m": "TR_MOMENTUM_6M",  # 6个月动量
        "momentum_12m": "TR_MOMENTUM_12M",  # 12个月动量
        "relative_strength": "TR_REL_STRENGTH",  # 相对强度
        "price_relative": "TR_PRICE_REL",  # 价格相对表现
        "moving_average_20d": "TR_MA_20D",  # 20日移动平均
        "moving_average_50d": "TR_MA_50D",  # 50日移动平均
        "moving_average_200d": "TR_MA_200D",  # 200日移动平均
        "bollinger_position": "TR_BB_POS",  # 布林带位置
        "rsi_14d": "TR_RSI_14D",  # 14日RSI
        "stochastic_k": "TR_STOCH_K",  # 随机指标K
        "macd_signal": "TR_MACD",  # MACD信号
        
        # ===== 流动性因子 =====
        "trading_volume_avg": "TR_VOLUME_AVG",  # 平均交易量
        "dollar_volume_avg": "TR_DOLLAR_VOL_AVG",  # 平均美元交易量
        "turnover_ratio": "TR_TURNOVER",  # 换手率
        "bid_ask_spread": "TR_BID_ASK",  # 买卖价差
        "market_impact": "TR_MARKET_IMPACT",  # 市场冲击
        "liquidity_ratio": "TR_LIQUIDITY",  # 流动性比率
        "free_float": "TR_FREE_FLOAT",  # 自由流通股比例
        "shares_outstanding": "TR_SHARES_OUT",  # 流通股数
        
        # ===== ESG因子 =====
        "esg_score": "TR_ESG_SCORE",  # ESG综合评分
        "esg_controversies": "TR_ESG_CONTROVERSIES",  # ESG争议评分
        "environmental_score": "TR_ENV_SCORE",  # 环境评分
        "social_score": "TR_SOC_SCORE",  # 社会责任评分
        "governance_score": "TR_GOV_SCORE",  # 公司治理评分
        "carbon_emissions": "TR_CARBON_EMISSIONS",  # 碳排放
        "water_usage": "TR_WATER_USAGE",  # 用水量
        "waste_recycling": "TR_WASTE_RECYCLING",  # 废料回收率
        "energy_efficiency": "TR_ENERGY_EFF",  # 能源效率
        "board_diversity": "TR_BOARD_DIVERSITY",  # 董事会多样性
        "executive_compensation": "TR_EXEC_COMP",  # 高管薪酬合理性
        "shareholder_rights": "TR_SHAREHOLDER_RIGHTS",  # 股东权利
        
        # ===== 信用因子 =====
        "credit_rating": "TR_CREDIT_RATING",  # 信用评级
        "default_probability": "TR_DEFAULT_PROB",  # 违约概率
        "credit_spread": "TR_CREDIT_SPREAD",  # 信用利差
        "cds_spread": "TR_CDS_SPREAD",  # CDS利差
        "distance_to_default": "TR_DISTANCE_DEFAULT",  # 距离违约
        "interest_rate_sensitivity": "TR_DURATION",  # 利率敏感性
        "credit_quality": "TR_CREDIT_QUALITY",  # 信用质量评分
        
        # ===== 行业因子 =====
        "industry_pe": "TR_INDUSTRY_PE",  # 行业市盈率
        "industry_pb": "TR_INDUSTRY_PB",  # 行业市净率
        "industry_momentum": "TR_INDUSTRY_MOM",  # 行业动量
        "industry_relative": "TR_INDUSTRY_REL",  # 行业相对表现
        "sector_allocation": "TR_SECTOR_ALLOC",  # 行业配置权重
        "industry_rotation": "TR_INDUSTRY_ROT",  # 行业轮动信号
        
        # ===== 宏观因子 =====
        "currency_exposure": "TR_CURRENCY_EXP",  # 汇率暴露
        "commodity_exposure": "TR_COMMODITY_EXP",  # 大宗商品暴露
        "interest_rate_exposure": "TR_IR_EXP",  # 利率暴露
        "inflation_sensitivity": "TR_INFLATION_BETA",  # 通胀敏感性
        "economic_sensitivity": "TR_ECONOMIC_BETA",  # 经济敏感性
        "country_risk": "TR_COUNTRY_RISK",  # 国家风险
        
        # ===== 市场微观结构因子 =====
        "order_flow": "TR_ORDER_FLOW",  # 订单流
        "price_impact": "TR_PRICE_IMPACT",  # 价格冲击
        "market_depth": "TR_MARKET_DEPTH",  # 市场深度
        "execution_quality": "TR_EXEC_QUALITY",  # 执行质量
        "trade_size": "TR_TRADE_SIZE",  # 交易规模
        "institutional_ownership": "TR_INST_OWN",  # 机构持股比例
        
        # ===== 复合因子 =====
        "quality_score": "QualityScore([roe_trailing, debt_to_equity, earnings_growth_1y, altman_z_score])",
        "value_score": "ValueScore([pe_ratio_current, pb_ratio_current, pcf_ratio_current, dividend_yield])",
        "growth_score": "GrowthScore([revenue_growth_1y, earnings_growth_1y, eps_estimate_change])",
        "momentum_score": "MomentumScore([momentum_3m, momentum_6m, relative_strength, analyst_rating_mean])",
        "risk_score": "RiskScore([beta_1y, volatility_3m, maximum_drawdown, debt_to_equity])",
        "esg_composite": "ESGComposite([esg_score, environmental_score, social_score, governance_score])",
        "starmine_composite": "StarMineComposite([starmine_arm, starmine_si, starmine_relval, starmine_creditrisk])",
        "refinitiv_alpha": "RefinitivAlpha([quality_score, value_score, momentum_score, esg_composite])"
    }
    
    # 因子分类定义
    CATEGORIES = {
        # Refinitiv核心因子
        "refinitiv_core": [
            "starmine_arm", "pe_ratio_current", "roe_trailing", "momentum_3m",
            "analyst_rating_mean", "esg_score", "beta_1y", "quality_score"
        ],
        
        # StarMine专有模型
        "starmine": [
            "starmine_arm", "starmine_si", "starmine_pct", "starmine_afr",
            "starmine_relval", "starmine_creditrisk", "starmine_esg", "starmine_smartest"
        ],
        
        # 基本面分析
        "fundamental": [
            "pe_ratio_current", "pb_ratio_current", "roe_trailing", "roa_trailing",
            "revenue_growth_1y", "debt_to_equity", "current_ratio", "asset_turnover"
        ],
        
        # 估值指标
        "valuation": [
            "pe_ratio_current", "pe_ratio_forward", "peg_ratio", "pb_ratio_current",
            "ps_ratio_current", "pcf_ratio_current", "ev_ebitda_current", "ev_sales_current"
        ],
        
        # 盈利能力
        "profitability": [
            "roe_trailing", "roa_trailing", "roic_trailing", "gross_margin_ttm",
            "operating_margin_ttm", "net_margin_ttm", "ebitda_margin_ttm"
        ],
        
        # 成长性
        "growth": [
            "revenue_growth_1y", "revenue_growth_3y", "earnings_growth_1y",
            "earnings_growth_3y", "book_value_growth", "dividend_growth"
        ],
        
        # 财务质量
        "quality": [
            "debt_to_equity", "current_ratio", "interest_coverage", 
            "altman_z_score", "piotroski_f_score", "cash_conversion_cycle"
        ],
        
        # 分析师研究
        "analyst": [
            "analyst_rating_mean", "target_price_mean", "price_target_return",
            "eps_estimate_change", "recommendation_change", "earnings_surprise"
        ],
        
        # 风险管理
        "risk": [
            "beta_1y", "volatility_1y", "downside_volatility", "tracking_error",
            "sharpe_ratio", "maximum_drawdown", "value_at_risk"
        ],
        
        # 技术分析
        "technical": [
            "momentum_3m", "momentum_6m", "relative_strength", "moving_average_20d",
            "bollinger_position", "rsi_14d", "macd_signal"
        ],
        
        # 流动性
        "liquidity": [
            "trading_volume_avg", "turnover_ratio", "bid_ask_spread", 
            "market_impact", "free_float", "liquidity_ratio"
        ],
        
        # ESG可持续性
        "esg": [
            "esg_score", "environmental_score", "social_score", "governance_score",
            "carbon_emissions", "board_diversity", "esg_controversies"
        ],
        
        # 信用分析
        "credit": [
            "credit_rating", "default_probability", "credit_spread", "cds_spread",
            "distance_to_default", "credit_quality"
        ],
        
        # 行业分析
        "sector": [
            "industry_pe", "industry_momentum", "industry_relative", 
            "sector_allocation", "industry_rotation"
        ],
        
        # 宏观敏感性
        "macro": [
            "currency_exposure", "commodity_exposure", "interest_rate_exposure",
            "inflation_sensitivity", "economic_sensitivity", "country_risk"
        ],
        
        # 市场微观结构
        "microstructure": [
            "order_flow", "price_impact", "market_depth", "execution_quality",
            "institutional_ownership"
        ],
        
        # 复合评分
        "composite": [
            "quality_score", "value_score", "growth_score", "momentum_score",
            "risk_score", "esg_composite", "starmine_composite", "refinitiv_alpha"
        ],
        
        # 短期因子
        "short_term": [
            "momentum_1m", "volatility_1m", "analyst_rating_mean", "order_flow",
            "price_impact", "earnings_surprise"
        ],
        
        # 中期因子
        "medium_term": [
            "momentum_3m", "momentum_6m", "volatility_3m", "relative_strength",
            "estimate_revision", "beta_1y"
        ],
        
        # 长期因子
        "long_term": [
            "momentum_12m", "revenue_growth_3y", "volatility_3y", "esg_score",
            "credit_rating", "piotroski_f_score"
        ],
        
        # 机构投资者
        "institutional": [
            "starmine_arm", "analyst_rating_mean", "esg_score", "risk_score",
            "institutional_ownership", "liquidity_ratio"
        ],
        
        # 量化投资
        "quantitative": [
            "momentum_score", "quality_score", "value_score", "beta_1y",
            "relative_strength", "volatility_1y"
        ],
        
        # 主动管理
        "active_management": [
            "starmine_arm", "analyst_rating_mean", "target_price_return",
            "earnings_surprise", "recommendation_change", "estimate_revision"
        ]
    }