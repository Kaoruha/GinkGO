# Upstream: Backtest Engines, Portfolio Manager
# Downstream: Data Layer, Event System
# Role: WeightedMovingAverage加权移动平均线继承BaseIndicator提供加权趋势分析功能






import pandas as pd
import numpy as np
from typing import List
from ginkgo.trading.computation.technical.base_indicator import BaseIndicator


class WeightedMovingAverage(BaseIndicator):
    """
    加权移动平均线 (WMA) - 纯静态计算
    
    返回格式: DataFrame['timestamp', 'wma']
    """

    @staticmethod
    def cal(period: int, prices: List[float]) -> float:
        """
        计算加权移动平均线
        
        Args:
            period: WMA计算周期
            prices: 价格列表，长度必须等于period
            
        Returns:
            float: WMA值，如果数据不足或有错误则返回NaN
        """
        try:
            if period <= 0:
                return float('nan')
            
            if len(prices) != period:
                return float('nan')
            
            # 检查是否包含NaN值
            if any(pd.isna(price) for price in prices):
                return float('nan')
            
            # 生成权重：最新数据权重最大 (1, 2, 3, ..., period)
            weights = np.array([i for i in range(1, period + 1)], dtype=float)
            weights = weights / weights.sum()  # 标准化权重
            
            # 计算加权平均
            wma_value = np.sum(np.array(prices) * weights)
            
            return wma_value
            
        except Exception:
            return float('nan')
    
    @staticmethod
    def cal_matrix(period: int, matrix_data: pd.DataFrame) -> pd.DataFrame:
        """
        WMA的Matrix回测计算 - 静态方法
        
        Args:
            period: WMA计算周期
            matrix_data: 矩阵数据
            
        Returns:
            pd.DataFrame: WMA计算结果
        """
        try:
            if period <= 0:
                return BaseIndicator.cal_matrix(matrix_data)
                
            # 生成权重：最新数据权重最大
            weights = np.array([i for i in range(1, period + 1)])
            weights = weights / weights.sum()  # 标准化权重
                
            if 'code' in matrix_data.columns:
                # 长格式：按股票分组计算
                def calc_wma_for_group(group):
                    group = group.sort_values('timestamp')
                    
                    if len(group) < period:
                        group['wma'] = float('nan')
                        return group
                    
                    wma_values = []
                    for i in range(len(group)):
                        if i < period - 1:
                            wma_values.append(np.nan)
                        else:
                            # 获取最近period个价格
                            price_window = group['close'].iloc[i-period+1:i+1].values
                            # 计算加权平均
                            wma_value = np.sum(price_window * weights)
                            wma_values.append(wma_value)
                    
                    group['wma'] = wma_values
                    return group
                
                result = matrix_data.groupby('code').apply(calc_wma_for_group).reset_index(drop=True)
                return result
            else:
                # 宽格式：对整个矩阵计算WMA
                result = matrix_data.copy()
                for i in range(len(matrix_data)):
                    if i >= period - 1:
                        # 获取最近period行数据
                        data_window = matrix_data.iloc[i-period+1:i+1].values
                        # 计算加权平均
                        weighted_values = np.sum(data_window * weights.reshape(-1, 1), axis=0)
                        result.iloc[i] = weighted_values
                    else:
                        result.iloc[i] = np.nan
                return result
                
        except Exception:
            return BaseIndicator.cal_matrix(matrix_data)
