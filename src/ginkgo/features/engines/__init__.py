# Upstream: External Applications
# Downstream: Trading Strategies, Analysis Tools
# Role: 因子引擎模块公共接口，导出ExpressionEngine表达式引擎、FactorEngine因子引擎等因子计算引擎，支持表达式解析和因子计算






"""
引擎模块 - 计算和解析引擎

重新组织的引擎模块，包含：
- FactorEngine: 因子计算引擎
- ExpressionEngine: 表达式处理引擎  
- Expression子模块: 表达式解析组件
"""

from ginkgo.features.engines.factor_engine import FactorEngine
from ginkgo.features.engines.expression_engine import ExpressionEngine

# 导出expression子模块的核心组件
from ginkgo.features.engines.expression.parser import ExpressionParser
from ginkgo.features.engines.expression.registry import OperatorRegistry

__all__ = [
    "FactorEngine",
    "ExpressionEngine", 
    "ExpressionParser",
    "OperatorRegistry",
]