# Upstream: Backtest Engines, Portfolio Manager
# Downstream: Data Layer, Event System
# Role: 接口Mixin模块导出引擎混入/事件混入/策略数据混入等接口混入类支持交易系统功能和组件集成提供完整业务支持






"""
Trading Interface Mixins

提供各种功能混入类，增强Ginkgo交易系统的组件能力。

Mixin类：
- EngineMixin: 引擎事件上下文追踪和性能监控
- EventMixin: 事件数据模型增强 (TASK-010)
- ParameterValidationMixin: 参数验证和管理功能
- StrategyDataMixin: 策略数据处理功能

使用方式：
    from ginkgo.trading.interfaces.mixins import EngineMixin

    class MyEngine(BaseEngine, EngineMixin):
        def __init__(self, **kwargs):
            super().__init__(**kwargs)
            # 自动获得EngineMixin的所有功能

Author: TDD Framework
Created: 2024-01-17
"""

from .engine_mixin import EngineMixin
from .event_mixin import EventMixin
from .strategy_data_mixin import StrategyDataMixin

__all__ = [
    'EngineMixin',
    'EventMixin',
    'StrategyDataMixin',
]