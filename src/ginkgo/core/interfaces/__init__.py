"""
统一接口定义模块

定义系统中所有组件的统一接口，确保不同模块间的兼容性。
"""

from .strategy_interface import IStrategy
from .model_interface import IModel  
from .engine_interface import IEngine
from .portfolio_interface import IPortfolio

__all__ = [
    'IStrategy',
    'IModel', 
    'IEngine',
    'IPortfolio'
]