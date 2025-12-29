# Upstream: External Applications
# Downstream: Trading Strategies, Analysis Tools
# Role: Ast Nodes模块提供ASTNodes抽象语法树节点定义表达式AST节点类型支持相关业务功能支持交易系统功能






"""
AST Nodes - 抽象语法树节点定义

定义表达式解析后的AST节点类型和执行逻辑：
- ASTNode: 抽象基类
- FieldNode: 字段节点 ($close, $volume)
- NumberNode: 数值节点 (20, 0.5)
- BinaryOpNode: 二元运算节点 (+, -, *, /)
- FunctionNode: 函数节点 (Mean, Ref, RSI)
"""

from abc import ABC, abstractmethod
from typing import List, Any
import pandas as pd
import numpy as np
from ginkgo.libs import GLOG


class ASTNode(ABC):
    """AST节点抽象基类"""
    
    @abstractmethod
    def execute(self, data: pd.DataFrame) -> pd.Series:
        """
        执行节点计算
        
        Args:
            data: 输入数据DataFrame，包含OHLCV等字段
            
        Returns:
            pd.Series: 计算结果序列
        """
        pass
    
    def __repr__(self):
        """调试用的字符串表示"""
        return f"{self.__class__.__name__}()"


class FieldNode(ASTNode):
    """
    字段节点 - 引用数据中的字段
    
    示例: $close, $volume, $high, $low, $open
    """
    
    def __init__(self, field_name: str):
        """
        初始化字段节点
        
        Args:
            field_name: 字段名称，支持带$前缀或不带
        """
        # 移除$前缀，标准化字段名
        self.field_name = field_name.lstrip('$').lower()
        
    def execute(self, data: pd.DataFrame) -> pd.Series:
        """返回指定字段的数据"""
        try:
            if self.field_name not in data.columns:
                raise ValueError(f"Field '{self.field_name}' not found in data columns: {list(data.columns)}")
                
            return data[self.field_name].copy()
            
        except Exception as e:
            GLOG.ERROR(f"FieldNode execution failed for field '{self.field_name}': {e}")
            # 返回NaN序列，不中断计算
            return pd.Series([np.nan] * len(data), index=data.index)
    
    def __repr__(self):
        return f"FieldNode(${self.field_name})"


class NumberNode(ASTNode):
    """
    数值节点 - 常量数值
    
    示例: 20, 0.5, -1.2
    """
    
    def __init__(self, value: float):
        """
        初始化数值节点
        
        Args:
            value: 数值常量
        """
        self.value = float(value)
        
    def execute(self, data: pd.DataFrame) -> pd.Series:
        """返回常量值序列"""
        try:
            return pd.Series([self.value] * len(data), index=data.index, dtype=float)
        except Exception as e:
            GLOG.ERROR(f"NumberNode execution failed for value {self.value}: {e}")
            return pd.Series([np.nan] * len(data), index=data.index)
    
    def __repr__(self):
        return f"NumberNode({self.value})"


class BinaryOpNode(ASTNode):
    """
    二元运算节点 - 支持基础数学运算
    
    示例: +, -, *, /, >, <, >=, <=, ==, !=
    """
    
    def __init__(self, left: ASTNode, operator: str, right: ASTNode):
        """
        初始化二元运算节点
        
        Args:
            left: 左操作数节点
            operator: 运算符
            right: 右操作数节点
        """
        self.left = left
        self.operator = operator
        self.right = right
        
    def execute(self, data: pd.DataFrame) -> pd.Series:
        """执行二元运算"""
        try:
            left_result = self.left.execute(data)
            right_result = self.right.execute(data)
            
            # 确保两个序列有相同的索引
            if not left_result.index.equals(right_result.index):
                # 重新对齐索引
                left_result, right_result = left_result.align(right_result, join='outer', fill_value=np.nan)
            
            # 执行运算
            if self.operator == '+':
                return left_result + right_result
            elif self.operator == '-':
                return left_result - right_result
            elif self.operator == '*':
                return left_result * right_result
            elif self.operator == '/':
                # 避免除零错误
                with np.errstate(divide='ignore', invalid='ignore'):
                    result = left_result / right_result
                    return result.replace([np.inf, -np.inf], np.nan)
            elif self.operator == '>':
                return (left_result > right_result).astype(float)
            elif self.operator == '<':
                return (left_result < right_result).astype(float)
            elif self.operator == '>=':
                return (left_result >= right_result).astype(float)
            elif self.operator == '<=':
                return (left_result <= right_result).astype(float)
            elif self.operator == '==':
                return (left_result == right_result).astype(float)
            elif self.operator == '!=':
                return (left_result != right_result).astype(float)
            else:
                raise ValueError(f"Unsupported operator: {self.operator}")
                
        except Exception as e:
            GLOG.ERROR(f"BinaryOpNode execution failed for operator '{self.operator}': {e}")
            return pd.Series([np.nan] * len(data), index=data.index)
    
    def __repr__(self):
        return f"BinaryOpNode({self.left} {self.operator} {self.right})"


class FunctionNode(ASTNode):
    """
    函数节点 - 调用注册的函数
    
    示例: Mean($close, 20), Ref($close, 5), RSI($close, 14)
    """
    
    def __init__(self, function_name: str, args: List[ASTNode]):
        """
        初始化函数节点
        
        Args:
            function_name: 函数名称
            args: 参数节点列表
        """
        self.function_name = function_name
        self.args = args
        
    def execute(self, data: pd.DataFrame) -> pd.Series:
        """执行函数调用"""
        try:
            # 延迟导入避免循环依赖
            from ginkgo.features.engines.expression.registry import OperatorRegistry
            
            # 执行所有参数节点
            arg_values = []
            for arg in self.args:
                arg_result = arg.execute(data)
                arg_values.append(arg_result)
            
            # 调用注册的函数
            result = OperatorRegistry.execute_function(
                self.function_name, 
                arg_values, 
                data
            )
            
            return result
            
        except Exception as e:
            GLOG.ERROR(f"FunctionNode execution failed for function '{self.function_name}': {e}")
            return pd.Series([np.nan] * len(data), index=data.index)
    
    def __repr__(self):
        args_repr = ", ".join(str(arg) for arg in self.args)
        return f"FunctionNode({self.function_name}({args_repr}))"


class ConditionalNode(ASTNode):
    """
    条件节点 - 三元条件运算
    
    示例: IF($close > Mean($close, 20), 1, 0)
    """
    
    def __init__(self, condition: ASTNode, true_value: ASTNode, false_value: ASTNode):
        """
        初始化条件节点
        
        Args:
            condition: 条件表达式节点
            true_value: 条件为真时的值
            false_value: 条件为假时的值
        """
        self.condition = condition
        self.true_value = true_value
        self.false_value = false_value
        
    def execute(self, data: pd.DataFrame) -> pd.Series:
        """执行条件运算"""
        try:
            condition_result = self.condition.execute(data)
            true_result = self.true_value.execute(data)
            false_result = self.false_value.execute(data)
            
            # 条件选择
            result = pd.Series(index=data.index, dtype=float)
            condition_bool = condition_result.astype(bool)
            
            result.loc[condition_bool] = true_result.loc[condition_bool]
            result.loc[~condition_bool] = false_result.loc[~condition_bool]
            
            return result
            
        except Exception as e:
            GLOG.ERROR(f"ConditionalNode execution failed: {e}")
            return pd.Series([np.nan] * len(data), index=data.index)
    
    def __repr__(self):
        return f"ConditionalNode(IF({self.condition}, {self.true_value}, {self.false_value}))"


# 工具函数
def create_field_node(field_name: str) -> FieldNode:
    """创建字段节点的便捷函数"""
    return FieldNode(field_name)


def create_number_node(value: float) -> NumberNode:
    """创建数值节点的便捷函数"""
    return NumberNode(value)


def create_binary_op_node(left: ASTNode, operator: str, right: ASTNode) -> BinaryOpNode:
    """创建二元运算节点的便捷函数"""
    return BinaryOpNode(left, operator, right)


def create_function_node(function_name: str, *args: ASTNode) -> FunctionNode:
    """创建函数节点的便捷函数"""
    return FunctionNode(function_name, list(args))


def create_conditional_node(condition: ASTNode, true_value: ASTNode, false_value: ASTNode) -> ConditionalNode:
    """创建条件节点的便捷函数"""
    return ConditionalNode(condition, true_value, false_value)