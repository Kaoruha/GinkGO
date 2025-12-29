# Upstream: Backtest Engines, Portfolio Manager
# Downstream: Data Layer, Event System
# Role: 信号处理模块导出批量/资源优化/窗口等处理器组件支持交易系统功能支持信号批量处理和性能优化提升系统吞吐量






"""
信号批处理模块

该模块实现了时间窗口批处理系统，用于解决信号逐个处理导致的资源竞争不真实问题。
支持多种时间粒度和处理模式，兼容回测和实盘交易需求。
"""

from .batch_processor import (
    TimeWindowBatchProcessor,
    WindowType,
    ProcessingMode,
)

from .window_processors import (
    DailyWindowProcessor,
    HourlyWindowProcessor,
    MinuteWindowProcessor,
    ImmediateProcessor,
)

from .resource_optimizer import (
    ResourceOptimizer,
    OptimizationStrategy,
)

__all__ = [
    'TimeWindowBatchProcessor',
    'WindowType',
    'ProcessingMode',
    'DailyWindowProcessor',
    'HourlyWindowProcessor', 
    'MinuteWindowProcessor',
    'ImmediateProcessor',
    'ResourceOptimizer',
    'OptimizationStrategy',
]