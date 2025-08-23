"""
Expression Parser - 表达式解析器

将字符串表达式解析为可执行的AST结构：
- 词法分析：将表达式分解为tokens
- 语法分析：构建抽象语法树
- 错误处理：提供详细的错误信息
"""

import re
from typing import List, Union, Optional
from .ast_nodes import *
from .registry import OperatorRegistry
from ginkgo.libs import GLOG


class ParseError(Exception):
    """解析错误异常"""
    def __init__(self, message: str, position: int = -1, expression: str = ""):
        self.message = message
        self.position = position
        self.expression = expression
        super().__init__(self._format_error())
    
    def _format_error(self):
        """格式化错误信息"""
        if self.position >= 0 and self.expression:
            error_pointer = " " * self.position + "^"
            return f"Parse error at position {self.position}: {self.message}\n{self.expression}\n{error_pointer}"
        return f"Parse error: {self.message}"


class Token:
    """词法单元"""
    def __init__(self, type_: str, value: str, position: int):
        self.type = type_
        self.value = value
        self.position = position
    
    def __repr__(self):
        return f"Token({self.type}, {self.value}, {self.position})"


class ExpressionParser:
    """表达式解析器"""
    
    # Token类型定义
    TOKEN_TYPES = {
        'FIELD': r'\$\w+',                    # $close, $volume
        'NUMBER': r'\d+\.?\d*',               # 20, 3.14
        'FUNCTION': r'[A-Za-z_]\w*(?=\()',   # Mean(, RSI(
        'IDENTIFIER': r'[A-Za-z_]\w*',       # 标识符
        'OPERATOR': r'[+\-*/]',              # +, -, *, /
        'COMPARISON': r'(>=|<=|==|!=|>|<)',  # 比较运算符
        'LPAREN': r'\(',                     # (
        'RPAREN': r'\)',                     # )
        'COMMA': r',',                       # ,
        'WHITESPACE': r'\s+',                # 空白字符
    }
    
    def __init__(self):
        """初始化解析器"""
        self.tokens: List[Token] = []
        self.position = 0
        self.expression = ""
        
        # 编译正则表达式
        self.token_regex = self._compile_token_patterns()
        
        # 导入操作符模块确保注册
        self._import_operators()
    
    def _compile_token_patterns(self):
        """编译token模式的正则表达式"""
        patterns = []
        for token_type, pattern in self.TOKEN_TYPES.items():
            patterns.append(f"(?P<{token_type}>{pattern})")
        return re.compile('|'.join(patterns))
    
    def _import_operators(self):
        """导入操作符模块确保它们被注册"""
        try:
            from .operators import basic, statistical, temporal, technical
        except ImportError as e:
            GLOG.WARNING(f"Failed to import some operator modules: {e}")
    
    def parse(self, expression: str) -> ASTNode:
        """
        解析表达式字符串为AST
        
        Args:
            expression: 表达式字符串
            
        Returns:
            ASTNode: 根节点
            
        Raises:
            ParseError: 解析错误
        """
        try:
            self.expression = expression.strip()
            if not self.expression:
                raise ParseError("Empty expression")
            
            # 词法分析
            self.tokens = self._tokenize(self.expression)
            if not self.tokens:
                raise ParseError("No valid tokens found")
            
            self.position = 0
            
            # 语法分析
            ast = self._parse_expression()
            
            # 检查是否有未消费的tokens
            if self.position < len(self.tokens):
                unexpected_token = self.tokens[self.position]
                raise ParseError(
                    f"Unexpected token: {unexpected_token.value}",
                    unexpected_token.position,
                    self.expression
                )
            
            return ast
            
        except ParseError:
            raise
        except Exception as e:
            GLOG.ERROR(f"Unexpected error during parsing: {e}")
            raise ParseError(f"Parsing failed: {str(e)}")
    
    def _tokenize(self, expression: str) -> List[Token]:
        """
        词法分析 - 将表达式分解为tokens
        
        Args:
            expression: 表达式字符串
            
        Returns:
            List[Token]: token列表
        """
        tokens = []
        pos = 0
        
        while pos < len(expression):
            match = self.token_regex.match(expression, pos)
            if not match:
                raise ParseError(f"Invalid character: '{expression[pos]}'", pos, expression)
            
            token_type = match.lastgroup
            token_value = match.group()
            
            # 跳过空白字符
            if token_type != 'WHITESPACE':
                tokens.append(Token(token_type, token_value, pos))
            
            pos = match.end()
        
        return tokens
    
    def _current_token(self) -> Optional[Token]:
        """获取当前token"""
        if self.position < len(self.tokens):
            return self.tokens[self.position]
        return None
    
    def _consume_token(self, expected_type: str = None) -> Token:
        """
        消费当前token
        
        Args:
            expected_type: 期望的token类型
            
        Returns:
            Token: 消费的token
            
        Raises:
            ParseError: 如果token类型不匹配或没有更多token
        """
        if self.position >= len(self.tokens):
            raise ParseError("Unexpected end of expression", len(self.expression), self.expression)
        
        token = self.tokens[self.position]
        if expected_type and token.type != expected_type:
            raise ParseError(
                f"Expected {expected_type}, got {token.type}",
                token.position,
                self.expression
            )
        
        self.position += 1
        return token
    
    def _parse_expression(self) -> ASTNode:
        """解析表达式 - 处理比较运算符 (>=, <=, ==, !=, >, <)"""
        node = self._parse_additive()
        
        while self._current_token() and self._current_token().type == 'COMPARISON':
            operator_token = self._consume_token('COMPARISON')
            right = self._parse_additive()
            node = BinaryOpNode(node, operator_token.value, right)
        
        return node
    
    def _parse_additive(self) -> ASTNode:
        """解析加法和减法表达式"""
        node = self._parse_multiplicative()
        
        while (self._current_token() and 
               self._current_token().type == 'OPERATOR' and 
               self._current_token().value in ['+', '-']):
            operator_token = self._consume_token('OPERATOR')
            right = self._parse_multiplicative()
            node = BinaryOpNode(node, operator_token.value, right)
        
        return node
    
    def _parse_multiplicative(self) -> ASTNode:
        """解析乘法和除法表达式"""
        node = self._parse_unary()
        
        while (self._current_token() and 
               self._current_token().type == 'OPERATOR' and 
               self._current_token().value in ['*', '/']):
            operator_token = self._consume_token('OPERATOR')
            right = self._parse_unary()
            node = BinaryOpNode(node, operator_token.value, right)
        
        return node
    
    def _parse_unary(self) -> ASTNode:
        """解析一元表达式（负号）"""
        current = self._current_token()
        
        if (current and current.type == 'OPERATOR' and current.value == '-'):
            self._consume_token('OPERATOR')
            operand = self._parse_unary()
            # 创建 0 - operand
            return BinaryOpNode(NumberNode(0), '-', operand)
        
        return self._parse_primary()
    
    def _parse_primary(self) -> ASTNode:
        """解析基本表达式元素"""
        current = self._current_token()
        
        if not current:
            raise ParseError("Unexpected end of expression", len(self.expression), self.expression)
        
        # 字段引用: $close, $volume
        if current.type == 'FIELD':
            token = self._consume_token('FIELD')
            return FieldNode(token.value)
        
        # 数字常量: 20, 3.14
        elif current.type == 'NUMBER':
            token = self._consume_token('NUMBER')
            try:
                return NumberNode(float(token.value))
            except ValueError:
                raise ParseError(f"Invalid number: {token.value}", token.position, self.expression)
        
        # 函数调用: Mean($close, 20)
        elif current.type == 'FUNCTION':
            return self._parse_function()
        
        # 括号表达式: ($close + $volume)
        elif current.type == 'LPAREN':
            self._consume_token('LPAREN')
            node = self._parse_expression()
            self._consume_token('RPAREN')
            return node
        
        # 条件表达式: IF(condition, true_value, false_value)
        elif current.type == 'IDENTIFIER' and current.value.upper() == 'IF':
            return self._parse_conditional()
        
        else:
            raise ParseError(
                f"Unexpected token: {current.value}",
                current.position,
                self.expression
            )
    
    def _parse_function(self) -> ASTNode:
        """解析函数调用"""
        function_token = self._consume_token('FUNCTION')
        function_name = function_token.value
        
        # 验证函数是否已注册
        if not OperatorRegistry.is_registered(function_name):
            raise ParseError(
                f"Unknown function: {function_name}",
                function_token.position,
                self.expression
            )
        
        self._consume_token('LPAREN')
        
        # 解析参数列表
        args = []
        
        # 处理空参数列表
        if self._current_token() and self._current_token().type == 'RPAREN':
            self._consume_token('RPAREN')
            return FunctionNode(function_name, args)
        
        # 解析第一个参数
        args.append(self._parse_expression())
        
        # 解析后续参数
        while self._current_token() and self._current_token().type == 'COMMA':
            self._consume_token('COMMA')
            args.append(self._parse_expression())
        
        self._consume_token('RPAREN')
        
        # 验证参数数量
        if not OperatorRegistry.validate_function_call(function_name, len(args)):
            operator_info = OperatorRegistry.get_operator_info(function_name)
            min_args = operator_info.get('min_args', 0)
            max_args = operator_info.get('max_args', len(args))
            raise ParseError(
                f"Function {function_name} expects {min_args}-{max_args} arguments, got {len(args)}",
                function_token.position,
                self.expression
            )
        
        return FunctionNode(function_name, args)
    
    def _parse_conditional(self) -> ASTNode:
        """解析条件表达式: IF(condition, true_value, false_value)"""
        if_token = self._consume_token('IDENTIFIER')  # IF
        self._consume_token('LPAREN')
        
        # 解析条件
        condition = self._parse_expression()
        self._consume_token('COMMA')
        
        # 解析真值
        true_value = self._parse_expression()
        self._consume_token('COMMA')
        
        # 解析假值
        false_value = self._parse_expression()
        self._consume_token('RPAREN')
        
        return ConditionalNode(condition, true_value, false_value)
    
    def validate_expression(self, expression: str) -> bool:
        """
        验证表达式语法是否正确
        
        Args:
            expression: 表达式字符串
            
        Returns:
            bool: 是否有效
        """
        try:
            self.parse(expression)
            return True
        except ParseError as e:
            GLOG.DEBUG(f"Expression validation failed: {e}")
            return False
        except Exception as e:
            GLOG.ERROR(f"Unexpected error during validation: {e}")
            return False
    
    def get_dependencies(self, expression: str) -> List[str]:
        """
        获取表达式依赖的字段
        
        Args:
            expression: 表达式字符串
            
        Returns:
            List[str]: 依赖的字段列表
        """
        try:
            ast = self.parse(expression)
            dependencies = set()
            self._collect_dependencies(ast, dependencies)
            return list(dependencies)
        except Exception as e:
            GLOG.ERROR(f"Failed to get dependencies: {e}")
            return []
    
    def _collect_dependencies(self, node: ASTNode, dependencies: set):
        """递归收集AST中的字段依赖"""
        if isinstance(node, FieldNode):
            dependencies.add(node.field_name)
        elif isinstance(node, BinaryOpNode):
            self._collect_dependencies(node.left, dependencies)
            self._collect_dependencies(node.right, dependencies)
        elif isinstance(node, FunctionNode):
            for arg in node.args:
                self._collect_dependencies(arg, dependencies)
        elif isinstance(node, ConditionalNode):
            self._collect_dependencies(node.condition, dependencies)
            self._collect_dependencies(node.true_value, dependencies)
            self._collect_dependencies(node.false_value, dependencies)


# 便捷函数
def parse_expression(expression: str) -> ASTNode:
    """解析表达式的便捷函数"""
    parser = ExpressionParser()
    return parser.parse(expression)


def validate_expression(expression: str) -> bool:
    """验证表达式的便捷函数"""
    parser = ExpressionParser()
    return parser.validate_expression(expression)


def get_expression_dependencies(expression: str) -> List[str]:
    """获取表达式依赖的便捷函数"""
    parser = ExpressionParser()
    return parser.get_dependencies(expression)