"""
引擎模块 - 计算和解析引擎

重新组织的引擎模块，包含：
- FactorEngine: 因子计算引擎
- ExpressionEngine: 表达式处理引擎  
- Expression子模块: 表达式解析组件
"""

from .factor_engine import FactorEngine
from .expression_engine import ExpressionEngine

# 导出expression子模块的核心组件
from .expression.parser import ExpressionParser
from .expression.registry import OperatorRegistry

__all__ = [
    "FactorEngine",
    "ExpressionEngine", 
    "ExpressionParser",
    "OperatorRegistry",
]