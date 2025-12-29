# Upstream: External Applications
# Downstream: Trading Strategies, Analysis Tools
# Role: 表达式引擎模块公共接口，导出Parser解析器、ASTNodes抽象语法树、Operators运算符、Registry注册表等表达式解析组件






"""
Expression Module - 表达式解析层

负责将字符串表达式解析为可执行的AST结构：
- ExpressionParser: 表达式解析器
- AST节点定义和执行
- 操作符注册和管理
"""

from ginkgo.features.engines.expression.parser import ExpressionParser
from ginkgo.features.engines.expression.ast_nodes import *
from ginkgo.features.engines.expression.registry import OperatorRegistry

__all__ = [
    "ExpressionParser",
    "OperatorRegistry",
    "ASTNode",
    "FieldNode", 
    "NumberNode",
    "BinaryOpNode",
    "FunctionNode"
]