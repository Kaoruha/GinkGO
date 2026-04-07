# Upstream: 核心模块(core.__init__)、全局服务访问(通过container.services获取配置/日志/线程)
# Downstream: core_containers(container/CoreContainer/Container)
# Role: DI容器包入口，导出Container容器类和全局单例container实例，提供配置/日志/线程等核心服务的依赖注入






"""
Core模块DI容器

提供核心模块的依赖注入支持，管理配置、日志、线程等核心服务。
使用dependency-injector库统一管理依赖注入。
"""

# 直接从新容器导入，移除旧容器兼容逻辑
from ginkgo.core.core_containers import container, core_container, Container

# 保持向后兼容的别名
CoreContainer = Container

__all__ = [
    'CoreContainer',
    'Container',
    'container',
    'core_container'
]
