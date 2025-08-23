"""
中国A股特色因子集合 - 配置式定义

针对中国A股市场特殊性设计的因子，
包含小盘效应、ST效应、新股效应、涨跌停、融资融券、北向资金等A股独有特征。
"""

from .base import BaseDefinition


class ChinaAFactors(BaseDefinition):
    """中国A股特色因子表达式类 - 适配A股市场独特特征"""
    
    NAME = "ChinaA"
    DESCRIPTION = "中国A股市场特色因子集合，包含小盘效应、ST效应、新股效应等A股独有的市场特征因子"
    
    # 中国A股特色因子表达式定义
    EXPRESSIONS = {
        # 小盘效应 - A股最显著特征
        "SMALL_CAP_PREMIUM": "SmallCapPremium($market_cap, $total_market_cap)",   # 小盘股溢价
        "MICRO_CAP_EFFECT": "MicroCapEffect($market_cap, 0.1)",                  # 微盘股效应
        "SIZE_MOMENTUM": "SizeMomentum($market_cap, $momentum)",                 # 规模动量交互
        
        # ST股效应 - 中国特色
        "ST_EFFECT": "STStockEffect($st_status, $delisting_risk)",               # ST股票效应
        "ST_REVERSAL": "STReversalEffect($st_status, $returns)",                 # ST股反转效应
        "DELISTING_RISK": "DelistingRisk($financial_condition, $trading_status)", # 退市风险
        
        # 新股效应
        "IPO_EFFECT": "IPOEffect($days_since_listing)",                          # 新股上市效应
        "IPO_MOMENTUM": "IPOMomentum($days_since_listing, $returns)",            # 新股动量
        "IPO_LOTTERY_EFFECT": "IPOLotteryEffect($ipo_subscription_ratio)",       # 新股中签效应
        "SUB_NEW_EFFECT": "SubNewStockEffect($days_since_listing, 250)",         # 次新股效应
        
        # 停牌复牌效应
        "SUSPENSION_EFFECT": "SuspensionEffect($suspension_days)",               # 停牌效应
        "RESUMPTION_EFFECT": "ResumptionEffect($resumption_announcement)",       # 复牌效应
        "SUSPENSION_FREQUENCY": "SuspensionFrequency($suspension_count, 252)",   # 停牌频率
        
        # 涨跌停效应
        "LIMIT_UP_EFFECT": "LimitUpEffect($limit_up_indicator)",                 # 涨停效应
        "LIMIT_DOWN_EFFECT": "LimitDownEffect($limit_down_indicator)",           # 跌停效应
        "LIMIT_UP_MOMENTUM": "LimitUpMomentum($limit_up_days, 20)",              # 涨停动量
        "CONSECUTIVE_LIMIT_UP": "ConsecutiveLimitUp($limit_up_sequence)",        # 连续涨停
        "LIMIT_UP_OPEN_RATE": "LimitUpOpenRate($open_after_limit_up)",          # 涨停开板率
        
        # 分红除权效应
        "DIVIDEND_EFFECT": "DividendEffect($dividend_announcement)",             # 分红效应
        "EX_DIVIDEND_EFFECT": "ExDividendEffect($ex_dividend_date)",            # 除权除息效应
        "HIGH_DIVIDEND_YIELD": "HighDividendYield($dividend_yield, $market_avg)", # 高股息效应
        "BONUS_SHARE_EFFECT": "BonusShareEffect($bonus_share_ratio)",           # 送股效应
        
        # 机构投资者因子
        "FUND_HOLDING_RATIO": "FundHoldingRatio($fund_shares, $total_shares)",   # 基金持股比例
        "QFII_HOLDING": "QFIIHolding($qfii_shares, $total_shares)",             # QFII持股
        "SOCIAL_SECURITY_HOLDING": "SocialSecurityHolding($social_security_shares)", # 社保持股
        "INSURANCE_HOLDING": "InsuranceHolding($insurance_shares)",              # 保险资金持股
        "FUND_CONCENTRATION": "FundConcentration($top10_fund_ratio)",            # 基金持股集中度
        
        # 北向资金效应
        "NORTHBOUND_NET_BUY": "NorthboundNetBuy($northbound_flow, 20)",          # 北向资金净买入
        "NORTHBOUND_HOLDING_RATIO": "NorthboundHoldingRatio($northbound_shares)", # 北向资金持股比例
        "NORTHBOUND_MOMENTUM": "NorthboundMomentum($northbound_flow, 60)",       # 北向资金动量
        "MSCI_INCLUSION_EFFECT": "MSCIInclusionEffect($msci_inclusion_status)",  # MSCI纳入效应
        "CONNECT_ELIGIBILITY": "ConnectEligibility($connect_status)",            # 港股通标的效应
        
        # 融资融券因子
        "MARGIN_TRADING_RATIO": "MarginTradingRatio($margin_balance, $market_cap)", # 融资融券余额比例
        "MARGIN_BUY_RATIO": "MarginBuyRatio($margin_buy, $total_buy)",           # 融资买入占比
        "SHORT_SELLING_RATIO": "ShortSellingRatio($short_sell, $total_sell)",    # 融券卖出占比
        "MARGIN_DEBT_CHANGE": "MarginDebtChange($margin_balance, 20)",           # 融资余额变化
        "SECURITIES_LENDING": "SecuritiesLending($securities_lending_volume)",    # 券源供给
        
        # 换手率和流动性
        "TURNOVER_VOLATILITY": "TurnoverVolatility($turnover_rate, 60)",         # 换手率波动
        "HIGH_TURNOVER_EFFECT": "HighTurnoverEffect($turnover_rate, $market_avg)", # 高换手率效应
        "LIQUIDITY_SHOCK": "LiquidityShock($volume, $turnover_rate)",           # 流动性冲击
        "BID_ASK_SPREAD": "BidAskSpread($bid_price, $ask_price, $mid_price)",   # 买卖价差
        
        # 概念题材因子
        "HOT_CONCEPT": "HotConceptEffect($concept_heat_score)",                  # 热门概念
        "THEME_ROTATION": "ThemeRotation($theme_performance, 20)",               # 题材轮动
        "EVENT_DRIVEN": "EventDriven($corporate_events, $abnormal_returns)",     # 事件驱动
        "POLICY_SENSITIVITY": "PolicySensitivity($policy_announcement, $returns)", # 政策敏感性
        
        # 大股东行为
        "MAJOR_SHAREHOLDER_REDUCTION": "MajorShareholderReduction($reduction_announcement)", # 大股东减持
        "SHARE_BUYBACK": "ShareBuyback($buyback_announcement)",                 # 股份回购
        "CONTROLLING_SHAREHOLDER_PLEDGE": "ControllingShareholderPledge($pledge_ratio)", # 控股股东质押
        "INSIDER_TRADING": "InsiderTrading($insider_transactions)",             # 内幕交易
        
        # 信息披露质量
        "DISCLOSURE_QUALITY": "DisclosureQuality($disclosure_score)",           # 信息披露质量
        "EARNINGS_ANNOUNCEMENT_EFFECT": "EarningsAnnouncementEffect($earnings_surprise)", # 业绩预告效应
        "AUDIT_OPINION": "AuditOpinion($audit_opinion_type)",                   # 审计意见
        "ACCOUNTING_QUALITY": "AccountingQuality($accruals, $cash_flow)",       # 会计质量
        
        # 市场情绪因子
        "RETAIL_SENTIMENT": "RetailSentiment($retail_trading_volume)",          # 散户情绪
        "MARGIN_SENTIMENT": "MarginSentiment($margin_balance, $market_sentiment)", # 融资情绪
        "NEW_ACCOUNT_OPENING": "NewAccountOpening($new_accounts, $market_cap)",  # 新开户数
        "SEARCH_VOLUME": "SearchVolume($baidu_search_index)",                   # 搜索热度
        
        # 行业轮动因子
        "INDUSTRY_MOMENTUM": "IndustryMomentum($industry_returns, 20)",         # 行业动量
        "SECTOR_ROTATION": "SectorRotation($sector_performance, 60)",           # 板块轮动
        "CYCLICAL_VS_DEFENSIVE": "CyclicalVsDefensive($cyclical_sectors, $defensive_sectors)", # 周期vs防御
        "VALUE_VS_GROWTH_STYLE": "ValueVsGrowthStyle($value_stocks, $growth_stocks)", # 价值vs成长风格
        
        # 特殊日期效应
        "MONTH_END_EFFECT": "MonthEndEffect($month_end_indicator)",              # 月末效应
        "QUARTER_END_EFFECT": "QuarterEndEffect($quarter_end_indicator)",       # 季末效应
        "YEAR_END_EFFECT": "YearEndEffect($year_end_indicator)",                # 年末效应
        "HOLIDAY_EFFECT": "HolidayEffect($holiday_indicator)",                  # 节假日效应
        "LUNAR_CALENDAR_EFFECT": "LunarCalendarEffect($lunar_date)",            # 农历效应
    }
    
    # 因子分类定义
    CATEGORIES = {
        # A股核心特色因子
        "a_share_core": ["SMALL_CAP_PREMIUM", "ST_EFFECT", "IPO_EFFECT", "LIMIT_UP_EFFECT", 
                        "NORTHBOUND_NET_BUY", "MARGIN_TRADING_RATIO"],
        
        # 规模效应
        "size_effects": ["SMALL_CAP_PREMIUM", "MICRO_CAP_EFFECT", "SIZE_MOMENTUM"],
        
        # 特殊股票类型
        "special_stocks": ["ST_EFFECT", "ST_REVERSAL", "DELISTING_RISK"],
        
        # 新股相关
        "ipo_effects": ["IPO_EFFECT", "IPO_MOMENTUM", "IPO_LOTTERY_EFFECT", "SUB_NEW_EFFECT"],
        
        # 交易机制相关
        "trading_mechanism": ["SUSPENSION_EFFECT", "RESUMPTION_EFFECT", "LIMIT_UP_EFFECT", 
                             "LIMIT_DOWN_EFFECT", "CONSECUTIVE_LIMIT_UP"],
        
        # 公司行为
        "corporate_actions": ["DIVIDEND_EFFECT", "EX_DIVIDEND_EFFECT", "BONUS_SHARE_EFFECT", 
                             "SHARE_BUYBACK", "MAJOR_SHAREHOLDER_REDUCTION"],
        
        # 机构投资者
        "institutional": ["FUND_HOLDING_RATIO", "QFII_HOLDING", "SOCIAL_SECURITY_HOLDING", 
                         "INSURANCE_HOLDING", "FUND_CONCENTRATION"],
        
        # 外资流入
        "foreign_capital": ["NORTHBOUND_NET_BUY", "NORTHBOUND_HOLDING_RATIO", "NORTHBOUND_MOMENTUM",
                           "MSCI_INCLUSION_EFFECT", "CONNECT_ELIGIBILITY"],
        
        # 融资融券
        "margin_trading": ["MARGIN_TRADING_RATIO", "MARGIN_BUY_RATIO", "SHORT_SELLING_RATIO",
                          "MARGIN_DEBT_CHANGE", "SECURITIES_LENDING"],
        
        # 流动性相关
        "liquidity": ["TURNOVER_VOLATILITY", "HIGH_TURNOVER_EFFECT", "LIQUIDITY_SHOCK", "BID_ASK_SPREAD"],
        
        # 市场主题
        "themes": ["HOT_CONCEPT", "THEME_ROTATION", "EVENT_DRIVEN", "POLICY_SENSITIVITY"],
        
        # 信息质量
        "information": ["DISCLOSURE_QUALITY", "EARNINGS_ANNOUNCEMENT_EFFECT", "AUDIT_OPINION", 
                       "ACCOUNTING_QUALITY"],
        
        # 市场情绪
        "sentiment": ["RETAIL_SENTIMENT", "MARGIN_SENTIMENT", "NEW_ACCOUNT_OPENING", "SEARCH_VOLUME"],
        
        # 风格轮动
        "style_rotation": ["INDUSTRY_MOMENTUM", "SECTOR_ROTATION", "CYCLICAL_VS_DEFENSIVE", 
                          "VALUE_VS_GROWTH_STYLE"],
        
        # 日历效应
        "calendar_effects": ["MONTH_END_EFFECT", "QUARTER_END_EFFECT", "YEAR_END_EFFECT", 
                            "HOLIDAY_EFFECT", "LUNAR_CALENDAR_EFFECT"],
        
        # 高频交易相关
        "high_frequency": ["LIMIT_UP_MOMENTUM", "LIMIT_UP_OPEN_RATE", "LIQUIDITY_SHOCK"],
        
        # 政策相关
        "policy_related": ["POLICY_SENSITIVITY", "MSCI_INCLUSION_EFFECT", "CONNECT_ELIGIBILITY"],
        
        # 投资者行为
        "investor_behavior": ["RETAIL_SENTIMENT", "INSIDER_TRADING", "CONTROLLING_SHAREHOLDER_PLEDGE"],
        
        # 核心实战因子 (A股最有效的因子)
        "practical_core": ["SMALL_CAP_PREMIUM", "TURNOVER_VOLATILITY", "NORTHBOUND_NET_BUY",
                          "MARGIN_TRADING_RATIO", "IPO_EFFECT", "LIMIT_UP_MOMENTUM"]
    }