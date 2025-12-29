# Upstream: All Modules
# Downstream: Standard Library
# Role: 核心容器模块导出核心容器/应用容器等依赖注入容器提供组件注册和解析功能支持交易系统功能和组件集成提供完整业务支持






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