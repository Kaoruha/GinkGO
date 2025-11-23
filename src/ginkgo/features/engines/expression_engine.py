"""
Expression Engine - 表达式执行引擎

负责表达式的解析、编译和执行，提供：
- 表达式解析和AST构建
- 运算符注册和执行
- 数据流处理和优化
"""

from typing import Dict, List, Optional, Any
import pandas as pd
from ginkgo.libs import GLOG
from ginkgo.features.engines.expression.parser import ExpressionParser
# from .expression.operator_registry import OperatorRegistry


class ExpressionEngine:
    """
    表达式执行引擎
    
    提供表达式解析、编译和执行功能，支持：
    - 自定义运算符注册
    - 数据流优化
    - 批量表达式执行
    """
    
    def __init__(self):
        """初始化表达式引擎"""
        self.parser = ExpressionParser()
        # self.operator_registry = OperatorRegistry()
        GLOG.INFO("ExpressionEngine initialized")
    
    def parse_expression(self, expression: str) -> Dict[str, Any]:
        """
        解析表达式为AST
        
        Args:
            expression: 表达式字符串
            
        Returns:
            Dict: 解析后的AST结构
        """
        try:
            return self.parser.parse(expression)
        except Exception as e:
            GLOG.ERROR(f"Expression parsing failed: {expression}, error: {e}")
            raise
    
    def execute_expression(self, expression: str, data: pd.DataFrame) -> pd.Series:
        """
        执行表达式计算
        
        Args:
            expression: 表达式字符串
            data: 输入数据DataFrame
            
        Returns:
            pd.Series: 计算结果
        """
        try:
            ast = self.parse_expression(expression)
            return self._evaluate_ast(ast, data)
        except Exception as e:
            GLOG.ERROR(f"Expression execution failed: {expression}, error: {e}")
            raise
    
    def _evaluate_ast(self, ast: Dict[str, Any], data: pd.DataFrame) -> pd.Series:
        """
        递归评估AST节点
        
        Args:
            ast: AST节点或AST节点对象
            data: 数据DataFrame
            
        Returns:
            pd.Series: 节点计算结果
        """
        try:
            # 如果ast已经是AST节点对象，直接调用execute方法
            if hasattr(ast, 'execute'):
                return ast.execute(data)
            
            # 如果ast是字典，需要根据类型创建相应的AST节点
            from ginkgo.features.engines.expression.ast_nodes import (
                FieldNode, NumberNode, BinaryOpNode, FunctionNode, ConditionalNode
            )
            
            if isinstance(ast, dict):
                node_type = ast.get('type')
                
                if node_type == 'field':
                    node = FieldNode(ast['field_name'])
                    return node.execute(data)
                
                elif node_type == 'number':
                    node = NumberNode(ast['value'])
                    return node.execute(data)
                
                elif node_type == 'binary_op':
                    left = self._evaluate_ast(ast['left'], data)
                    right = self._evaluate_ast(ast['right'], data)
                    node = BinaryOpNode(ast['operator'], None, None)
                    # 直接使用已计算的值
                    return node._apply_operator(left, right)
                
                elif node_type == 'function':
                    # 递归评估参数
                    args = []
                    for arg in ast.get('args', []):
                        args.append(self._evaluate_ast(arg, data))
                    
                    # 调用函数
                    from ginkgo.features.engines.expression.registry import OperatorRegistry
                    return OperatorRegistry.execute_function(
                        ast['function_name'], args, data
                    )
                
                elif node_type == 'conditional':
                    condition = self._evaluate_ast(ast['condition'], data)
                    true_value = self._evaluate_ast(ast['true_value'], data)
                    false_value = self._evaluate_ast(ast['false_value'], data)
                    
                    # 实现条件逻辑
                    bool_condition = condition.fillna(False).astype(bool)
                    return true_value.where(bool_condition, false_value)
                
                else:
                    raise ValueError(f"Unknown AST node type: {node_type}")
            
            else:
                raise ValueError(f"Invalid AST format: {type(ast)}")
                
        except Exception as e:
            GLOG.ERROR(f"AST evaluation failed: {e}")
            import numpy as np
            return pd.Series([np.nan] * len(data), index=data.index)
    
    def register_operator(self, name: str, func: callable):
        """注册自定义运算符"""
        # self.operator_registry.register(name, func)
        GLOG.INFO(f"Operator registered: {name}")
    
    def batch_execute(self, expressions: Dict[str, str], data: pd.DataFrame) -> pd.DataFrame:
        """
        批量执行表达式
        
        Args:
            expressions: 表达式字典 {name: expression}
            data: 输入数据
            
        Returns:
            pd.DataFrame: 所有表达式的计算结果
        """
        results = {}
        for name, expr in expressions.items():
            try:
                results[name] = self.execute_expression(expr, data)
            except Exception as e:
                GLOG.ERROR(f"Failed to execute {name}: {e}")
                results[name] = pd.Series([None] * len(data), index=data.index)
        
        return pd.DataFrame(results)