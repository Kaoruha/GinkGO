"""
Technical Operators - 技术指标操作符

提供常用技术指标的操作符实现，这些是对现有indicators模块的封装。
"""

import pandas as pd
import numpy as np
from ..registry import register_operator
from ginkgo.libs import GLOG


@register_operator("RSI", "Relative Strength Index", min_args=2, max_args=2)
def rsi_operator(data: pd.DataFrame, close_series: pd.Series, period: pd.Series) -> pd.Series:
    """RSI相对强弱指数"""
    try:
        period_value = int(period.iloc[0]) if len(period) > 0 else 14
        if period_value <= 0:
            raise ValueError(f"Period must be positive, got {period_value}")
        
        # 计算价格变化
        delta = close_series.diff()
        
        # 分离上涨和下跌
        gain = delta.where(delta > 0, 0)
        loss = -delta.where(delta < 0, 0)
        
        # 计算平均收益和损失
        avg_gain = gain.rolling(window=period_value, min_periods=1).mean()
        avg_loss = loss.rolling(window=period_value, min_periods=1).mean()
        
        # 计算RSI
        with np.errstate(divide='ignore', invalid='ignore'):
            rs = avg_gain / avg_loss
            rsi = 100 - (100 / (1 + rs))
            return rsi.replace([np.inf, -np.inf], np.nan)
            
    except Exception as e:
        GLOG.ERROR(f"RSI operator failed: {e}")
        return pd.Series([np.nan] * len(close_series), index=close_series.index)


@register_operator("MACD", "Moving Average Convergence Divergence", min_args=1, max_args=4)
def macd_operator(data: pd.DataFrame, close_series: pd.Series, 
                 fast_period: pd.Series = None, slow_period: pd.Series = None, 
                 signal_period: pd.Series = None) -> pd.Series:
    """MACD指标"""
    try:
        fast = int(fast_period.iloc[0]) if fast_period is not None and len(fast_period) > 0 else 12
        slow = int(slow_period.iloc[0]) if slow_period is not None and len(slow_period) > 0 else 26
        signal = int(signal_period.iloc[0]) if signal_period is not None and len(signal_period) > 0 else 9
        
        if fast <= 0 or slow <= 0 or signal <= 0:
            raise ValueError("All periods must be positive")
        
        # 计算EMA
        ema_fast = close_series.ewm(span=fast).mean()
        ema_slow = close_series.ewm(span=slow).mean()
        
        # MACD线
        macd_line = ema_fast - ema_slow
        
        # 信号线
        signal_line = macd_line.ewm(span=signal).mean()
        
        # 返回MACD线（可以扩展为返回多个值）
        return macd_line
        
    except Exception as e:
        GLOG.ERROR(f"MACD operator failed: {e}")
        return pd.Series([np.nan] * len(close_series), index=close_series.index)


@register_operator("BB_upper", "Bollinger Bands Upper", min_args=2, max_args=3)
def bb_upper_operator(data: pd.DataFrame, close_series: pd.Series, period: pd.Series, 
                     std_dev: pd.Series = None) -> pd.Series:
    """布林带上轨"""
    try:
        period_value = int(period.iloc[0]) if len(period) > 0 else 20
        std_multiplier = float(std_dev.iloc[0]) if std_dev is not None and len(std_dev) > 0 else 2.0
        
        if period_value <= 0:
            raise ValueError(f"Period must be positive, got {period_value}")
        
        # 计算移动平均和标准差
        sma = close_series.rolling(window=period_value, min_periods=1).mean()
        std = close_series.rolling(window=period_value, min_periods=1).std()
        
        # 上轨
        upper_band = sma + (std * std_multiplier)
        return upper_band
        
    except Exception as e:
        GLOG.ERROR(f"BB_upper operator failed: {e}")
        return pd.Series([np.nan] * len(close_series), index=close_series.index)


@register_operator("BB_lower", "Bollinger Bands Lower", min_args=2, max_args=3)
def bb_lower_operator(data: pd.DataFrame, close_series: pd.Series, period: pd.Series, 
                     std_dev: pd.Series = None) -> pd.Series:
    """布林带下轨"""
    try:
        period_value = int(period.iloc[0]) if len(period) > 0 else 20
        std_multiplier = float(std_dev.iloc[0]) if std_dev is not None and len(std_dev) > 0 else 2.0
        
        if period_value <= 0:
            raise ValueError(f"Period must be positive, got {period_value}")
        
        # 计算移动平均和标准差
        sma = close_series.rolling(window=period_value, min_periods=1).mean()
        std = close_series.rolling(window=period_value, min_periods=1).std()
        
        # 下轨
        lower_band = sma - (std * std_multiplier)
        return lower_band
        
    except Exception as e:
        GLOG.ERROR(f"BB_lower operator failed: {e}")
        return pd.Series([np.nan] * len(close_series), index=close_series.index)


@register_operator("ATR", "Average True Range", min_args=4, max_args=4)
def atr_operator(data: pd.DataFrame, high_series: pd.Series, low_series: pd.Series, 
                close_series: pd.Series, period: pd.Series) -> pd.Series:
    """平均真实范围"""
    try:
        period_value = int(period.iloc[0]) if len(period) > 0 else 14
        if period_value <= 0:
            raise ValueError(f"Period must be positive, got {period_value}")
        
        # 前一日收盘价
        prev_close = close_series.shift(1)
        
        # 计算真实范围的三个候选值
        tr1 = high_series - low_series
        tr2 = (high_series - prev_close).abs()
        tr3 = (low_series - prev_close).abs()
        
        # 真实范围是三者的最大值
        true_range = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
        
        # ATR是真实范围的移动平均
        atr = true_range.rolling(window=period_value, min_periods=1).mean()
        return atr
        
    except Exception as e:
        GLOG.ERROR(f"ATR operator failed: {e}")
        return pd.Series([np.nan] * len(high_series), index=high_series.index)


@register_operator("Stoch", "Stochastic Oscillator", min_args=4, max_args=4)
def stoch_operator(data: pd.DataFrame, high_series: pd.Series, low_series: pd.Series, 
                  close_series: pd.Series, period: pd.Series) -> pd.Series:
    """随机振荡器%K"""
    try:
        period_value = int(period.iloc[0]) if len(period) > 0 else 14
        if period_value <= 0:
            raise ValueError(f"Period must be positive, got {period_value}")
        
        # 计算n期内的最高价和最低价
        lowest_low = low_series.rolling(window=period_value, min_periods=1).min()
        highest_high = high_series.rolling(window=period_value, min_periods=1).max()
        
        # 计算%K
        with np.errstate(divide='ignore', invalid='ignore'):
            k_percent = 100 * (close_series - lowest_low) / (highest_high - lowest_low)
            return k_percent.replace([np.inf, -np.inf], np.nan)
            
    except Exception as e:
        GLOG.ERROR(f"Stoch operator failed: {e}")
        return pd.Series([np.nan] * len(high_series), index=high_series.index)


@register_operator("Williams_R", "Williams %R", min_args=4, max_args=4)
def williams_r_operator(data: pd.DataFrame, high_series: pd.Series, low_series: pd.Series, 
                       close_series: pd.Series, period: pd.Series) -> pd.Series:
    """威廉指标%R"""
    try:
        period_value = int(period.iloc[0]) if len(period) > 0 else 14
        if period_value <= 0:
            raise ValueError(f"Period must be positive, got {period_value}")
        
        # 计算n期内的最高价和最低价
        highest_high = high_series.rolling(window=period_value, min_periods=1).max()
        lowest_low = low_series.rolling(window=period_value, min_periods=1).min()
        
        # 计算Williams %R
        with np.errstate(divide='ignore', invalid='ignore'):
            williams_r = -100 * (highest_high - close_series) / (highest_high - lowest_low)
            return williams_r.replace([np.inf, -np.inf], np.nan)
            
    except Exception as e:
        GLOG.ERROR(f"Williams_R operator failed: {e}")
        return pd.Series([np.nan] * len(high_series), index=high_series.index)


@register_operator("CCI", "Commodity Channel Index", min_args=4, max_args=4)
def cci_operator(data: pd.DataFrame, high_series: pd.Series, low_series: pd.Series, 
                close_series: pd.Series, period: pd.Series) -> pd.Series:
    """商品路径指标"""
    try:
        period_value = int(period.iloc[0]) if len(period) > 0 else 20
        if period_value <= 0:
            raise ValueError(f"Period must be positive, got {period_value}")
        
        # 典型价格
        typical_price = (high_series + low_series + close_series) / 3
        
        # 移动平均
        sma_tp = typical_price.rolling(window=period_value, min_periods=1).mean()
        
        # 平均偏差
        mean_deviation = (typical_price - sma_tp).abs().rolling(window=period_value, min_periods=1).mean()
        
        # CCI计算
        with np.errstate(divide='ignore', invalid='ignore'):
            cci = (typical_price - sma_tp) / (0.015 * mean_deviation)
            return cci.replace([np.inf, -np.inf], np.nan)
            
    except Exception as e:
        GLOG.ERROR(f"CCI operator failed: {e}")
        return pd.Series([np.nan] * len(high_series), index=high_series.index)


@register_operator("PinBar", "Pin Bar Pattern Detection", min_args=5, max_args=5)
def pinbar_operator(data: pd.DataFrame, open_series: pd.Series, high_series: pd.Series,
                   low_series: pd.Series, close_series: pd.Series, direction: pd.Series) -> pd.Series:
    """PinBar形态检测"""
    try:
        dir_value = int(direction.iloc[0]) if len(direction) > 0 else 0
        
        result = []
        for i in range(len(open_series)):
            open_price = open_series.iloc[i]
            high_price = high_series.iloc[i]
            low_price = low_series.iloc[i]
            close_price = close_series.iloc[i]
            
            if pd.isna(open_price) or pd.isna(high_price) or pd.isna(low_price) or pd.isna(close_price):
                result.append(0)
                continue
            
            if open_price == 0:
                result.append(0)
                continue
                
            # 计算影线长度
            up_shadow = high_price - max(open_price, close_price)
            down_shadow = min(open_price, close_price) - low_price
            body_size = abs(close_price - open_price)
            total_range = high_price - low_price
            
            # 实体变化幅度检查
            chg_pct = body_size / open_price
            if chg_pct > 0.03:  # 实体过大
                result.append(0)
                continue
            
            if total_range == 0:
                result.append(0)
                continue
                
            # 影线比例检查
            if down_shadow == 0:
                result.append(0)
                continue
                
            shadow_ratio = up_shadow / down_shadow if down_shadow != 0 else float('inf')
            if 0.6 < shadow_ratio < 1.4:  # 上下影线接近
                result.append(0)
                continue
            
            # 主要影线检查
            main_shadow = max(up_shadow, down_shadow)
            if main_shadow > total_range * 2 / 3:
                if dir_value == 1:  # 只检测看涨PinBar
                    result.append(1 if down_shadow > up_shadow else 0)
                elif dir_value == -1:  # 只检测看跌PinBar
                    result.append(-1 if up_shadow > down_shadow else 0)
                else:  # 检测任意PinBar
                    result.append(1 if down_shadow > up_shadow else (-1 if up_shadow > down_shadow else 0))
            else:
                result.append(0)
        
        return pd.Series(result, index=open_series.index)
        
    except Exception as e:
        GLOG.ERROR(f"PinBar operator failed: {e}")
        return pd.Series([0] * len(open_series), index=open_series.index)


@register_operator("Gap", "Gap Pattern Detection", min_args=5, max_args=5)
def gap_operator(data: pd.DataFrame, open_series: pd.Series, high_series: pd.Series,
                low_series: pd.Series, close_series: pd.Series, direction: pd.Series) -> pd.Series:
    """跳空形态检测"""
    try:
        dir_value = int(direction.iloc[0]) if len(direction) > 0 else 0
        filter_ratio = 0.5  # 过滤比例
        
        result = []
        for i in range(len(open_series)):
            if i == 0:
                result.append(0)
                continue
                
            # 当前K线数据
            curr_open = open_series.iloc[i]
            curr_high = high_series.iloc[i]
            curr_low = low_series.iloc[i]
            curr_close = close_series.iloc[i]
            
            # 前一根K线数据
            prev_high = high_series.iloc[i-1]
            prev_low = low_series.iloc[i-1]
            
            if any(pd.isna(x) for x in [curr_open, curr_high, curr_low, curr_close, prev_high, prev_low]):
                result.append(0)
                continue
            
            # 计算前一根K线的范围
            prev_range = prev_high - prev_low
            if prev_range <= 0:
                result.append(0)
                continue
            
            # 当前K线的实体范围
            curr_top = max(curr_open, curr_close)
            curr_bottom = min(curr_open, curr_close)
            
            # 检测跳空
            if curr_bottom > prev_high:  # 向上跳空
                gap = curr_bottom - prev_high
                gap_value = gap if gap > prev_range * filter_ratio else 0
                if dir_value == 1:  # 只检测向上跳空
                    result.append(gap_value)
                elif dir_value == -1:  # 只检测向下跳空
                    result.append(0)
                else:  # 检测任意跳空
                    result.append(gap_value)
            elif curr_top < prev_low:  # 向下跳空
                gap = curr_top - prev_low  # 负值
                gap_value = gap if abs(gap) > prev_range * filter_ratio else 0
                if dir_value == -1:  # 只检测向下跳空
                    result.append(gap_value)
                elif dir_value == 1:  # 只检测向上跳空
                    result.append(0)
                else:  # 检测任意跳空
                    result.append(gap_value)
            else:
                result.append(0)
        
        return pd.Series(result, index=open_series.index)
        
    except Exception as e:
        GLOG.ERROR(f"Gap operator failed: {e}")
        return pd.Series([0] * len(open_series), index=open_series.index)


@register_operator("InflectionPoint", "Inflection Point Detection", min_args=2, max_args=2)
def inflection_point_operator(data: pd.DataFrame, close_series: pd.Series, window: pd.Series) -> pd.Series:
    """拐点检测"""
    try:
        window_size = int(window.iloc[0]) if len(window) > 0 else 4
        if window_size <= 0:
            raise ValueError(f"Window size must be positive, got {window_size}")
        
        result = []
        for i in range(len(close_series)):
            if i < window_size or i >= len(close_series) - window_size:
                result.append(0)
                continue
            
            # 获取窗口内的价格数据
            window_prices = close_series.iloc[i-window_size:i+window_size+1].values
            center_idx = window_size
            center_price = window_prices[center_idx]
            
            if pd.isna(center_price):
                result.append(0)
                continue
            
            # 检查是否为局部极值
            is_peak = all(center_price >= price or pd.isna(price) 
                         for j, price in enumerate(window_prices) if j != center_idx)
            is_valley = all(center_price <= price or pd.isna(price) 
                           for j, price in enumerate(window_prices) if j != center_idx)
            
            if is_peak and not is_valley:
                result.append(1)  # 峰值
            elif is_valley and not is_peak:
                result.append(-1)  # 谷值
            else:
                result.append(0)  # 非拐点
        
        return pd.Series(result, index=close_series.index)
        
    except Exception as e:
        GLOG.ERROR(f"InflectionPoint operator failed: {e}")
        return pd.Series([0] * len(close_series), index=close_series.index)


@register_operator("GoldenSection", "Golden Section Levels", min_args=3, max_args=3)
def golden_section_operator(data: pd.DataFrame, high_series: pd.Series, low_series: pd.Series, 
                           ratio: pd.Series) -> pd.Series:
    """黄金分割位计算"""
    try:
        ratio_value = float(ratio.iloc[0]) if len(ratio) > 0 else 0.618
        if not 0 < ratio_value < 1:
            raise ValueError(f"Ratio must be between 0 and 1, got {ratio_value}")
        
        # 计算20期高低点
        rolling_high = high_series.rolling(window=20, min_periods=1).max()
        rolling_low = low_series.rolling(window=20, min_periods=1).min()
        
        # 计算黄金分割位
        golden_level = rolling_low + (rolling_high - rolling_low) * ratio_value
        
        return golden_level
        
    except Exception as e:
        GLOG.ERROR(f"GoldenSection operator failed: {e}")
        return pd.Series([np.nan] * len(high_series), index=high_series.index)


@register_operator("RSV", "Raw Stochastic Value", min_args=4, max_args=4)
def rsv_operator(data: pd.DataFrame, high_series: pd.Series, low_series: pd.Series, 
                close_series: pd.Series, window: pd.Series) -> pd.Series:
    """RSV未成熟随机值"""
    try:
        window_size = int(window.iloc[0]) if len(window) > 0 else 9
        if window_size <= 0:
            raise ValueError(f"Window size must be positive, got {window_size}")
        
        # 计算n期内的最高价和最低价
        lowest_low = low_series.rolling(window=window_size, min_periods=1).min()
        highest_high = high_series.rolling(window=window_size, min_periods=1).max()
        
        # 计算RSV = (收盘价-最低价)/(最高价-最低价) * 100
        with np.errstate(divide='ignore', invalid='ignore'):
            rsv = 100 * (close_series - lowest_low) / (highest_high - lowest_low)
            return rsv.replace([np.inf, -np.inf], np.nan)
            
    except Exception as e:
        GLOG.ERROR(f"RSV operator failed: {e}")
        return pd.Series([np.nan] * len(high_series), index=high_series.index)