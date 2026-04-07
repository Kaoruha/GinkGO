# Upstream: 核心模块(core.__init__)、工厂模块(core.factories)、接口模块(core.interfaces)
# Downstream: BaseAdapter, ModeAdapter, ModelAdapter, StrategyAdapter, GLOG日志
# Role: 适配器模式包入口，导出基类/模式/模型/策略四类适配器，实现组件间的无缝集成和接口转换






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
