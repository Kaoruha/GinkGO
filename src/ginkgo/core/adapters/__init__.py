"""
适配器模式实现

提供各种适配器，实现不同组件间的无缝集成，
特别是策略模式适配和ML集成适配。
"""

from .base_adapter import BaseAdapter
from .mode_adapter import ModeAdapter
from .strategy_adapter import StrategyAdapter
from .model_adapter import ModelAdapter

__all__ = [
    'BaseAdapter',
    'ModeAdapter', 
    'StrategyAdapter',
    'ModelAdapter'
]