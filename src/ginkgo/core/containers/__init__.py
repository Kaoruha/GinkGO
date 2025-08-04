"""
Core模块DI容器

提供核心模块的依赖注入支持，管理适配器、工厂、工具等组件的依赖关系。
"""

# Import from the correct core_containers module
try:
    # Import from the core_containers.py file in the parent directory
    from ..core_containers import container, core_container, Container
    
    # For backward compatibility, also export the old name
    CoreContainer = Container
    
except ImportError:
    # Fallback to old container if new one is not available
    try:
        from .core_container import CoreContainer
        
        # Create dummy instances for compatibility
        container = None
        core_container = None
    except ImportError:
        # If even the fallback fails, create basic dummy classes
        class CoreContainer:
            pass
        
        container = None
        core_container = None

__all__ = [
    'CoreContainer',
    'container',
    'core_container'
]