# Upstream: External Applications
# Downstream: Trading Strategies, Analysis Tools
# Role: 定义TA-Lib技术指标计算函数提供SMA/EMA/MACD/RSI/ATR/BBANDS等150+方法






"""
TA-Lib技术指标库 - 配置式定义

Technical Analysis Library (TA-Lib)的150+个技术指标，
涵盖趋势、动量、成交量、波动率、价格形态等各个技术分析维度。

数据来源: TA-Lib官方库 - https://github.com/mrjbq7/ta-lib
"""

from ginkgo.features.definitions.base import BaseDefinition


class TALibIndicators(BaseDefinition):
    """TA-Lib技术指标库 - 工业标准的技术分析指标"""
    
    NAME = "TA-Lib Technical Indicators"
    DESCRIPTION = "TA-Lib官方技术指标库，包含150+个标准化技术分析指标，覆盖趋势、动量、成交量等维度"
    
    # TA-Lib技术指标表达式定义
    EXPRESSIONS = {
        # ===== 重叠研究指标 (Overlap Studies) =====
        "sma_5": "SMA(close, 5)",  # 简单移动平均线
        "sma_10": "SMA(close, 10)",
        "sma_20": "SMA(close, 20)",
        "sma_50": "SMA(close, 50)",
        "sma_200": "SMA(close, 200)",
        
        "ema_5": "EMA(close, 5)",  # 指数移动平均线
        "ema_10": "EMA(close, 10)",
        "ema_20": "EMA(close, 20)",
        "ema_50": "EMA(close, 50)",
        "ema_200": "EMA(close, 200)",
        
        "wma_10": "WMA(close, 10)",  # 加权移动平均线
        "wma_20": "WMA(close, 20)",
        
        "dema_10": "DEMA(close, 10)",  # 双指数移动平均线
        "dema_20": "DEMA(close, 20)",
        
        "tema_10": "TEMA(close, 10)",  # 三指数移动平均线
        "tema_20": "TEMA(close, 20)",
        
        "trima_10": "TRIMA(close, 10)",  # 三角移动平均线
        "trima_20": "TRIMA(close, 20)",
        
        "kama_10": "KAMA(close, 10)",  # 考夫曼自适应移动平均线
        "kama_20": "KAMA(close, 20)",
        
        "mama": "MAMA(close, 0.5, 0.05)",  # MESA自适应移动平均线
        "fama": "FAMA(close, 0.5, 0.05)",  # 跟随自适应移动平均线
        
        "t3_10": "T3(close, 10, 0.7)",  # T3移动平均线
        "t3_20": "T3(close, 20, 0.7)",
        
        # 布林带
        "bb_upper": "BBANDS(close, 20, 2, 2).upper",  # 布林带上轨
        "bb_middle": "BBANDS(close, 20, 2, 2).middle",  # 布林带中轨
        "bb_lower": "BBANDS(close, 20, 2, 2).lower",  # 布林带下轨
        "bb_width": "Subtract(bb_upper, bb_lower)",  # 布林带宽度
        "bb_percent": "Divide(Subtract(close, bb_lower), Subtract(bb_upper, bb_lower))",  # %B
        
        # SAR抛物线
        "sar": "SAR(high, low, 0.02, 0.2)",  # 抛物线SAR
        
        # ===== 动量指标 (Momentum Indicators) =====
        "rsi_14": "RSI(close, 14)",  # 相对强弱指标
        "rsi_21": "RSI(close, 21)",
        "rsi_9": "RSI(close, 9)",
        
        "macd": "MACD(close, 12, 26, 9).macd",  # MACD
        "macd_signal": "MACD(close, 12, 26, 9).macdsignal",  # MACD信号线
        "macd_histogram": "MACD(close, 12, 26, 9).macdhist",  # MACD柱状图
        
        "stoch_k": "STOCH(high, low, close, 14, 3, 0, 3, 0).slowk",  # 随机指标%K
        "stoch_d": "STOCH(high, low, close, 14, 3, 0, 3, 0).slowd",  # 随机指标%D
        
        "stochf_k": "STOCHF(high, low, close, 5, 3, 0).fastk",  # 快速随机指标%K
        "stochf_d": "STOCHF(high, low, close, 5, 3, 0).fastd",  # 快速随机指标%D
        
        "stochrsi_k": "STOCHRSI(close, 14, 5, 3, 0).fastk",  # 随机RSI %K
        "stochrsi_d": "STOCHRSI(close, 14, 5, 3, 0).fastd",  # 随机RSI %D
        
        "cci_14": "CCI(high, low, close, 14)",  # 商品通道指标
        "cci_20": "CCI(high, low, close, 20)",
        
        "cmo_14": "CMO(close, 14)",  # 钱德动量摆动指标
        "cmo_21": "CMO(close, 21)",
        
        "mom_10": "MOM(close, 10)",  # 动量指标
        "mom_20": "MOM(close, 20)",
        
        "roc_10": "ROC(close, 10)",  # 变动率指标
        "roc_20": "ROC(close, 20)",
        
        "rocp_10": "ROCP(close, 10)",  # 价格变动率
        "rocp_20": "ROCP(close, 20)",
        
        "rocr_10": "ROCR(close, 10)",  # 比率变动率
        "rocr_20": "ROCR(close, 20)",
        
        "aroon_up": "AROON(high, low, 14).aroonup",  # Aroon向上
        "aroon_down": "AROON(high, low, 14).aroondown",  # Aroon向下
        "aroon_osc": "AROONOSC(high, low, 14)",  # Aroon振荡器
        
        "bop": "BOP(open, high, low, close)",  # 均势指标
        
        "dx_14": "DX(high, low, close, 14)",  # 方向性指标
        "adx_14": "ADX(high, low, close, 14)",  # 平均方向性指标
        "adxr_14": "ADXR(high, low, close, 14)",  # 平均方向性指标评级
        
        "plus_di_14": "PLUS_DI(high, low, close, 14)",  # +DI
        "minus_di_14": "MINUS_DI(high, low, close, 14)",  # -DI
        "plus_dm_14": "PLUS_DM(high, low, 14)",  # +DM
        "minus_dm_14": "MINUS_DM(high, low, 14)",  # -DM
        
        "apo_12_26": "APO(close, 12, 26, 0)",  # 价格振荡器
        "ppo_12_26": "PPO(close, 12, 26, 0)",  # 百分比价格振荡器
        
        "trix_14": "TRIX(close, 14)",  # 三重指数平滑振荡器
        
        "ultosc": "ULTOSC(high, low, close, 7, 14, 28)",  # 终极振荡器
        
        "willr_14": "WILLR(high, low, close, 14)",  # 威廉指标
        "willr_21": "WILLR(high, low, close, 21)",
        
        # ===== 成交量指标 (Volume Indicators) =====
        "ad": "AD(high, low, close, volume)",  # 累积/派发线
        "adosc": "ADOSC(high, low, close, volume, 3, 10)",  # A/D振荡器
        
        "obv": "OBV(close, volume)",  # 能量潮指标
        
        # ===== 波动率指标 (Volatility Indicators) =====
        "atr_14": "ATR(high, low, close, 14)",  # 真实波动幅度均值
        "atr_20": "ATR(high, low, close, 20)",
        
        "natr_14": "NATR(high, low, close, 14)",  # 标准化真实波动幅度
        "natr_20": "NATR(high, low, close, 20)",
        
        "trange": "TRANGE(high, low, close)",  # 真实范围
        
        # ===== 价格变换 (Price Transform) =====
        "avgprice": "AVGPRICE(open, high, low, close)",  # 平均价格
        "medprice": "MEDPRICE(high, low)",  # 中位价格
        "typprice": "TYPPRICE(high, low, close)",  # 典型价格
        "wclprice": "WCLPRICE(high, low, close)",  # 加权收盘价
        
        # ===== 周期指标 (Cycle Indicators) =====
        "ht_dcperiod": "HT_DCPERIOD(close)",  # 希尔伯特变换-主导周期
        "ht_dcphase": "HT_DCPHASE(close)",  # 希尔伯特变换-主导周期相位
        "ht_phasor_inphase": "HT_PHASOR(close).inphase",  # 希尔伯特变换-向量
        "ht_phasor_quadrature": "HT_PHASOR(close).quadrature",  # 希尔伯特变换-正交
        "ht_sine_sine": "HT_SINE(close).sine",  # 希尔伯特变换-正弦波
        "ht_sine_leadsine": "HT_SINE(close).leadsine",  # 希尔伯特变换-领先正弦波
        "ht_trendmode": "HT_TRENDMODE(close)",  # 希尔伯特变换-趋势模式
        
        # ===== 统计函数 (Statistic Functions) =====
        "beta_20": "BETA(high, low, 20)",  # 贝塔系数
        "correl_20": "CORREL(high, low, 20)",  # 皮尔逊相关系数
        "linearreg_14": "LINEARREG(close, 14)",  # 线性回归
        "linearreg_angle_14": "LINEARREG_ANGLE(close, 14)",  # 线性回归角度
        "linearreg_intercept_14": "LINEARREG_INTERCEPT(close, 14)",  # 线性回归截距
        "linearreg_slope_14": "LINEARREG_SLOPE(close, 14)",  # 线性回归斜率
        "stddev_20": "STDDEV(close, 20, 1)",  # 标准差
        "tsf_14": "TSF(close, 14)",  # 时间序列预测
        "var_20": "VAR(close, 20, 1)",  # 方差
        
        # ===== 数学变换 (Math Transform) =====
        "acos": "ACOS(close)",  # 反余弦
        "asin": "ASIN(close)",  # 反正弦
        "atan": "ATAN(close)",  # 反正切
        "ceil": "CEIL(close)",  # 向上舍入
        "cos": "COS(close)",  # 余弦
        "cosh": "COSH(close)",  # 双曲余弦
        "exp": "EXP(close)",  # 指数
        "floor": "FLOOR(close)",  # 向下舍入
        "ln": "LN(close)",  # 自然对数
        "log10": "LOG10(close)",  # 常用对数
        "sin": "SIN(close)",  # 正弦
        "sinh": "SINH(close)",  # 双曲正弦
        "sqrt": "SQRT(close)",  # 平方根
        "tan": "TAN(close)",  # 正切
        "tanh": "TANH(close)",  # 双曲正切
        
        # ===== 数学运算符 (Math Operators) =====
        "add": "ADD(high, low)",  # 加法
        "div": "DIV(high, low)",  # 除法
        "max_20": "MAX(close, 20)",  # 最大值
        "maxindex_20": "MAXINDEX(close, 20)",  # 最大值索引
        "min_20": "MIN(close, 20)",  # 最小值
        "minindex_20": "MININDEX(close, 20)",  # 最小值索引
        "minmax_20": "MINMAX(close, 20)",  # 最小最大值
        "minmaxindex_20": "MINMAXINDEX(close, 20)",  # 最小最大值索引
        "mult": "MULT(high, low)",  # 乘法
        "sub": "SUB(high, low)",  # 减法
        "sum_20": "SUM(close, 20)",  # 求和
        
        # ===== 形态识别 (Pattern Recognition) - 选择性实现 =====
        "cdl_doji": "CDLDOJI(open, high, low, close)",  # 十字星
        "cdl_hammer": "CDLHAMMER(open, high, low, close)",  # 锤子线
        "cdl_hangingman": "CDLHANGINGMAN(open, high, low, close)",  # 上吊线
        "cdl_engulfing": "CDLENGULFING(open, high, low, close)",  # 吞噬形态
        "cdl_morning_star": "CDLMORNINGSTAR(open, high, low, close, 0.3)",  # 晨星
        "cdl_evening_star": "CDLEVENINGSTAR(open, high, low, close, 0.3)",  # 黄昏星
        "cdl_shooting_star": "CDLSHOOTINGSTAR(open, high, low, close)",  # 流星
        "cdl_spinning_top": "CDLSPINNINGTOP(open, high, low, close)",  # 纺锤顶
        "cdl_dragonfly_doji": "CDLDRAGONFLYDOJI(open, high, low, close)",  # 蜻蜓十字
        "cdl_gravestone_doji": "CDLGRAVESTONEDOJI(open, high, low, close)",  # 墓碑十字
    }
    
    # 因子分类定义
    CATEGORIES = {
        # 移动平均线
        "moving_averages": [
            "sma_5", "sma_10", "sma_20", "sma_50", "sma_200",
            "ema_5", "ema_10", "ema_20", "ema_50", "ema_200",
            "wma_10", "wma_20", "dema_10", "dema_20", "tema_10", "tema_20",
            "trima_10", "trima_20", "kama_10", "kama_20", "mama", "fama", "t3_10", "t3_20"
        ],
        
        # 布林带相关
        "bollinger_bands": [
            "bb_upper", "bb_middle", "bb_lower", "bb_width", "bb_percent"
        ],
        
        # 经典动量指标
        "momentum_classic": [
            "rsi_14", "rsi_21", "rsi_9", "macd", "macd_signal", "macd_histogram",
            "mom_10", "mom_20", "roc_10", "roc_20", "rocp_10", "rocp_20", "rocr_10", "rocr_20"
        ],
        
        # 随机指标系列
        "stochastic": [
            "stoch_k", "stoch_d", "stochf_k", "stochf_d", "stochrsi_k", "stochrsi_d"
        ],
        
        # 通道和振荡器
        "oscillators": [
            "cci_14", "cci_20", "cmo_14", "cmo_21", "apo_12_26", "ppo_12_26",
            "trix_14", "ultosc", "willr_14", "willr_21", "bop"
        ],
        
        # 方向性指标
        "directional": [
            "dx_14", "adx_14", "adxr_14", "plus_di_14", "minus_di_14", 
            "plus_dm_14", "minus_dm_14"
        ],
        
        # Aroon系列
        "aroon": [
            "aroon_up", "aroon_down", "aroon_osc"
        ],
        
        # 成交量指标
        "volume": [
            "ad", "adosc", "obv"
        ],
        
        # 波动率指标
        "volatility": [
            "atr_14", "atr_20", "natr_14", "natr_20", "trange"
        ],
        
        # 价格变换
        "price_transform": [
            "avgprice", "medprice", "typprice", "wclprice"
        ],
        
        # 周期分析
        "cycle_analysis": [
            "ht_dcperiod", "ht_dcphase", "ht_phasor_inphase", "ht_phasor_quadrature",
            "ht_sine_sine", "ht_sine_leadsine", "ht_trendmode"
        ],
        
        # 统计分析
        "statistics": [
            "beta_20", "correl_20", "linearreg_14", "linearreg_angle_14",
            "linearreg_intercept_14", "linearreg_slope_14", "stddev_20", "tsf_14", "var_20"
        ],
        
        # 数学变换
        "math_transform": [
            "acos", "asin", "atan", "ceil", "cos", "cosh", "exp", "floor",
            "ln", "log10", "sin", "sinh", "sqrt", "tan", "tanh"
        ],
        
        # 数学运算
        "math_operators": [
            "add", "div", "max_20", "maxindex_20", "min_20", "minindex_20",
            "minmax_20", "minmaxindex_20", "mult", "sub", "sum_20"
        ],
        
        # K线形态
        "candlestick_patterns": [
            "cdl_doji", "cdl_hammer", "cdl_hangingman", "cdl_engulfing",
            "cdl_morning_star", "cdl_evening_star", "cdl_shooting_star",
            "cdl_spinning_top", "cdl_dragonfly_doji", "cdl_gravestone_doji"
        ],
        
        # 趋势指标
        "trend": [
            "sma_20", "sma_50", "sma_200", "ema_20", "ema_50", "ema_200",
            "adx_14", "sar", "linearreg_14", "tsf_14"
        ],
        
        # 超买超卖
        "overbought_oversold": [
            "rsi_14", "stoch_k", "stoch_d", "cci_14", "willr_14", "cmo_14"
        ],
        
        # 强度指标
        "strength": [
            "adx_14", "dx_14", "atr_14", "obv", "ad", "bop"
        ],
        
        # 速度指标
        "velocity": [
            "mom_10", "roc_10", "macd", "ppo_12_26", "trix_14"
        ],
        
        # 核心指标 (最常用的)
        "core_indicators": [
            "sma_20", "ema_20", "rsi_14", "macd", "bb_upper", "bb_lower",
            "stoch_k", "atr_14", "adx_14", "obv"
        ]
    }