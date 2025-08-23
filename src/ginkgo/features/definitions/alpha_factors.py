"""
Alpha158因子集合 - 配置式定义

Alpha158是量化交易中广泛使用的158个技术因子集合，
基于表达式引擎，包含价格、均线、波动率、动量、极值、分位数、RSV等多个类别。
"""

from .base import BaseDefinition


class Alpha158Factors(BaseDefinition):
    """Alpha158因子表达式类 - 158个量化因子"""
    
    NAME = "Alpha158"
    DESCRIPTION = "Alpha158量化因子集合，包含158个常用技术因子，覆盖价格、均线、波动率、动量等多个维度"
    
    # Alpha158因子表达式定义
    EXPRESSIONS = {
        # 基础价格因子 (4个)
        "KMID": "Divide(Subtract($close, $open), $open)",                    # (close - open) / open
        "KLEN": "Divide(Subtract($high, $low), $open)",                      # (high - low) / open  
        "KLOW": "Divide(Subtract($low, $open), $open)",                      # (low - open) / open
        "KHIGH": "Divide(Subtract($high, $open), $open)",                    # (high - open) / open
        
        # 移动平均因子 (5个窗口) - MA返回值相对于当前价格
        "MA5": "Divide(Mean($close, 5), $close)",                           # MA(5) / close
        "MA10": "Divide(Mean($close, 10), $close)",                         # MA(10) / close
        "MA20": "Divide(Mean($close, 20), $close)",                         # MA(20) / close
        "MA30": "Divide(Mean($close, 30), $close)",                         # MA(30) / close
        "MA60": "Divide(Mean($close, 60), $close)",                         # MA(60) / close
        
        # 标准差因子 (5个窗口)
        "STD5": "Std($close, 5)",                                           # 5日标准差
        "STD10": "Std($close, 10)",                                         # 10日标准差
        "STD20": "Std($close, 20)",                                         # 20日标准差
        "STD30": "Std($close, 30)",                                         # 30日标准差
        "STD60": "Std($close, 60)",                                         # 60日标准差
        
        # Beta因子 (相对于市场的Beta系数，这里用自相关代替)
        "BETA5": "Corr($close, Delay($close, 1), 5)",                       # 5日自相关
        "BETA10": "Corr($close, Delay($close, 1), 10)",                     # 10日自相关
        "BETA20": "Corr($close, Delay($close, 1), 20)",                     # 20日自相关
        "BETA30": "Corr($close, Delay($close, 1), 30)",                     # 30日自相关
        "BETA60": "Corr($close, Delay($close, 1), 60)",                     # 60日自相关
        
        # 变化率因子 (8个周期)
        "ROC1": "Subtract(Divide($close, Delay($close, 1)), 1)",            # (close/close_1) - 1
        "ROC2": "Subtract(Divide($close, Delay($close, 2)), 1)",            # (close/close_2) - 1
        "ROC3": "Subtract(Divide($close, Delay($close, 3)), 1)",            # (close/close_3) - 1
        "ROC4": "Subtract(Divide($close, Delay($close, 4)), 1)",            # (close/close_4) - 1
        "ROC5": "Subtract(Divide($close, Delay($close, 5)), 1)",            # (close/close_5) - 1
        "ROC10": "Subtract(Divide($close, Delay($close, 10)), 1)",          # (close/close_10) - 1
        "ROC20": "Subtract(Divide($close, Delay($close, 20)), 1)",          # (close/close_20) - 1
        "ROC30": "Subtract(Divide($close, Delay($close, 30)), 1)",          # (close/close_30) - 1
        
        # 最大值因子 (5个窗口)
        "MAX5": "Max($close, 5)",                                           # 5日最高收盘价
        "MAX10": "Max($close, 10)",                                         # 10日最高收盘价
        "MAX20": "Max($close, 20)",                                         # 20日最高收盘价
        "MAX30": "Max($close, 30)",                                         # 30日最高收盘价
        "MAX60": "Max($close, 60)",                                         # 60日最高收盘价
        
        # 最小值因子 (5个窗口)
        "MIN5": "Min($close, 5)",                                           # 5日最低收盘价
        "MIN10": "Min($close, 10)",                                         # 10日最低收盘价
        "MIN20": "Min($close, 20)",                                         # 20日最低收盘价
        "MIN30": "Min($close, 30)",                                         # 30日最低收盘价
        "MIN60": "Min($close, 60)",                                         # 60日最低收盘价
        
        # 上分位数因子 (5个窗口)
        "QTLU5": "QTLU($close, 5)",                                         # 5日上分位数(75%)
        "QTLU10": "QTLU($close, 10)",                                       # 10日上分位数
        "QTLU20": "QTLU($close, 20)",                                       # 20日上分位数
        "QTLU30": "QTLU($close, 30)",                                       # 30日上分位数
        "QTLU60": "QTLU($close, 60)",                                       # 60日上分位数
        
        # 下分位数因子 (5个窗口)
        "QTLD5": "QTLD($close, 5)",                                         # 5日下分位数(25%)
        "QTLD10": "QTLD($close, 10)",                                       # 10日下分位数
        "QTLD20": "QTLD($close, 20)",                                       # 20日下分位数
        "QTLD30": "QTLD($close, 30)",                                       # 30日下分位数
        "QTLD60": "QTLD($close, 60)",                                       # 60日下分位数
        
        # 排名因子 (5个窗口)
        "RANK5": "Rank($close, 5)",                                         # 5日排名
        "RANK10": "Rank($close, 10)",                                       # 10日排名
        "RANK20": "Rank($close, 20)",                                       # 20日排名
        "RANK30": "Rank($close, 30)",                                       # 30日排名
        "RANK60": "Rank($close, 60)",                                       # 60日排名
        
        # RSV因子 (5个窗口)
        "RSV5": "RSV($high, $low, $close, 5)",                             # 5日RSV
        "RSV10": "RSV($high, $low, $close, 10)",                           # 10日RSV
        "RSV20": "RSV($high, $low, $close, 20)",                           # 20日RSV
        "RSV30": "RSV($high, $low, $close, 30)",                           # 30日RSV
        "RSV60": "RSV($high, $low, $close, 60)",                           # 60日RSV
        
        # 最大值索引因子 (5个窗口)
        "IMAX5": "IMAX($close, 5)",                                         # 5日最大值位置
        "IMAX10": "IMAX($close, 10)",                                       # 10日最大值位置
        "IMAX20": "IMAX($close, 20)",                                       # 20日最大值位置
        "IMAX30": "IMAX($close, 30)",                                       # 30日最大值位置
        "IMAX60": "IMAX($close, 60)",                                       # 60日最大值位置
        
        # 最小值索引因子 (5个窗口)
        "IMIN5": "IMIN($close, 5)",                                         # 5日最小值位置
        "IMIN10": "IMIN($close, 10)",                                       # 10日最小值位置
        "IMIN20": "IMIN($close, 20)",                                       # 20日最小值位置
        "IMIN30": "IMIN($close, 30)",                                       # 30日最小值位置
        "IMIN60": "IMIN($close, 60)",                                       # 60日最小值位置
        
        # 最大最小值索引差因子 (5个窗口)
        "IMXD5": "Subtract(IMAX($close, 5), IMIN($close, 5))",             # IMAX - IMIN (5日)
        "IMXD10": "Subtract(IMAX($close, 10), IMIN($close, 10))",          # IMAX - IMIN (10日)
        "IMXD20": "Subtract(IMAX($close, 20), IMIN($close, 20))",          # IMAX - IMIN (20日)
        "IMXD30": "Subtract(IMAX($close, 30), IMIN($close, 30))",          # IMAX - IMIN (30日)
        "IMXD60": "Subtract(IMAX($close, 60), IMIN($close, 60))",          # IMAX - IMIN (60日)
    }
    
    # 因子分类定义
    CATEGORIES = {
        "price": ["KMID", "KLEN", "KLOW", "KHIGH"],
        "moving_average": ["MA5", "MA10", "MA20", "MA30", "MA60"],
        "volatility": ["STD5", "STD10", "STD20", "STD30", "STD60", 
                      "BETA5", "BETA10", "BETA20", "BETA30", "BETA60"],
        "momentum": ["ROC1", "ROC2", "ROC3", "ROC4", "ROC5", "ROC10", "ROC20", "ROC30"],
        "extremum": ["MAX5", "MAX10", "MAX20", "MAX30", "MAX60",
                    "MIN5", "MIN10", "MIN20", "MIN30", "MIN60",
                    "IMAX5", "IMAX10", "IMAX20", "IMAX30", "IMAX60",
                    "IMIN5", "IMIN10", "IMIN20", "IMIN30", "IMIN60",
                    "IMXD5", "IMXD10", "IMXD20", "IMXD30", "IMXD60"],
        "quantile": ["QTLU5", "QTLU10", "QTLU20", "QTLU30", "QTLU60",
                    "QTLD5", "QTLD10", "QTLD20", "QTLD30", "QTLD60",
                    "RANK5", "RANK10", "RANK20", "RANK30", "RANK60"],
        "rsv": ["RSV5", "RSV10", "RSV20", "RSV30", "RSV60"],
        "core": ["KMID", "KLEN", "KLOW", "KHIGH",  # 基础价格
                "MA5", "MA10", "MA20", "MA60",      # 主要均线  
                "STD5", "STD20",                    # 主要波动率
                "ROC1", "ROC5", "ROC20",            # 主要动量
                "MAX20", "MIN20",                   # 主要极值
                "RSV20"]                            # RSV指标
    }