# Upstream: Backtest Engines, Portfolio Manager
# Downstream: Data Layer, Event System
# Role: ATR平均真实波幅指标继承BaseIndicator提供市场波动率分析和算法实现支持风险评估支持交易系统功能和组件集成提供完整业务支持






import pandas as pd
import numpy as np
from typing import List
from ginkgo.trading.computation.technical.base_indicator import BaseIndicator


class AverageTrueRange(BaseIndicator):
    """
    平均真实范围 (ATR) - 纯静态计算
    
    返回格式: DataFrame['timestamp', 'atr']
    """

    @staticmethod
    def cal(period: int, high_prices: List[float], low_prices: List[float], close_prices: List[float]) -> float:
        """
        计算平均真实范围
        
        Args:
            period: ATR计算周期
            high_prices: 最高价列表，长度必须等于period+1（需要前一日收盘价）
            low_prices: 最低价列表，长度必须等于period+1
            close_prices: 收盘价列表，长度必须等于period+1
            
        Returns:
            float: ATR值，如果数据不足或有错误则返回NaN
        """
        try:
            if period <= 0:
                return float('nan')
            
            if len(high_prices) != period + 1 or len(low_prices) != period + 1 or len(close_prices) != period + 1:
                return float('nan')
            
            # 检查是否包含NaN值
            if (any(pd.isna(price) for price in high_prices) or 
                any(pd.isna(price) for price in low_prices) or 
                any(pd.isna(price) for price in close_prices)):
                return float('nan')
            
            # 计算真实范围
            true_ranges = []
            for i in range(1, len(high_prices)):
                # 三种真实范围的计算方式
                tr1 = high_prices[i] - low_prices[i]  # 当日高低差
                tr2 = abs(high_prices[i] - close_prices[i-1])  # 当日高价与前日收盘价差
                tr3 = abs(low_prices[i] - close_prices[i-1])   # 当日低价与前日收盘价差
                
                # 取最大值作为真实范围
                true_range = max(tr1, tr2, tr3)
                true_ranges.append(true_range)
            
            # 计算ATR（真实范围的简单移动平均）
            atr_value = sum(true_ranges) / period
            
            return atr_value
            
        except Exception:
            return float('nan')
    
    @staticmethod
    def cal_matrix(period: int, matrix_data: pd.DataFrame) -> pd.DataFrame:
        """
        ATR的Matrix回测计算 - 静态方法
        
        Args:
            period: ATR计算周期
            matrix_data: 矩阵数据
            
        Returns:
            pd.DataFrame: ATR计算结果
        """
        try:
            if period <= 0:
                return BaseIndicator.cal_matrix(matrix_data)
                
            if 'code' in matrix_data.columns:
                # 长格式：按股票分组计算
                def calc_atr_for_group(group):
                    group = group.sort_values('timestamp')
                    if len(group) < period + 1:
                        group['atr'] = float('nan')
                        return group
                    
                    # 计算True Range
                    high = group['high']
                    low = group['low']
                    close = group['close']
                    prev_close = close.shift(1)
                    
                    tr1 = high - low
                    tr2 = (high - prev_close).abs()
                    tr3 = (low - prev_close).abs()
                    
                    true_range = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
                    
                    # 计算ATR
                    group['atr'] = true_range.rolling(period).mean()
                    return group
                
                result = matrix_data.groupby('code').apply(calc_atr_for_group).reset_index(drop=True)
                return result
            else:
                # 宽格式：ATR需要HLC数据，返回NaN占位符
                return pd.DataFrame(
                    float('nan'), 
                    index=matrix_data.index, 
                    columns=matrix_data.columns
                )
                
        except Exception:
            return BaseIndicator.cal_matrix(matrix_data)
