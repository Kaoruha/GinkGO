# Upstream: All Modules
# Downstream: Standard Library
# Role: 核心工厂模块公共接口，导出BaseFactory工厂基类、ComponentFactory组件工厂等工厂类，提供组件创建和装配功能






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