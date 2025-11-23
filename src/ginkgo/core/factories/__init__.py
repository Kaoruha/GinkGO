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