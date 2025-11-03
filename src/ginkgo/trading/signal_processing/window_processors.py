"""
具体时间窗口处理器实现

该模块实现了不同时间粒度的窗口处理器，支持日线、小时线、分钟线等不同策略需求。
"""

from datetime import datetime, timedelta
from ginkgo.trading.time.clock import now as clock_now
from typing import List

from .batch_processor import TimeWindowBatchProcessor, WindowType, ProcessingMode
from ginkgo.trading.entities.signal import Signal


class DailyWindowProcessor(TimeWindowBatchProcessor):
    """
    日线窗口处理器
    
    适合基于日线数据的策略，兼容T+1交易机制。
    在回测模式下严格按天分组处理信号。
    """
    
    def __init__(self, **kwargs):
        # 设置日线处理器的默认配置
        kwargs.setdefault('window_type', WindowType.DAILY)
        kwargs.setdefault('processing_mode', ProcessingMode.BACKTEST)
        kwargs.setdefault('resource_optimization', True)
        kwargs.setdefault('priority_weighting', True)  # 日线策略通常需要优先级权重
        
        super().__init__(**kwargs)
        
    def get_window_start(self, timestamp: datetime) -> datetime:
        """
        获取日线窗口起始时间（当天00:00:00）
        
        Args:
            timestamp: 信号时间戳
            
        Returns:
            当天零点时间
        """
        return timestamp.replace(hour=0, minute=0, second=0, microsecond=0)
        
    def should_process_batch(self, window_start: datetime, signals: List[Signal]) -> bool:
        """
        判断是否应该处理日线批次
        
        回测模式：等到下一交易日开始处理（模拟T+1）
        实盘模式：收盘后或达到最大延迟时间处理
        混合模式：根据批次大小和延迟时间决定
        
        Args:
            window_start: 窗口起始时间
            signals: 该窗口内的信号列表
            
        Returns:
            是否应该处理该批次
        """
        current_time = clock_now()  # 与全局时钟对齐
        
        if self.processing_mode == ProcessingMode.BACKTEST:
            # 回测模式：严格等到下一交易日
            # 这里简化处理，实际应该考虑交易日历
            next_trading_day = window_start + timedelta(days=1)
            return current_time >= next_trading_day
            
        elif self.processing_mode == ProcessingMode.LIVE:
            # 实盘模式：收盘后或达到最大延迟时间
            market_close = window_start.replace(hour=15, minute=0)  # 假设15:00收盘
            max_delay_time = market_close + self.max_batch_delay
            
            # 如果当前时间超过收盘时间或最大延迟时间，则处理
            return current_time >= market_close or current_time >= max_delay_time
            
        elif self.processing_mode == ProcessingMode.HYBRID:
            # 混合模式：考虑批次大小和延迟时间
            batch_created_time = self._batch_timestamps.get(window_start, current_time)
            delay_exceeded = current_time >= batch_created_time + self.max_batch_delay
            size_threshold_met = len(signals) >= self.min_batch_size
            
            return delay_exceeded or size_threshold_met
            
        return len(signals) >= self.min_batch_size


class HourlyWindowProcessor(TimeWindowBatchProcessor):
    """
    小时窗口处理器
    
    适合日内策略，按小时分组处理信号。
    在实盘模式下提供相对较短的延迟。
    """
    
    def __init__(self, **kwargs):
        kwargs.setdefault('window_type', WindowType.HOURLY)
        kwargs.setdefault('processing_mode', ProcessingMode.LIVE)
        kwargs.setdefault('max_batch_delay', timedelta(minutes=5))  # 小时级策略5分钟延迟
        kwargs.setdefault('resource_optimization', True)
        
        super().__init__(**kwargs)
        
    def get_window_start(self, timestamp: datetime) -> datetime:
        """
        获取小时窗口起始时间（整点时间）
        
        Args:
            timestamp: 信号时间戳
            
        Returns:
            该小时的整点时间
        """
        return timestamp.replace(minute=0, second=0, microsecond=0)
        
    def should_process_batch(self, window_start: datetime, signals: List[Signal]) -> bool:
        """
        判断是否应该处理小时批次
        
        Args:
            window_start: 窗口起始时间
            signals: 该窗口内的信号列表
            
        Returns:
            是否应该处理该批次
        """
        current_time = clock_now()
        
        if self.processing_mode == ProcessingMode.BACKTEST:
            # 回测模式：等到下一小时
            next_hour = window_start + timedelta(hours=1)
            return current_time >= next_hour
            
        elif self.processing_mode == ProcessingMode.LIVE:
            # 实盘模式：小时结束后或达到延迟阈值
            hour_end = window_start + timedelta(hours=1)
            batch_created_time = self._batch_timestamps.get(window_start, current_time)
            max_delay_time = batch_created_time + self.max_batch_delay
            
            return current_time >= hour_end or current_time >= max_delay_time
            
        elif self.processing_mode == ProcessingMode.HYBRID:
            # 混合模式
            batch_created_time = self._batch_timestamps.get(window_start, current_time)
            delay_exceeded = current_time >= batch_created_time + self.max_batch_delay
            size_threshold_met = len(signals) >= self.min_batch_size
            
            return delay_exceeded or size_threshold_met
            
        return len(signals) >= self.min_batch_size


class MinuteWindowProcessor(TimeWindowBatchProcessor):
    """
    分钟窗口处理器
    
    适合高频策略，按分钟分组处理信号。
    在实盘模式下提供很短的延迟以满足高频需求。
    """
    
    def __init__(self, **kwargs):
        kwargs.setdefault('window_type', WindowType.MINUTELY)
        kwargs.setdefault('processing_mode', ProcessingMode.LIVE)
        kwargs.setdefault('max_batch_delay', timedelta(seconds=10))  # 高频策略10秒延迟
        kwargs.setdefault('min_batch_size', 1)  # 高频策略降低批次大小要求
        kwargs.setdefault('resource_optimization', True)
        kwargs.setdefault('priority_weighting', False)  # 高频策略通常不需要复杂优先级
        
        super().__init__(**kwargs)
        
    def get_window_start(self, timestamp: datetime) -> datetime:
        """
        获取分钟窗口起始时间（整分钟时间）
        
        Args:
            timestamp: 信号时间戳
            
        Returns:
            该分钟的起始时间
        """
        return timestamp.replace(second=0, microsecond=0)
        
    def should_process_batch(self, window_start: datetime, signals: List[Signal]) -> bool:
        """
        判断是否应该处理分钟批次
        
        Args:
            window_start: 窗口起始时间
            signals: 该窗口内的信号列表
            
        Returns:
            是否应该处理该批次
        """
        current_time = clock_now()
        
        if self.processing_mode == ProcessingMode.BACKTEST:
            # 回测模式：等到下一分钟
            next_minute = window_start + timedelta(minutes=1)
            return current_time >= next_minute
            
        elif self.processing_mode == ProcessingMode.LIVE:
            # 实盘模式：很短延迟后处理
            batch_created_time = self._batch_timestamps.get(window_start, current_time)
            delay_time = current_time - batch_created_time
            
            # 如果延迟超过阈值或者有足够信号，就处理
            return (delay_time >= self.max_batch_delay or 
                   len(signals) >= self.min_batch_size)
                   
        elif self.processing_mode == ProcessingMode.HYBRID:
            # 混合模式：快速响应
            batch_created_time = self._batch_timestamps.get(window_start, current_time)
            delay_exceeded = current_time >= batch_created_time + self.max_batch_delay
            
            return delay_exceeded or len(signals) >= self.min_batch_size
            
        return True  # 默认立即处理


class ImmediateProcessor(TimeWindowBatchProcessor):
    """
    立即处理器
    
    兼容现有的逐个信号处理模式，不进行批处理。
    主要用于向后兼容和特殊场景。
    """
    
    def __init__(self, **kwargs):
        kwargs.setdefault('window_type', WindowType.IMMEDIATE)
        kwargs.setdefault('processing_mode', ProcessingMode.LIVE)
        kwargs.setdefault('max_batch_delay', timedelta(seconds=0))
        kwargs.setdefault('min_batch_size', 1)
        kwargs.setdefault('resource_optimization', False)  # 立即处理通常不需要优化
        kwargs.setdefault('priority_weighting', False)
        
        super().__init__(**kwargs)
        
    def get_window_start(self, timestamp: datetime) -> datetime:
        """
        立即处理模式：每个信号都有独立的时间窗口
        
        Args:
            timestamp: 信号时间戳
            
        Returns:
            信号本身的时间戳
        """
        return timestamp
        
    def should_process_batch(self, window_start: datetime, signals: List[Signal]) -> bool:
        """
        立即处理模式：总是立即处理
        
        Args:
            window_start: 窗口起始时间（未使用）
            signals: 信号列表（未使用）
            
        Returns:
            总是返回True，立即处理
        """
        return True


class CustomWindowProcessor(TimeWindowBatchProcessor):
    """
    自定义窗口处理器
    
    提供灵活的自定义窗口定义，用户可以传入自定义的窗口计算函数。
    适合有特殊时间窗口需求的策略。
    """
    
    def __init__(self, 
                 window_calculator,
                 batch_trigger_func,
                 **kwargs):
        """
        初始化自定义窗口处理器
        
        Args:
            window_calculator: 窗口计算函数，接收timestamp返回window_start
            batch_trigger_func: 批次触发函数，接收(window_start, signals)返回bool
            **kwargs: 其他配置参数
        """
        kwargs.setdefault('window_type', WindowType.DAILY)  # 默认配置
        kwargs.setdefault('processing_mode', ProcessingMode.HYBRID)
        
        super().__init__(**kwargs)
        
        self._window_calculator = window_calculator
        self._batch_trigger_func = batch_trigger_func
        
    def get_window_start(self, timestamp: datetime) -> datetime:
        """
        使用自定义窗口计算函数
        
        Args:
            timestamp: 信号时间戳
            
        Returns:
            自定义计算的窗口起始时间
        """
        try:
            return self._window_calculator(timestamp)
        except Exception as e:
            self.logger.ERROR(f"Custom window calculator failed: {e}")
            # 回退到日线窗口
            return timestamp.replace(hour=0, minute=0, second=0, microsecond=0)
            
    def should_process_batch(self, window_start: datetime, signals: List[Signal]) -> bool:
        """
        使用自定义批次触发函数
        
        Args:
            window_start: 窗口起始时间
            signals: 该窗口内的信号列表
            
        Returns:
            自定义函数的判断结果
        """
        try:
            return self._batch_trigger_func(window_start, signals)
        except Exception as e:
            self.logger.ERROR(f"Custom batch trigger function failed: {e}")
            # 回退到基于批次大小的判断
            return len(signals) >= self.min_batch_size
