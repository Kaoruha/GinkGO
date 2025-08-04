"""
Ginkgo量化机器学习模块

提供机器学习与量化投资的集成功能，包括模型训练、预测、策略集成等。
与backtest模块紧密集成，支持机器学习驱动的量化策略开发。
"""

# Import container first (this is what users mainly need)
try:
    from .containers import container, ml_container
except ImportError as e:
    container = None
    ml_container = None
    print(f"Warning: ML containers not available: {e}")

# Try to import other components, but don't fail if they're not available
try:
    from . import models
except ImportError as e:
    models = None

try:
    from . import strategies
except ImportError as e:
    strategies = None

__version__ = "1.0.0"
__author__ = "Ginkgo Team"

# Export the main interfaces that users need
__all__ = ['container', 'ml_container', 'models', 'strategies']