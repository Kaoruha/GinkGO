import pandas as pd
import numpy as np
from typing import List, Union
from .base_indicator import BaseIndicator


class SimpleMovingAverage(BaseIndicator):
    """
    简单移动平均线 (SMA) - 纯静态计算
    """

    @staticmethod
    def cal(period: int, prices: List[float]) -> float:
        """
        计算简单移动平均线
        
        Args:
            period: 移动平均周期
            prices: 价格列表，长度必须等于period
            
        Returns:
            float: SMA值，如果数据不足或有错误则返回NaN
        """
        try:
            if period <= 0:
                return float('nan')
            
            if len(prices) != period:
                return float('nan')
            
            # 检查是否包含NaN值
            if any(pd.isna(price) for price in prices):
                return float('nan')
            
            return sum(prices) / period
            
        except Exception:
            return float('nan')
    
    @staticmethod
    def cal_matrix(period: int, close_matrix: pd.DataFrame) -> pd.DataFrame:
        """
        SMA的Matrix回测计算 - 静态方法
        
        Args:
            period: 移动平均周期
            close_matrix: 收盘价矩阵 (日期 × 股票代码)
            
        Returns:
            pd.DataFrame: SMA计算结果，与输入矩阵同维度
        """
        try:
            if period <= 0:
                return pd.DataFrame(
                    float('nan'), 
                    index=close_matrix.index, 
                    columns=close_matrix.columns
                )
            
            # 直接对整个矩阵进行滚动平均计算
            return close_matrix.rolling(window=period).mean()
                
        except Exception:
            return pd.DataFrame(
                float('nan'), 
                index=close_matrix.index, 
                columns=close_matrix.columns
            )
