"""
ML模块DI容器

提供机器学习模块的依赖注入支持，管理模型、策略、工具等组件的依赖关系。
"""

# Import from new unified container
try:
    # Try to import the new container from the parent directory
    from ..containers import container, ml_container
    
    # For backward compatibility, also export the old name
    MLContainer = type(ml_container)
    
except ImportError:
    # Fallback to old container if new one is not available
    from .ml_container import MLContainer
    
    # Create dummy instances for compatibility
    container = None
    ml_container = None

__all__ = [
    'MLContainer',
    'container',
    'ml_container'
]