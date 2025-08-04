import pandas as pd
import numpy as np
from typing import List
from .base_indicator import BaseIndicator


class RelativeStrengthIndex(BaseIndicator):
    """
    相对强弱指数 (RSI) - 纯静态计算
    
    返回格式: DataFrame['timestamp', 'rsi']
    """

    @staticmethod
    def cal(period: int, prices: List[float]) -> float:
        """
        计算RSI指标
        
        Args:
            period: RSI计算周期
            prices: 价格列表，长度必须等于period+1（需要计算价格变化）
            
        Returns:
            float: RSI值，如果数据不足或有错误则返回NaN
        """
        try:
            if period <= 0:
                return float('nan')
            
            if len(prices) != period + 1:
                return float('nan')
            
            # 检查是否包含NaN值
            if any(pd.isna(price) for price in prices):
                return float('nan')
            
            # 计算价格变化
            price_diffs = [prices[i] - prices[i-1] for i in range(1, len(prices))]
            
            # 分离上涨和下跌
            gains = [diff if diff > 0 else 0 for diff in price_diffs]
            losses = [-diff if diff < 0 else 0 for diff in price_diffs]
            
            # 计算平均增益和平均损失
            avg_gain = sum(gains) / period
            avg_loss = sum(losses) / period
            
            # 计算RSI，避免除零
            if avg_loss == 0:
                return 100.0 if avg_gain > 0 else 50.0
            
            rs = avg_gain / avg_loss
            rsi = 100 - (100 / (1 + rs))
            
            return rsi
            
        except Exception:
            return float('nan')
    
    @staticmethod
    def cal_matrix(period: int, matrix_data: pd.DataFrame) -> pd.DataFrame:
        """
        RSI的Matrix回测计算 - 静态方法
        
        Args:
            period: RSI计算周期
            matrix_data: 矩阵数据
            
        Returns:
            pd.DataFrame: RSI计算结果
        """
        try:
            if period <= 0:
                return BaseIndicator.cal_matrix(matrix_data)
                
            if 'code' in matrix_data.columns:
                # 长格式：按股票分组计算
                def calc_rsi_for_group(group):
                    group = group.sort_values('timestamp')
                    
                    if len(group) < period + 1:
                        group['rsi'] = float('nan')
                        return group
                    
                    # 计算价格变化
                    price_diff = group['close'].diff()
                    
                    # 分离上涨和下跌
                    gains = price_diff.where(price_diff > 0, 0)
                    losses = -price_diff.where(price_diff < 0, 0)
                    
                    # 计算平均增益和平均损失
                    avg_gains = gains.rolling(window=period).mean()
                    avg_losses = losses.rolling(window=period).mean()
                    
                    # 计算RSI，避免除零
                    rs_ratio = avg_gains / avg_losses
                    rs_ratio = rs_ratio.replace([np.inf, -np.inf], np.nan)
                    
                    rsi = 100 - (100 / (1 + rs_ratio))
                    
                    group['rsi'] = rsi
                    return group
                
                result = matrix_data.groupby('code').apply(calc_rsi_for_group).reset_index(drop=True)
                return result
            else:
                # 宽格式：对整个矩阵计算RSI
                price_diff = matrix_data.diff()
                gains = price_diff.where(price_diff > 0, 0)
                losses = -price_diff.where(price_diff < 0, 0)
                
                avg_gains = gains.rolling(window=period).mean()
                avg_losses = losses.rolling(window=period).mean()
                
                rs_ratio = avg_gains / avg_losses
                rs_ratio = rs_ratio.replace([np.inf, -np.inf], np.nan)
                
                rsi = 100 - (100 / (1 + rs_ratio))
                
                return rsi
                
        except Exception:
            return BaseIndicator.cal_matrix(matrix_data)


class RSISignal(BaseIndicator):
    """
    RSI交易信号指标 - 纯静态计算
    
    基于RSI的经典交易信号：
    - RSI从下方突破30：买入信号
    - RSI从上方跌破70：卖出信号
    - RSI在30-70之间：持有信号
    
    返回格式: DataFrame['timestamp', 'rsi_signal']
    """

    @staticmethod
    def cal(period: int, oversold: float, overbought: float, data: pd.DataFrame) -> pd.DataFrame:
        """
        计算RSI交易信号
        
        Args:
            period: RSI计算周期
            oversold: 超卖阈值
            overbought: 超买阈值
            data: DataFrame，必须包含 'close' 和 'timestamp' 列
        
        Returns:
            DataFrame: 包含 'timestamp' 和 'rsi_signal' 列，信号值: 1 (买入), -1 (卖出), 0 (持有)
        """
        try:
            validated_data, error = RSISignal._validate_and_prepare(
                data, ['close', 'timestamp'], period + 1
            )
            if error:
                return RSISignal._handle_error(data, ['rsi_signal'])
            
            df = validated_data.sort_values('timestamp').reset_index(drop=True)
            
            # 先计算RSI
            price_diff = df["close"].diff()
            gains = price_diff.where(price_diff > 0, 0)
            losses = -price_diff.where(price_diff < 0, 0)
            
            avg_gains = gains.rolling(window=period).mean()
            avg_losses = losses.rolling(window=period).mean()
            
            rs_ratio = avg_gains / avg_losses
            rs_ratio = rs_ratio.replace([np.inf, -np.inf], np.nan)
            rsi = 100 - (100 / (1 + rs_ratio))
            
            # 生成交易信号
            signals = np.zeros(len(df))
            
            for i in range(1, len(df)):
                current_rsi = rsi.iloc[i]
                prev_rsi = rsi.iloc[i-1]
                
                if pd.isna(current_rsi) or pd.isna(prev_rsi):
                    continue
                
                # RSI从超卖区域向上突破：买入信号
                if prev_rsi <= oversold and current_rsi > oversold:
                    signals[i] = 1
                
                # RSI从超买区域向下突破：卖出信号
                elif prev_rsi >= overbought and current_rsi < overbought:
                    signals[i] = -1
            
            return RSISignal._create_result_df(
                df,
                rsi_signal=pd.Series(signals, index=df.index)
            )
            
        except Exception:
            return RSISignal._handle_error(data, ['rsi_signal'])
    
    @staticmethod
    def cal_matrix(period: int, oversold: float, overbought: float, matrix_data: pd.DataFrame) -> pd.DataFrame:
        """
        RSI信号的Matrix计算 - 静态方法
        
        Args:
            period: RSI计算周期
            oversold: 超卖阈值
            overbought: 超买阈值
            matrix_data: 矩阵数据
            
        Returns:
            pd.DataFrame: RSI信号计算结果
        """
        try:
            if 'code' in matrix_data.columns:
                # 长格式：按股票分组计算信号
                def calc_signal_for_group(group):
                    group = group.sort_values('timestamp')
                    
                    if len(group) < period + 1:
                        group['rsi_signal'] = 0
                        return group
                    
                    # 计算RSI
                    price_diff = group['close'].diff()
                    gains = price_diff.where(price_diff > 0, 0)
                    losses = -price_diff.where(price_diff < 0, 0)
                    
                    avg_gains = gains.rolling(window=period).mean()
                    avg_losses = losses.rolling(window=period).mean()
                    
                    rs_ratio = avg_gains / avg_losses
                    rs_ratio = rs_ratio.replace([np.inf, -np.inf], np.nan)
                    rsi = 100 - (100 / (1 + rs_ratio))
                    
                    # 生成交易信号
                    signals = np.zeros(len(group))
                    
                    for i in range(1, len(group)):
                        current_rsi = rsi.iloc[i]
                        prev_rsi = rsi.iloc[i-1]
                        
                        if pd.isna(current_rsi) or pd.isna(prev_rsi):
                            continue
                        
                        # RSI突破信号
                        if prev_rsi <= oversold and current_rsi > oversold:
                            signals[i] = 1
                        elif prev_rsi >= overbought and current_rsi < overbought:
                            signals[i] = -1
                    
                    group['rsi_signal'] = signals
                    return group
                
                result = matrix_data.groupby('code').apply(calc_signal_for_group).reset_index(drop=True)
                return result
            else:
                # 宽格式：暂时返回零信号矩阵
                return pd.DataFrame(0, index=matrix_data.index, columns=matrix_data.columns)
                
        except Exception:
            return BaseIndicator.cal_matrix(matrix_data)