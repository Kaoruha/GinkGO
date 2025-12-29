# Upstream: All Modules
# Downstream: Standard Library
# Role: 核心适配器模块导出基类/模式/模型/策略等适配器实现支持交易系统功能提供组件适配和接口转换支持模块解耦






"""
适配器模式实现

提供各种适配器，实现不同组件间的无缝集成，
特别是策略模式适配和ML集成适配。
"""

from ginkgo.core.adapters.base_adapter import BaseAdapter
from ginkgo.core.adapters.mode_adapter import ModeAdapter
from ginkgo.core.adapters.strategy_adapter import StrategyAdapter
from ginkgo.core.adapters.model_adapter import ModelAdapter

__all__ = [
    'BaseAdapter',
    'ModeAdapter', 
    'StrategyAdapter',
    'ModelAdapter'
]