# Upstream: Backtest Engines, Portfolio Manager
# Downstream: Data Layer, Event System
# Role: BollingerBands布林带指标继承BaseIndicator提供价格通道和波动率分析功能支持交易系统功能和组件集成提供完整业务支持






import pandas as pd
import numpy as np
from typing import List, Tuple
from ginkgo.trading.computation.technical.base_indicator import BaseIndicator


class BollingerBands(BaseIndicator):
    """
    布林带指标 (Bollinger Bands) - 纯静态计算

    返回格式: DataFrame['timestamp', 'bb_upper', 'bb_middle', 'bb_lower', 'bb_position']
    """

    @staticmethod
    def cal(period: int, std_multiplier: float, prices: List[float]) -> Tuple[float, float, float, float]:
        """
        计算布林带指标

        Args:
            period: 移动平均和标准差计算周期
            std_multiplier: 标准差倍数
            prices: 价格列表，长度必须等于period

        Returns:
            Tuple[float, float, float, float]: (上轨, 中轨, 下轨, 价格位置)
            价格位置在0-1之间，0.5表示在中轨，如果有错误则返回NaN
        """
        try:
            if period <= 0 or std_multiplier <= 0:
                return (float('nan'), float('nan'), float('nan'), float('nan'))
            
            if len(prices) != period:
                return (float('nan'), float('nan'), float('nan'), float('nan'))

            # 检查是否包含NaN值
            if any(pd.isna(price) for price in prices):
                return (float('nan'), float('nan'), float('nan'), float('nan'))

            # 计算中轨（移动平均）
            middle = sum(prices) / period

            # 计算标准差
            variance = sum((price - middle) ** 2 for price in prices) / period
            std_dev = variance ** 0.5

            # 计算上轨和下轨
            upper = middle + (std_dev * std_multiplier)
            lower = middle - (std_dev * std_multiplier)

            # 计算当前价格的相对位置（使用最后一个价格）
            current_price = prices[-1]
            band_width = upper - lower
            if band_width > 0:
                position = (current_price - lower) / band_width
            else:
                position = 0.5  # 如果带宽为0，位置设为中间

            return (upper, middle, lower, position)

        except Exception:
            return (float('nan'), float('nan'), float('nan'), float('nan'))

    @staticmethod
    def cal_matrix(period: int, std_multiplier: float, matrix_data: pd.DataFrame) -> pd.DataFrame:
        """
        布林带的Matrix回测计算 - 静态方法
        
        Args:
            period: 移动平均和标准差计算周期
            std_multiplier: 标准差倍数
            matrix_data: 矩阵数据
            
        Returns:
            pd.DataFrame: 布林带计算结果
        """
        try:
            if period <= 0 or std_multiplier <= 0:
                return BaseIndicator.cal_matrix(matrix_data)
                
            if "code" in matrix_data.columns:
                # 长格式：按股票分组计算
                def calc_boll_for_group(group):
                    group = group.sort_values("timestamp")

                    close_prices = group["close"]
                    
                    # 计算移动平均和标准差
                    middle = close_prices.rolling(period).mean()
                    std = close_prices.rolling(period).std()

                    # 计算上下轨
                    upper = middle + (std * std_multiplier)
                    lower = middle - (std * std_multiplier)

                    # 添加标准化结果列
                    group["bb_middle"] = middle
                    group["bb_upper"] = upper
                    group["bb_lower"] = lower

                    # 计算价格相对位置
                    band_width = upper - lower
                    group["bb_position"] = np.where(band_width > 0, (close_prices - lower) / band_width, 0.5)

                    return group

                result = matrix_data.groupby("code").apply(calc_boll_for_group).reset_index(drop=True)
                return result
            else:
                # 宽格式：对整个矩阵计算布林带（只返回中轨）
                return matrix_data.rolling(window=period).mean()
                
        except Exception:
            return BaseIndicator.cal_matrix(matrix_data)


class BollingerBandsSignal(BaseIndicator):
    """
    布林带交易信号指标 - 纯静态计算

    生成基于布林带的交易信号：
    - 价格突破上轨：可能的卖出信号
    - 价格突破下轨：可能的买入信号
    - 价格回归中轨：信号确认
    
    返回格式: DataFrame['timestamp', 'boll_signal']
    """

    @staticmethod
    def cal(period: int, std_multiplier: float, data: pd.DataFrame) -> pd.DataFrame:
        """
        计算布林带交易信号

        Args:
            period: 布林带计算周期
            std_multiplier: 标准差倍数
            data: DataFrame，必须包含 'close' 和 'timestamp' 列

        Returns:
            DataFrame: 包含 'timestamp' 和 'boll_signal' 列，信号值: 1 (买入), -1 (卖出), 0 (无信号)
        """
        try:
            validated_data, error = BollingerBandsSignal._validate_and_prepare(
                data, ["close", "timestamp"], period
            )
            if error:
                return BollingerBandsSignal._handle_error(data, ["boll_signal"])

            df = validated_data.sort_values("timestamp").reset_index(drop=True)

            # 计算布林带
            middle = df["close"].rolling(window=period).mean()
            std = df["close"].rolling(window=period).std()
            upper = middle + (std * std_multiplier)
            lower = middle - (std * std_multiplier)

            # 生成信号
            signals = np.zeros(len(df))

            for i in range(1, len(df)):
                current_price = df.iloc[i]["close"]
                prev_price = df.iloc[i - 1]["close"]

                current_upper = upper.iloc[i]
                current_lower = lower.iloc[i]
                prev_upper = upper.iloc[i - 1]
                prev_lower = lower.iloc[i - 1]

                # 突破上轨：卖出信号
                if prev_price <= prev_upper and current_price > current_upper and not pd.isna(current_upper):
                    signals[i] = -1

                # 突破下轨：买入信号
                elif prev_price >= prev_lower and current_price < current_lower and not pd.isna(current_lower):
                    signals[i] = 1

            return BollingerBandsSignal._create_result_df(
                df,
                boll_signal=pd.Series(signals, index=df.index)
            )
            
        except Exception:
            return BollingerBandsSignal._handle_error(data, ["boll_signal"])

    @staticmethod
    def cal_matrix(period: int, std_multiplier: float, matrix_data: pd.DataFrame) -> pd.DataFrame:
        """
        布林带信号的Matrix计算 - 静态方法
        
        Args:
            period: 布林带计算周期
            std_multiplier: 标准差倍数
            matrix_data: 矩阵数据
            
        Returns:
            pd.DataFrame: 布林带信号计算结果
        """
        try:
            if "code" in matrix_data.columns:
                # 长格式：按股票分组计算信号
                def calc_signal_for_group(group):
                    group = group.sort_values("timestamp")

                    if len(group) < period:
                        group['boll_signal'] = 0
                        return group

                    # 计算布林带
                    middle = group["close"].rolling(window=period).mean()
                    std = group["close"].rolling(window=period).std()
                    upper = middle + (std * std_multiplier)
                    lower = middle - (std * std_multiplier)

                    # 生成信号
                    signals = np.zeros(len(group))

                    for i in range(1, len(group)):
                        current_price = group.iloc[i]["close"]
                        prev_price = group.iloc[i - 1]["close"]

                        current_upper = upper.iloc[i]
                        current_lower = lower.iloc[i]
                        prev_upper = upper.iloc[i - 1]
                        prev_lower = lower.iloc[i - 1]

                        # 突破上轨：卖出信号
                        if prev_price <= prev_upper and current_price > current_upper and not pd.isna(current_upper):
                            signals[i] = -1

                        # 突破下轨：买入信号
                        elif prev_price >= prev_lower and current_price < current_lower and not pd.isna(current_lower):
                            signals[i] = 1

                    group['boll_signal'] = signals
                    return group

                result = matrix_data.groupby("code").apply(calc_signal_for_group).reset_index(drop=True)
                return result
            else:
                # 宽格式：暂时返回零信号矩阵
                return pd.DataFrame(0, index=matrix_data.index, columns=matrix_data.columns)
                
        except Exception:
            return BaseIndicator.cal_matrix(matrix_data)
