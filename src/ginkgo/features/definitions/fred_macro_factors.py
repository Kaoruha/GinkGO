# Upstream: External Applications
# Downstream: Trading Strategies, Analysis Tools
# Role: Fred Macro Factors因子定义继承FactorBase提供FredMacroFactors FRED宏观计算






"""
FRED宏观经济因子库 - 配置式定义

美联储经济数据库(FRED)的宏观经济指标和因子，
涵盖货币政策、经济增长、通胀、就业、金融市场等各个维度。

数据来源: Federal Reserve Economic Data (FRED) - https://fred.stlouisfed.org/
"""

from ginkgo.features.definitions.base import BaseDefinition


class FREDMacroFactors(BaseDefinition):
    """FRED宏观经济因子库 - 美联储官方宏观数据"""
    
    NAME = "FRED Macro Factors"
    DESCRIPTION = "美联储经济数据库(FRED)的宏观经济因子，包含货币政策、经济增长、通胀、就业等官方指标"
    
    # FRED宏观因子表达式定义
    EXPRESSIONS = {
        # ===== 货币政策因子 =====
        "fed_funds_rate": "FEDFUNDS",  # 联邦基金利率
        "discount_rate": "DISCOUNT",  # 贴现率
        "real_fed_funds": "Subtract(FEDFUNDS, CPILFESL_YOY)",  # 实际联邦基金利率
        "yield_curve_10y2y": "Subtract(GS10, GS2)",  # 10年-2年期限利差
        "yield_curve_10y3m": "Subtract(GS10, GS3M)",  # 10年-3个月期限利差
        "yield_curve_slope": "LinearRegression([GS3M, GS6M, GS1, GS2, GS5, GS10]).slope",  # 收益率曲线斜率
        "term_spread": "Subtract(GS10, GS3M)",  # 期限溢价
        "credit_spread": "Subtract(BAA, AAA)",  # 信用利差(BAA-AAA)
        "high_yield_spread": "Subtract(BAMLH0A0HYM2, GS10)",  # 高收益债利差
        "monetary_policy_uncertainty": "MPU_Index",  # 货币政策不确定性指数
        
        # ===== 经济增长因子 =====
        "gdp_growth": "PercentChange(GDP, 4)",  # GDP同比增长率
        "real_gdp_growth": "PercentChange(GDPC1, 4)",  # 实际GDP同比增长率
        "gdp_gap": "HodrickPrescottFilter(GDPC1).gap",  # GDP缺口
        "industrial_production": "PercentChange(INDPRO, 12)",  # 工业生产同比增长
        "capacity_utilization": "TCU",  # 产能利用率
        "capacity_utilization_gap": "Subtract(TCU, RollingMean(TCU, 240))",  # 产能利用率缺口
        "leading_index": "PercentChange(USSLIND, 12)",  # 领先指标
        "coincident_index": "PercentChange(USPHCI, 12)",  # 同步指标
        "recession_probability": "RECPROUSM156N",  # 衰退概率
        "economic_surprise_index": "ESI_US",  # 经济意外指数
        
        # ===== 通胀因子 =====
        "cpi_inflation": "PercentChange(CPIAUCSL, 12)",  # CPI同比通胀率
        "core_cpi_inflation": "PercentChange(CPILFESL, 12)",  # 核心CPI通胀率
        "pce_inflation": "PercentChange(PCEPI, 12)",  # PCE通胀率
        "core_pce_inflation": "PercentChange(PCEPILFE, 12)",  # 核心PCE通胀率
        "inflation_expectations_5y": "T5YIE",  # 5年通胀预期
        "inflation_expectations_10y": "T10YIE",  # 10年通胀预期
        "breakeven_5y": "T5YIE",  # 5年盈亏平衡通胀率
        "breakeven_10y": "T10YIE",  # 10年盈亏平衡通胀率
        "inflation_surprise": "Subtract(cpi_inflation, inflation_expectations_5y)",  # 通胀意外
        "wage_inflation": "PercentChange(CES0500000003, 12)",  # 平均时薪增长率
        "import_price_inflation": "PercentChange(IR, 12)",  # 进口价格通胀
        
        # ===== 就业因子 =====
        "unemployment_rate": "UNRATE",  # 失业率
        "unemployment_gap": "Subtract(UNRATE, NROU)",  # 失业率缺口
        "employment_growth": "PercentChange(PAYEMS, 12)",  # 非农就业增长
        "labor_force_participation": "CIVPART",  # 劳动参与率
        "jobless_claims": "ICSA",  # 初次申请失业救济人数
        "continuing_claims": "CCSA",  # 持续申请失业救济人数
        "job_openings": "JTSJOL",  # 职位空缺数
        "quit_rate": "JTSQUR",  # 辞职率
        "hiring_rate": "JTSHIR",  # 招聘率
        "jolts_ratio": "Divide(JTSJOL, UNRATE)",  # 职位空缺与失业率比率
        
        # ===== 金融市场因子 =====
        "vix": "VIXCLS",  # VIX恐慌指数
        "ted_spread": "Subtract(DGS3MO, FEDFUNDS)",  # TED利差
        "financial_stress": "STLFSI",  # 金融压力指数
        "market_liquidity": "ML_Index",  # 市场流动性指数
        "credit_conditions": "DRTSCLCC",  # 信贷条件指数
        "bank_lending_standards": "DRBLACBS",  # 银行放贷标准
        "mortgage_rate": "MORTGAGE30US",  # 30年固定抵押贷款利率
        "corporate_bond_spread": "Subtract(BAMLC0A0CM, GS10)",  # 公司债利差
        "dollar_index": "DTWEXBGS",  # 美元指数
        "gold_price": "GOLDAMGBD228NLBM",  # 黄金价格
        
        # ===== 房地产因子 =====
        "house_price_index": "PercentChange(CSUSHPISA, 12)",  # 房价指数增长
        "housing_starts": "PercentChange(HOUST, 12)",  # 新屋开工增长
        "building_permits": "PercentChange(PERMIT, 12)",  # 建筑许可增长
        "existing_home_sales": "PercentChange(EXHOSLUSM495S, 12)",  # 成屋销售增长
        "mortgage_applications": "MBA_Index",  # 抵押贷款申请指数
        "home_affordability": "HA_Index",  # 住房负担能力指数
        
        # ===== 消费者因子 =====
        "consumer_confidence": "CSCICP03USM665S",  # 消费者信心指数
        "consumer_sentiment": "UMCSENT",  # 密歇根消费者情绪指数
        "retail_sales": "PercentChange(RSAFS, 12)",  # 零售销售增长
        "personal_income": "PercentChange(PI, 12)",  # 个人收入增长
        "personal_spending": "PercentChange(PCE, 12)",  # 个人消费支出增长
        "savings_rate": "PSAVERT",  # 个人储蓄率
        "consumer_credit": "PercentChange(TOTALSL, 12)",  # 消费者信贷增长
        
        # ===== 企业因子 =====
        "business_confidence": "BSCICP03USM665S",  # 企业信心指数
        "capital_expenditure": "PercentChange(PNFI, 4)",  # 资本支出增长
        "corporate_profits": "PercentChange(CP, 4)",  # 企业利润增长
        "profit_margins": "Divide(CP, GDP)",  # 利润率
        "business_inventories": "PercentChange(BUSINV, 12)",  # 企业库存增长
        "capacity_expansion": "PercentChange(CAPUTLB50001SQ, 4)",  # 产能扩张
        
        # ===== 政府财政因子 =====
        "government_debt_gdp": "Divide(GFDEGDQ188S, 100)",  # 政府债务占GDP比率
        "budget_deficit_gdp": "Divide(FYFSGDA188S, GDP)",  # 财政赤字占GDP比率
        "government_spending": "PercentChange(FGEXPND, 4)",  # 政府支出增长
        "tax_receipts": "PercentChange(FGRECPT, 4)",  # 税收收入增长
        
        # ===== 国际贸易因子 =====
        "trade_balance": "BOPGSTB",  # 贸易余额
        "exports": "PercentChange(EXPGS, 12)",  # 出口增长
        "imports": "PercentChange(IMPGS, 12)",  # 进口增长
        "current_account": "BOPBCAGDPNOSB",  # 经常账户占GDP比率
        
        # ===== 能源和商品因子 =====
        "oil_price": "PercentChange(DCOILWTICO, 12)",  # 原油价格增长
        "commodity_index": "PercentChange(PPIACO, 12)",  # 商品价格指数增长
        "energy_prices": "PercentChange(PPIFCG, 12)",  # 能源价格增长
        
        # ===== 人口和社会因子 =====
        "population_growth": "PercentChange(POPTHM, 12)",  # 人口增长率
        "productivity": "PercentChange(OPHNFB, 4)",  # 劳动生产率增长
        "income_inequality": "GINI_Index",  # 基尼系数
        
        # ===== 政策不确定性因子 =====
        "economic_policy_uncertainty": "USEPUINDXD",  # 经济政策不确定性指数
        "trade_policy_uncertainty": "TPU_Index",  # 贸易政策不确定性
        "fiscal_policy_uncertainty": "FPU_Index",  # 财政政策不确定性
        
        # ===== 复合宏观因子 =====
        "macro_surprise_index": "MacroSurpriseIndex([gdp_growth, cpi_inflation, unemployment_rate, fed_funds_rate])",
        "financial_conditions_index": "FinancialConditionsIndex([fed_funds_rate, credit_spread, vix, dollar_index])",
        "leading_macro_factor": "PrincipalComponent([leading_index, yield_curve_10y2y, credit_spread, consumer_confidence])",
        "recession_risk_model": "RecessionModel([yield_curve_10y3m, fed_funds_rate, unemployment_rate, leading_index])",
    }
    
    # 因子分类定义
    CATEGORIES = {
        # 核心宏观因子
        "core_macro": [
            "gdp_growth", "cpi_inflation", "unemployment_rate", "fed_funds_rate"
        ],
        
        # 货币政策
        "monetary_policy": [
            "fed_funds_rate", "discount_rate", "real_fed_funds", "yield_curve_10y2y", 
            "yield_curve_10y3m", "term_spread", "monetary_policy_uncertainty"
        ],
        
        # 利率和债券
        "interest_rates": [
            "fed_funds_rate", "yield_curve_10y2y", "yield_curve_slope", "term_spread",
            "credit_spread", "high_yield_spread", "mortgage_rate"
        ],
        
        # 经济增长
        "growth": [
            "gdp_growth", "real_gdp_growth", "gdp_gap", "industrial_production",
            "capacity_utilization", "leading_index", "coincident_index"
        ],
        
        # 通胀
        "inflation": [
            "cpi_inflation", "core_cpi_inflation", "pce_inflation", "core_pce_inflation",
            "inflation_expectations_5y", "inflation_expectations_10y", "wage_inflation"
        ],
        
        # 就业市场
        "employment": [
            "unemployment_rate", "unemployment_gap", "employment_growth",
            "labor_force_participation", "jobless_claims", "job_openings"
        ],
        
        # 金融市场
        "financial_markets": [
            "vix", "ted_spread", "financial_stress", "credit_conditions",
            "corporate_bond_spread", "dollar_index", "gold_price"
        ],
        
        # 房地产
        "real_estate": [
            "house_price_index", "housing_starts", "building_permits",
            "existing_home_sales", "home_affordability"
        ],
        
        # 消费者
        "consumer": [
            "consumer_confidence", "consumer_sentiment", "retail_sales",
            "personal_income", "personal_spending", "savings_rate"
        ],
        
        # 企业
        "business": [
            "business_confidence", "capital_expenditure", "corporate_profits",
            "profit_margins", "business_inventories"
        ],
        
        # 政府财政
        "fiscal": [
            "government_debt_gdp", "budget_deficit_gdp", "government_spending", "tax_receipts"
        ],
        
        # 国际贸易
        "trade": [
            "trade_balance", "exports", "imports", "current_account"
        ],
        
        # 商品和能源
        "commodities": [
            "oil_price", "commodity_index", "energy_prices", "gold_price"
        ],
        
        # 政策不确定性
        "policy_uncertainty": [
            "economic_policy_uncertainty", "trade_policy_uncertainty", 
            "fiscal_policy_uncertainty", "monetary_policy_uncertainty"
        ],
        
        # 先行指标
        "leading_indicators": [
            "yield_curve_10y2y", "leading_index", "jobless_claims", 
            "building_permits", "consumer_confidence"
        ],
        
        # 滞后指标
        "lagging_indicators": [
            "unemployment_rate", "corporate_profits", "consumer_credit", "prime_rate"
        ],
        
        # 同步指标
        "coincident_indicators": [
            "gdp_growth", "industrial_production", "employment_growth", "personal_income"
        ],
        
        # 市场情绪
        "market_sentiment": [
            "vix", "consumer_confidence", "business_confidence", "financial_stress"
        ],
        
        # 流动性指标
        "liquidity": [
            "fed_funds_rate", "ted_spread", "credit_conditions", "market_liquidity"
        ],
        
        # 复合因子
        "composite": [
            "macro_surprise_index", "financial_conditions_index", 
            "leading_macro_factor", "recession_risk_model"
        ]
    }