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