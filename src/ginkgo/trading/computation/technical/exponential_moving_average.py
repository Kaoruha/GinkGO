# Upstream: Backtest Engines, Portfolio Manager
# Downstream: Data Layer, Event System
# Role: ExponentialMovingAverage指数移动平均线继承BaseIndicator提供趋势分析和价格平滑功能






import pandas as pd
import numpy as np
from typing import List
from ginkgo.trading.computation.technical.base_indicator import BaseIndicator


class ExponentialMovingAverage(BaseIndicator):
    """
    指数移动平均线 (EMA) - 纯静态计算
    
    返回格式: DataFrame['timestamp', 'ema']
    """

    @staticmethod
    def cal(period: int, prices: List[float]) -> float:
        """
        计算指数移动平均线
        
        Args:
            period: EMA计算周期
            prices: 价格列表，长度必须等于period
            
        Returns:
            float: EMA值，如果数据不足或有错误则返回NaN
        """
        try:
            if period <= 0:
                return float('nan')
            
            if len(prices) != period:
                return float('nan')
            
            # 检查是否包含NaN值
            if any(pd.isna(price) for price in prices):
                return float('nan')
            
            # 计算EMA平滑系数
            alpha = 2.0 / (period + 1)
            
            # 初始值使用第一个价格
            ema = prices[0]
            
            # 逐步计算EMA
            for i in range(1, len(prices)):
                ema = alpha * prices[i] + (1 - alpha) * ema
            
            return ema
            
        except Exception:
            return float('nan')
    
    @staticmethod
    def cal_matrix(period: int, matrix_data: pd.DataFrame) -> pd.DataFrame:
        """
        EMA的Matrix回测计算 - 静态方法
        
        Args:
            period: EMA计算周期
            matrix_data: 矩阵数据
            
        Returns:
            pd.DataFrame: EMA计算结果
        """
        try:
            if period <= 0:
                return BaseIndicator.cal_matrix(matrix_data)
                
            if 'code' in matrix_data.columns:
                # 长格式：按股票分组计算
                def calc_ema_for_group(group):
                    group = group.sort_values('timestamp')
                    
                    if len(group) < period:
                        group['ema'] = float('nan')
                        return group
                    
                    # 使用pandas的ewm方法计算EMA
                    alpha = 2.0 / (period + 1)
                    group['ema'] = group['close'].ewm(alpha=alpha, adjust=False).mean()
                    
                    return group
                
                result = matrix_data.groupby('code').apply(calc_ema_for_group).reset_index(drop=True)
                return result
            else:
                # 宽格式：使用pandas的ewm方法进行高效计算
                alpha = 2.0 / (period + 1)
                return matrix_data.ewm(alpha=alpha, adjust=False).mean()
                
        except Exception:
            return BaseIndicator.cal_matrix(matrix_data)
