# Upstream: 核心模块(core.__init__)、各业务模块通过工厂创建组件
# Downstream: BaseFactory, ComponentFactory
# Role: 工厂模式包入口，导出BaseFactory基类和ComponentFactory组件工厂，提供依赖注入的组件创建






"""
Core工厂模块

提供统一的工厂接口和实现，支持依赖注入的组件创建。
"""

from ginkgo.core.factories.base_factory import BaseFactory
from ginkgo.core.factories.component_factory import ComponentFactory

__all__ = [
    'BaseFactory',
    'ComponentFactory',
]