# Upstream: External Applications
# Downstream: Trading Strategies, Analysis Tools
# Role: MLAlphaFactors ML alpha因子提供机器学习alpha因子计算支持交易系统功能支持相关功能






"""
Alpha因子计算模块

实现常用的量化因子，参考qlib的Alpha158和Alpha360因子集。
提供技术指标、价量因子、波动率因子等。
"""

import numpy as np
import pandas as pd
from typing import Dict, List, Optional, Union, Tuple
from datetime import datetime, timedelta

try:
    import talib
    TALIB_AVAILABLE = True
except ImportError:
    TALIB_AVAILABLE = False

from ginkgo.libs import GLOG


class AlphaFactors:
    """
    Alpha因子计算器
    
    实现常用的量化因子计算，包括：
    - 技术指标因子
    - 价量关系因子  
    - 波动率因子
    - 动量因子
    - 均值回归因子
    """
    
    def __init__(self, use_talib: bool = True):
        """
        初始化Alpha因子计算器
        
        Args:
            use_talib: 是否使用TA-Lib库加速计算
        """
        self.use_talib = use_talib and TALIB_AVAILABLE
        
        if not self.use_talib and TALIB_AVAILABLE:
            GLOG.WARN("TA-Lib可用但未启用，建议使用TA-Lib提高计算效率")
        elif self.use_talib and not TALIB_AVAILABLE:
            GLOG.WARN("TA-Lib未安装，使用纯pandas实现")
            self.use_talib = False
        
        GLOG.INFO(f"初始化Alpha因子计算器，TA-Lib: {self.use_talib}")
    
    def calculate_basic_factors(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        计算基础因子
        
        Args:
            df: OHLCV数据，需包含open, high, low, close, volume列
            
        Returns:
            pd.DataFrame: 包含基础因子的数据
        """
        try:
            result = df.copy()
            
            # 验证必需列
            required_cols = ['open', 'high', 'low', 'close', 'volume']
            missing_cols = [col for col in required_cols if col not in df.columns]
            if missing_cols:
                raise ValueError(f"缺少必需列: {missing_cols}")
            
            # 价格因子
            result['price_range'] = (result['high'] - result['low']) / result['close']
            result['price_gap'] = (result['open'] - result['close'].shift(1)) / result['close'].shift(1)
            result['price_position'] = (result['close'] - result['low']) / (result['high'] - result['low'] + 1e-8)
            
            # 收益率因子
            result['returns_1d'] = result['close'].pct_change(1)
            result['returns_5d'] = result['close'].pct_change(5)
            result['returns_20d'] = result['close'].pct_change(20)
            
            # 成交量因子
            result['volume_ratio'] = result['volume'] / result['volume'].rolling(20).mean()
            result['amount_ratio'] = (result['close'] * result['volume']) / (result['close'] * result['volume']).rolling(20).mean()
            
            # 价量关系
            result['price_volume_corr'] = result['close'].rolling(20).corr(result['volume'])
            result['volume_price_trend'] = (result['volume'] / result['volume'].rolling(5).mean()) * np.sign(result['returns_1d'])
            
            GLOG.DEBUG("基础因子计算完成")
            
            return result
            
        except Exception as e:
            GLOG.ERROR(f"基础因子计算失败: {e}")
            raise e
    
    def calculate_technical_indicators(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        计算技术指标因子
        
        Args:
            df: OHLCV数据
            
        Returns:
            pd.DataFrame: 包含技术指标的数据
        """
        try:
            result = df.copy()
            
            # 移动平均线
            periods = [5, 10, 20, 60]
            for period in periods:
                if self.use_talib:
                    result[f'ma_{period}'] = talib.SMA(result['close'].values, timeperiod=period)
                    result[f'ema_{period}'] = talib.EMA(result['close'].values, timeperiod=period)
                else:
                    result[f'ma_{period}'] = result['close'].rolling(period).mean()
                    result[f'ema_{period}'] = result['close'].ewm(span=period).mean()
                
                # 价格相对位置
                result[f'close_ma_ratio_{period}'] = result['close'] / result[f'ma_{period}']
                result[f'close_ema_ratio_{period}'] = result['close'] / result[f'ema_{period}']
            
            # RSI
            if self.use_talib:
                result['rsi_14'] = talib.RSI(result['close'].values, timeperiod=14)
            else:
                result['rsi_14'] = self._calculate_rsi(result['close'], 14)
            
            # MACD
            if self.use_talib:
                macd, signal, histogram = talib.MACD(result['close'].values)
                result['macd'] = macd
                result['macd_signal'] = signal
                result['macd_histogram'] = histogram
            else:
                macd_data = self._calculate_macd(result['close'])
                result['macd'] = macd_data['macd']
                result['macd_signal'] = macd_data['signal']
                result['macd_histogram'] = macd_data['histogram']
            
            # 布林带
            if self.use_talib:
                bb_upper, bb_middle, bb_lower = talib.BBANDS(result['close'].values)
                result['bb_upper'] = bb_upper
                result['bb_middle'] = bb_middle
                result['bb_lower'] = bb_lower
            else:
                bb_data = self._calculate_bollinger_bands(result['close'])
                result['bb_upper'] = bb_data['upper']
                result['bb_middle'] = bb_data['middle']
                result['bb_lower'] = bb_data['lower']
            
            result['bb_position'] = (result['close'] - result['bb_lower']) / (result['bb_upper'] - result['bb_lower'] + 1e-8)
            result['bb_width'] = (result['bb_upper'] - result['bb_lower']) / result['bb_middle']
            
            # KDJ
            kdj_data = self._calculate_kdj(result)
            result['kdj_k'] = kdj_data['k']
            result['kdj_d'] = kdj_data['d']
            result['kdj_j'] = kdj_data['j']
            
            GLOG.DEBUG("技术指标计算完成")
            
            return result
            
        except Exception as e:
            GLOG.ERROR(f"技术指标计算失败: {e}")
            raise e
    
    def calculate_volatility_factors(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        计算波动率因子
        
        Args:
            df: OHLCV数据
            
        Returns:
            pd.DataFrame: 包含波动率因子的数据
        """
        try:
            result = df.copy()
            
            # 计算收益率
            returns = result['close'].pct_change()
            
            # 历史波动率
            periods = [5, 10, 20, 60]
            for period in periods:
                result[f'volatility_{period}'] = returns.rolling(period).std() * np.sqrt(252)
                result[f'realized_vol_{period}'] = returns.rolling(period).apply(lambda x: np.sqrt(np.sum(x**2) * 252))
            
            # 真实波动幅度(ATR)
            if self.use_talib:
                result['atr_14'] = talib.ATR(result['high'].values, result['low'].values, result['close'].values, timeperiod=14)
            else:
                result['atr_14'] = self._calculate_atr(result)
            
            result['atr_ratio'] = result['atr_14'] / result['close']
            
            # Garman-Klass波动率估计
            result['gk_volatility'] = np.sqrt(
                0.5 * np.log(result['high'] / result['low']) ** 2 -
                (2 * np.log(2) - 1) * np.log(result['close'] / result['open']) ** 2
            ) * np.sqrt(252)
            
            # 价格跳跃
            result['price_jump'] = np.abs(result['open'] / result['close'].shift(1) - 1)
            result['jump_indicator'] = (result['price_jump'] > result['volatility_20'] / np.sqrt(252)).astype(int)
            
            # 波动率趋势
            result['vol_trend'] = result['volatility_5'] / result['volatility_20']
            result['vol_mean_reversion'] = (result['volatility_5'] - result['volatility_20']) / result['volatility_20']
            
            GLOG.DEBUG("波动率因子计算完成")
            
            return result
            
        except Exception as e:
            GLOG.ERROR(f"波动率因子计算失败: {e}")
            raise e
    
    def calculate_momentum_factors(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        计算动量因子
        
        Args:
            df: OHLCV数据
            
        Returns:
            pd.DataFrame: 包含动量因子的数据
        """
        try:
            result = df.copy()
            
            # 价格动量
            periods = [1, 3, 5, 10, 20, 60]
            for period in periods:
                result[f'momentum_{period}'] = result['close'] / result['close'].shift(period) - 1
                result[f'log_momentum_{period}'] = np.log(result['close'] / result['close'].shift(period))
            
            # 动量强度
            result['momentum_strength_20'] = result['momentum_20'] / result['momentum_20'].rolling(60).std()
            
            # 趋势强度
            result['trend_strength'] = (result['close'] > result['close'].shift(20)).rolling(60).mean()
            
            # 相对强弱
            result['relative_strength'] = result['close'] / result['close'].rolling(252).mean()
            
            # 价格加速度
            result['price_acceleration'] = (result['momentum_5'] - result['momentum_20']) / 20
            
            # 动量因子组合
            result['momentum_composite'] = (
                result['momentum_5'] * 0.4 +
                result['momentum_20'] * 0.4 +
                result['momentum_60'] * 0.2
            )
            
            GLOG.DEBUG("动量因子计算完成")
            
            return result
            
        except Exception as e:
            GLOG.ERROR(f"动量因子计算失败: {e}")
            raise e
    
    def calculate_mean_reversion_factors(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        计算均值回归因子
        
        Args:
            df: OHLCV数据
            
        Returns:
            pd.DataFrame: 包含均值回归因子的数据
        """
        try:
            result = df.copy()
            
            # 价格偏离
            periods = [5, 10, 20, 60]
            for period in periods:
                ma = result['close'].rolling(period).mean()
                result[f'price_deviation_{period}'] = (result['close'] - ma) / ma
                result[f'price_zscore_{period}'] = (result['close'] - ma) / result['close'].rolling(period).std()
            
            # 布林带位置（均值回归信号）
            bb_middle = result['close'].rolling(20).mean()
            bb_std = result['close'].rolling(20).std()
            result['bb_zscore'] = (result['close'] - bb_middle) / bb_std
            result['mean_reversion_signal'] = -result['bb_zscore']  # 反转信号
            
            # 超买超卖
            result['oversold'] = (result['rsi_14'] < 30).astype(int)
            result['overbought'] = (result['rsi_14'] > 70).astype(int)
            
            # 价格回归速度
            result['reversion_speed'] = result['price_deviation_20'].rolling(5).apply(
                lambda x: -np.polyfit(range(len(x)), x, 1)[0] if len(x) >= 2 else 0
            )
            
            GLOG.DEBUG("均值回归因子计算完成")
            
            return result
            
        except Exception as e:
            GLOG.ERROR(f"均值回归因子计算失败: {e}")
            raise e
    
    def calculate_all_factors(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        计算所有因子
        
        Args:
            df: OHLCV数据
            
        Returns:
            pd.DataFrame: 包含所有因子的数据
        """
        try:
            GLOG.INFO("开始计算所有Alpha因子")
            
            result = df.copy()
            
            # 按顺序计算各类因子
            result = self.calculate_basic_factors(result)
            result = self.calculate_technical_indicators(result)
            result = self.calculate_volatility_factors(result)
            result = self.calculate_momentum_factors(result)
            result = self.calculate_mean_reversion_factors(result)
            
            # 清理无穷值和极值
            result = result.replace([np.inf, -np.inf], np.nan)
            
            # 计算因子数量
            original_cols = len(df.columns)
            new_cols = len(result.columns)
            factor_count = new_cols - original_cols
            
            GLOG.INFO(f"因子计算完成，新增因子数: {factor_count}")
            
            return result
            
        except Exception as e:
            GLOG.ERROR(f"因子计算失败: {e}")
            raise e
    
    def _calculate_rsi(self, prices: pd.Series, period: int = 14) -> pd.Series:
        """计算RSI指标"""
        delta = prices.diff()
        gain = delta.where(delta > 0, 0)
        loss = -delta.where(delta < 0, 0)
        
        avg_gain = gain.rolling(window=period).mean()
        avg_loss = loss.rolling(window=period).mean()
        
        rs = avg_gain / avg_loss
        rsi = 100 - (100 / (1 + rs))
        
        return rsi
    
    def _calculate_macd(self, prices: pd.Series, fast=12, slow=26, signal=9) -> Dict[str, pd.Series]:
        """计算MACD指标"""
        ema_fast = prices.ewm(span=fast).mean()
        ema_slow = prices.ewm(span=slow).mean()
        
        macd = ema_fast - ema_slow
        signal_line = macd.ewm(span=signal).mean()
        histogram = macd - signal_line
        
        return {
            'macd': macd,
            'signal': signal_line,
            'histogram': histogram
        }
    
    def _calculate_bollinger_bands(self, prices: pd.Series, period: int = 20, std_dev: int = 2) -> Dict[str, pd.Series]:
        """计算布林带"""
        middle = prices.rolling(period).mean()
        std = prices.rolling(period).std()
        
        upper = middle + (std * std_dev)
        lower = middle - (std * std_dev)
        
        return {
            'upper': upper,
            'middle': middle,
            'lower': lower
        }
    
    def _calculate_kdj(self, df: pd.DataFrame, period: int = 9) -> Dict[str, pd.Series]:
        """计算KDJ指标"""
        lowest_low = df['low'].rolling(period).min()
        highest_high = df['high'].rolling(period).max()
        
        rsv = (df['close'] - lowest_low) / (highest_high - lowest_low + 1e-8) * 100
        
        k = rsv.ewm(alpha=1/3).mean()
        d = k.ewm(alpha=1/3).mean()
        j = 3 * k - 2 * d
        
        return {'k': k, 'd': d, 'j': j}
    
    def _calculate_atr(self, df: pd.DataFrame, period: int = 14) -> pd.Series:
        """计算ATR指标"""
        high_low = df['high'] - df['low']
        high_close = np.abs(df['high'] - df['close'].shift(1))
        low_close = np.abs(df['low'] - df['close'].shift(1))
        
        true_range = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
        atr = true_range.rolling(period).mean()
        
        return atr
    
    def get_factor_groups(self) -> Dict[str, List[str]]:
        """获取因子分组"""
        return {
            'basic': [
                'price_range', 'price_gap', 'price_position', 'returns_1d', 'returns_5d', 'returns_20d',
                'volume_ratio', 'amount_ratio', 'price_volume_corr', 'volume_price_trend'
            ],
            'technical': [
                'ma_5', 'ma_10', 'ma_20', 'ma_60', 'ema_5', 'ema_10', 'ema_20', 'ema_60',
                'rsi_14', 'macd', 'macd_signal', 'macd_histogram', 'bb_position', 'bb_width',
                'kdj_k', 'kdj_d', 'kdj_j'
            ],
            'volatility': [
                'volatility_5', 'volatility_10', 'volatility_20', 'volatility_60',
                'atr_14', 'atr_ratio', 'gk_volatility', 'price_jump', 'vol_trend'
            ],
            'momentum': [
                'momentum_1', 'momentum_3', 'momentum_5', 'momentum_10', 'momentum_20', 'momentum_60',
                'momentum_strength_20', 'trend_strength', 'relative_strength', 'momentum_composite'
            ],
            'mean_reversion': [
                'price_deviation_5', 'price_deviation_10', 'price_deviation_20', 'price_deviation_60',
                'bb_zscore', 'mean_reversion_signal', 'oversold', 'overbought', 'reversion_speed'
            ]
        }