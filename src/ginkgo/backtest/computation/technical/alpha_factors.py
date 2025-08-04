"""
Alpha因子指标实现 - 基于QLib Alpha158
实现常用的量化因子，支持事件引擎和矩阵引擎双模式
"""

import pandas as pd
import numpy as np
from typing import Dict, List
from .base_indicator import BaseIndicator


class KMID(BaseIndicator):
    """
    价格动量因子：日内动量
    公式：(close - open) / open
    """
    
    def __init__(self, name: str = "KMID", **kwargs):
        super().__init__(name, **kwargs)
    
    def cal(self, raw: pd.DataFrame, **kwargs) -> pd.DataFrame:
        df = raw.copy()
        rs = pd.DataFrame()
        rs["timestamp"] = df["timestamp"]
        rs[self.name] = (df["close"] - df["open"]) / df["open"]
        return rs
    
    def _calculate_vectorized(self, matrix_data: Dict[str, pd.DataFrame], 
                            dates: List, codes: List) -> pd.DataFrame:
        """高效矢量化计算"""
        close = matrix_data["close"]
        open_price = matrix_data["open"]
        return (close - open_price) / open_price


class KLEN(BaseIndicator):
    """
    波动率因子：日内波动幅度
    公式：(high - low) / open
    """
    
    def __init__(self, name: str = "KLEN", **kwargs):
        super().__init__(name, **kwargs)
    
    def cal(self, raw: pd.DataFrame, **kwargs) -> pd.DataFrame:
        df = raw.copy()
        rs = pd.DataFrame()
        rs["timestamp"] = df["timestamp"]
        rs[self.name] = (df["high"] - df["low"]) / df["open"]
        return rs
    
    def _calculate_vectorized(self, matrix_data: Dict[str, pd.DataFrame], 
                            dates: List, codes: List) -> pd.DataFrame:
        high = matrix_data["high"]
        low = matrix_data["low"]
        open_price = matrix_data["open"]
        return (high - low) / open_price


class KLOW(BaseIndicator):
    """
    价格位置因子：收盘价相对于最低价的位置
    公式：(close - low) / open
    """
    
    def __init__(self, name: str = "KLOW", **kwargs):
        super().__init__(name, **kwargs)
    
    def cal(self, raw: pd.DataFrame, **kwargs) -> pd.DataFrame:
        df = raw.copy()
        rs = pd.DataFrame()
        rs["timestamp"] = df["timestamp"]
        rs[self.name] = (df["close"] - df["low"]) / df["open"]
        return rs
    
    def _calculate_vectorized(self, matrix_data: Dict[str, pd.DataFrame], 
                            dates: List, codes: List) -> pd.DataFrame:
        close = matrix_data["close"]
        low = matrix_data["low"]
        open_price = matrix_data["open"]
        return (close - low) / open_price


class KHIGH(BaseIndicator):
    """
    价格位置因子：收盘价相对于最高价的位置
    公式：(high - close) / open
    """
    
    def __init__(self, name: str = "KHIGH", **kwargs):
        super().__init__(name, **kwargs)
    
    def cal(self, raw: pd.DataFrame, **kwargs) -> pd.DataFrame:
        df = raw.copy()
        rs = pd.DataFrame()
        rs["timestamp"] = df["timestamp"]
        rs[self.name] = (df["high"] - df["close"]) / df["open"]
        return rs
    
    def _calculate_vectorized(self, matrix_data: Dict[str, pd.DataFrame], 
                            dates: List, codes: List) -> pd.DataFrame:
        high = matrix_data["high"]
        close = matrix_data["close"]
        open_price = matrix_data["open"]
        return (high - close) / open_price


class MA(BaseIndicator):
    """
    移动平均因子
    公式：close.rolling(n).mean() / close
    """
    
    def __init__(self, name: str = "MA", window: int = 5, **kwargs):
        super().__init__(name, **kwargs)
        self.window = window
    
    def cal(self, raw: pd.DataFrame, **kwargs) -> pd.DataFrame:
        df = raw.copy()
        rs = pd.DataFrame()
        rs["timestamp"] = df["timestamp"]
        ma_value = df["close"].rolling(self.window).mean()
        rs[self.name] = ma_value / df["close"]
        return rs
    
    def _calculate_vectorized(self, matrix_data: Dict[str, pd.DataFrame], 
                            dates: List, codes: List) -> pd.DataFrame:
        close = matrix_data["close"]
        ma = close.rolling(self.window).mean()
        return ma / close


class STD(BaseIndicator):
    """
    波动率因子：标准差
    公式：close.rolling(n).std() / close
    """
    
    def __init__(self, name: str = "STD", window: int = 5, **kwargs):
        super().__init__(name, **kwargs)
        self.window = window
    
    def cal(self, raw: pd.DataFrame, **kwargs) -> pd.DataFrame:
        df = raw.copy()
        rs = pd.DataFrame()
        rs["timestamp"] = df["timestamp"]
        std_value = df["close"].rolling(self.window).std()
        rs[self.name] = std_value / df["close"]
        return rs
    
    def _calculate_vectorized(self, matrix_data: Dict[str, pd.DataFrame], 
                            dates: List, codes: List) -> pd.DataFrame:
        close = matrix_data["close"]
        std = close.rolling(self.window).std()
        return std / close


class BETA(BaseIndicator):
    """
    市场Beta因子：价格相对于均价的beta
    公式：(close / close.rolling(n).mean() - 1).rolling(n).mean()
    """
    
    def __init__(self, name: str = "BETA", window: int = 5, **kwargs):
        super().__init__(name, **kwargs)
        self.window = window
    
    def cal(self, raw: pd.DataFrame, **kwargs) -> pd.DataFrame:
        df = raw.copy()
        rs = pd.DataFrame()
        rs["timestamp"] = df["timestamp"]
        
        close = df["close"]
        ma = close.rolling(self.window).mean()
        returns = close / ma - 1
        beta = returns.rolling(self.window).mean()
        
        rs[self.name] = beta
        return rs
    
    def _calculate_vectorized(self, matrix_data: Dict[str, pd.DataFrame], 
                            dates: List, codes: List) -> pd.DataFrame:
        close = matrix_data["close"]
        ma = close.rolling(self.window).mean()
        returns = close / ma - 1
        return returns.rolling(self.window).mean()


class ROC(BaseIndicator):
    """
    变化率因子：价格变化率
    公式：close / Ref(close, n) - 1
    """
    
    def __init__(self, name: str = "ROC", period: int = 1, **kwargs):
        super().__init__(name, **kwargs)
        self.period = period
    
    def cal(self, raw: pd.DataFrame, **kwargs) -> pd.DataFrame:
        df = raw.copy()
        rs = pd.DataFrame()
        rs["timestamp"] = df["timestamp"]
        
        close = df["close"]
        prev_close = close.shift(self.period)
        rs[self.name] = close / prev_close - 1
        
        return rs
    
    def _calculate_vectorized(self, matrix_data: Dict[str, pd.DataFrame], 
                            dates: List, codes: List) -> pd.DataFrame:
        close = matrix_data["close"]
        prev_close = close.shift(self.period)
        return close / prev_close - 1


class MAX(BaseIndicator):
    """
    最大值因子：滚动窗口最大值
    公式：close.rolling(n).max() / close
    """
    
    def __init__(self, name: str = "MAX", window: int = 5, **kwargs):
        super().__init__(name, **kwargs)
        self.window = window
    
    def cal(self, raw: pd.DataFrame, **kwargs) -> pd.DataFrame:
        df = raw.copy()
        rs = pd.DataFrame()
        rs["timestamp"] = df["timestamp"]
        
        max_value = df["close"].rolling(self.window).max()
        rs[self.name] = max_value / df["close"]
        
        return rs
    
    def _calculate_vectorized(self, matrix_data: Dict[str, pd.DataFrame], 
                            dates: List, codes: List) -> pd.DataFrame:
        close = matrix_data["close"]
        max_value = close.rolling(self.window).max()
        return max_value / close


class MIN(BaseIndicator):
    """
    最小值因子：滚动窗口最小值
    公式：close.rolling(n).min() / close
    """
    
    def __init__(self, name: str = "MIN", window: int = 5, **kwargs):
        super().__init__(name, **kwargs)
        self.window = window
    
    def cal(self, raw: pd.DataFrame, **kwargs) -> pd.DataFrame:
        df = raw.copy()
        rs = pd.DataFrame()
        rs["timestamp"] = df["timestamp"]
        
        min_value = df["close"].rolling(self.window).min()
        rs[self.name] = min_value / df["close"]
        
        return rs
    
    def _calculate_vectorized(self, matrix_data: Dict[str, pd.DataFrame], 
                            dates: List, codes: List) -> pd.DataFrame:
        close = matrix_data["close"]
        min_value = close.rolling(self.window).min()
        return min_value / close


class QTLU(BaseIndicator):
    """
    分位数因子：滚动窗口上分位数
    公式：close.rolling(n).quantile(0.8) / close
    """
    
    def __init__(self, name: str = "QTLU", window: int = 5, quantile: float = 0.8, **kwargs):
        super().__init__(name, **kwargs)
        self.window = window
        self.quantile = quantile
    
    def cal(self, raw: pd.DataFrame, **kwargs) -> pd.DataFrame:
        df = raw.copy()
        rs = pd.DataFrame()
        rs["timestamp"] = df["timestamp"]
        
        qtl_value = df["close"].rolling(self.window).quantile(self.quantile)
        rs[self.name] = qtl_value / df["close"]
        
        return rs
    
    def _calculate_vectorized(self, matrix_data: Dict[str, pd.DataFrame], 
                            dates: List, codes: List) -> pd.DataFrame:
        close = matrix_data["close"]
        qtl_value = close.rolling(self.window).quantile(self.quantile)
        return qtl_value / close


class QTLD(BaseIndicator):
    """
    分位数因子：滚动窗口下分位数
    公式：close.rolling(n).quantile(0.2) / close
    """
    
    def __init__(self, name: str = "QTLD", window: int = 5, quantile: float = 0.2, **kwargs):
        super().__init__(name, **kwargs)
        self.window = window
        self.quantile = quantile
    
    def cal(self, raw: pd.DataFrame, **kwargs) -> pd.DataFrame:
        df = raw.copy()
        rs = pd.DataFrame()
        rs["timestamp"] = df["timestamp"]
        
        qtl_value = df["close"].rolling(self.window).quantile(self.quantile)
        rs[self.name] = qtl_value / df["close"]
        
        return rs
    
    def _calculate_vectorized(self, matrix_data: Dict[str, pd.DataFrame], 
                            dates: List, codes: List) -> pd.DataFrame:
        close = matrix_data["close"]
        qtl_value = close.rolling(self.window).quantile(self.quantile)
        return qtl_value / close


class RANK(BaseIndicator):
    """
    排名因子：横截面排名
    公式：当前值在滚动窗口中的排名百分比
    """
    
    def __init__(self, name: str = "RANK", window: int = 5, **kwargs):
        super().__init__(name, **kwargs)
        self.window = window
    
    def cal(self, raw: pd.DataFrame, **kwargs) -> pd.DataFrame:
        df = raw.copy()
        rs = pd.DataFrame()
        rs["timestamp"] = df["timestamp"]
        
        # 计算滚动排名
        rank_value = df["close"].rolling(self.window).apply(
            lambda x: (x.iloc[-1] > x).mean() if len(x) == self.window else np.nan
        )
        rs[self.name] = rank_value
        
        return rs
    
    def _calculate_vectorized(self, matrix_data: Dict[str, pd.DataFrame], 
                            dates: List, codes: List) -> pd.DataFrame:
        close = matrix_data["close"]
        
        # 横截面排名：每个日期，计算各股票的排名
        result = pd.DataFrame(index=dates, columns=codes)
        
        for date in dates:
            if date in close.index:
                values = close.loc[date]
                ranks = values.rank(pct=True)  # 百分比排名
                result.loc[date] = ranks
        
        return result


class RSV(BaseIndicator):
    """
    RSV因子：相对强弱值 (Raw Stochastic Value)
    公式：(close - low.rolling(n).min()) / (high.rolling(n).max() - low.rolling(n).min())
    """
    
    def __init__(self, name: str = "RSV", window: int = 9, **kwargs):
        super().__init__(name, **kwargs)
        self.window = window
    
    def cal(self, raw: pd.DataFrame, **kwargs) -> pd.DataFrame:
        df = raw.copy()
        rs = pd.DataFrame()
        rs["timestamp"] = df["timestamp"]
        
        close = df["close"]
        high = df["high"]
        low = df["low"]
        
        lowest_low = low.rolling(self.window).min()
        highest_high = high.rolling(self.window).max()
        
        rs[self.name] = (close - lowest_low) / (highest_high - lowest_low)
        
        return rs
    
    def _calculate_vectorized(self, matrix_data: Dict[str, pd.DataFrame], 
                            dates: List, codes: List) -> pd.DataFrame:
        close = matrix_data["close"]
        high = matrix_data["high"]
        low = matrix_data["low"]
        
        lowest_low = low.rolling(self.window).min()
        highest_high = high.rolling(self.window).max()
        
        return (close - lowest_low) / (highest_high - lowest_low)


class IMAX(BaseIndicator):
    """
    最大值位置因子：最大值出现的位置
    公式：argmax(high.rolling(n)) / n
    """
    
    def __init__(self, name: str = "IMAX", window: int = 5, **kwargs):
        super().__init__(name, **kwargs)
        self.window = window
    
    def cal(self, raw: pd.DataFrame, **kwargs) -> pd.DataFrame:
        df = raw.copy()
        rs = pd.DataFrame()
        rs["timestamp"] = df["timestamp"]
        
        # 计算最大值位置
        def argmax_position(series):
            if len(series) < self.window:
                return np.nan
            return (len(series) - 1 - series.argmax()) / (len(series) - 1)
        
        imax_value = df["high"].rolling(self.window).apply(argmax_position)
        rs[self.name] = imax_value
        
        return rs
    
    def _calculate_vectorized(self, matrix_data: Dict[str, pd.DataFrame], 
                            dates: List, codes: List) -> pd.DataFrame:
        high = matrix_data["high"]
        
        def argmax_position(series):
            if len(series) < self.window:
                return np.nan
            return (len(series) - 1 - series.argmax()) / (len(series) - 1)
        
        return high.rolling(self.window).apply(argmax_position)


class IMIN(BaseIndicator):
    """
    最小值位置因子：最小值出现的位置
    公式：argmin(low.rolling(n)) / n
    """
    
    def __init__(self, name: str = "IMIN", window: int = 5, **kwargs):
        super().__init__(name, **kwargs)
        self.window = window
    
    def cal(self, raw: pd.DataFrame, **kwargs) -> pd.DataFrame:
        df = raw.copy()
        rs = pd.DataFrame()
        rs["timestamp"] = df["timestamp"]
        
        # 计算最小值位置
        def argmin_position(series):
            if len(series) < self.window:
                return np.nan
            return (len(series) - 1 - series.argmin()) / (len(series) - 1)
        
        imin_value = df["low"].rolling(self.window).apply(argmin_position)
        rs[self.name] = imin_value
        
        return rs
    
    def _calculate_vectorized(self, matrix_data: Dict[str, pd.DataFrame], 
                            dates: List, codes: List) -> pd.DataFrame:
        low = matrix_data["low"]
        
        def argmin_position(series):
            if len(series) < self.window:
                return np.nan
            return (len(series) - 1 - series.argmin()) / (len(series) - 1)
        
        return low.rolling(self.window).apply(argmin_position)


class IMXD(BaseIndicator):
    """
    最大值距离因子：距离最大值的天数
    公式：距离最大值的天数 / 窗口大小
    """
    
    def __init__(self, name: str = "IMXD", window: int = 5, **kwargs):
        super().__init__(name, **kwargs)
        self.window = window
    
    def cal(self, raw: pd.DataFrame, **kwargs) -> pd.DataFrame:
        df = raw.copy()
        rs = pd.DataFrame()
        rs["timestamp"] = df["timestamp"]
        
        def days_since_max(series):
            if len(series) < self.window:
                return np.nan
            max_idx = series.argmax()
            return (len(series) - 1 - max_idx) / (self.window - 1)
        
        imxd_value = df["high"].rolling(self.window).apply(days_since_max)
        rs[self.name] = imxd_value
        
        return rs
    
    def _calculate_vectorized(self, matrix_data: Dict[str, pd.DataFrame], 
                            dates: List, codes: List) -> pd.DataFrame:
        high = matrix_data["high"]
        
        def days_since_max(series):
            if len(series) < self.window:
                return np.nan
            max_idx = series.argmax()
            return (len(series) - 1 - max_idx) / (self.window - 1)
        
        return high.rolling(self.window).apply(days_since_max)