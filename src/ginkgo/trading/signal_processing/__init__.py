# Upstream: BacktestEngine, PortfolioBase
# Downstream: TimeWindowBatchProcessor, WindowType, ProcessingMode, DailyWindowProcessor, ResourceOptimizer
# Role: 信号批处理模块包，导出时间窗口批处理器、窗口处理器和资源优化器






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
