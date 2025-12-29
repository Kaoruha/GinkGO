# Upstream: All Modules
# Downstream: Standard Library
# Role: 基础校验器模块提供ValidationLevel/ValidationResult/BaseValidator等类






"""
基础校验器模块
定义校验器通用接口和校验结果数据结构
"""

import ast
import importlib.util
import sys
import tempfile
import os
import inspect
from abc import ABC, abstractmethod
from enum import Enum
from typing import List, Dict, Any, Optional, Union
from dataclasses import dataclass


class ValidationLevel(Enum):
    """校验结果级别"""
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"


@dataclass
class ValidationResult:
    """校验结果数据结构"""
    is_valid: bool
    level: ValidationLevel
    message: str
    details: str = ""
    suggestions: List[str] = None
    
    def __post_init__(self):
        if self.suggestions is None:
            self.suggestions = []


class BaseValidator(ABC):
    """
    基础校验器抽象类
    定义所有组件校验器的通用接口和基础校验方法
    """
    
    def __init__(self):
        self.required_methods = []  # 子类需要定义必需的方法列表
        self.required_base_class = None  # 子类需要定义必需的基类
        
    @abstractmethod
    def validate_component_specific(self, module: Any) -> List[ValidationResult]:
        """
        组件特定的校验逻辑，由子类实现
        
        Args:
            module: 动态加载的组件模块
            
        Returns:
            List[ValidationResult]: 校验结果列表
        """
        pass
    
    def validate_code(self, code: str) -> ValidationResult:
        """
        校验代码字符串
        
        Args:
            code(str): Python代码字符串
            
        Returns:
            ValidationResult: 校验结果
        """
        try:
            # 创建临时文件
            with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as temp_file:
                temp_file.write(code)
                temp_file_path = temp_file.name
            
            try:
                return self.validate_file(temp_file_path)
            finally:
                # 清理临时文件
                if os.path.exists(temp_file_path):
                    os.unlink(temp_file_path)
                    
        except Exception as e:
            return ValidationResult(
                is_valid=False,
                level=ValidationLevel.ERROR,
                message="Failed to create temporary file for validation",
                details=str(e)
            )
    
    def validate_file(self, file_path: str) -> ValidationResult:
        """
        校验文件
        
        Args:
            file_path(str): 文件路径
            
        Returns:
            ValidationResult: 校验结果
        """
        # 基础校验流程
        results = []
        
        # 1. 文件存在性检查
        if not os.path.exists(file_path):
            return ValidationResult(
                is_valid=False,
                level=ValidationLevel.ERROR,
                message="File not found",
                details=f"File does not exist: {file_path}"
            )
        
        # 2. 语法校验
        syntax_result = self._validate_syntax(file_path)
        results.append(syntax_result)
        if not syntax_result.is_valid:
            return syntax_result
        
        # 3. 导入校验
        import_result = self._validate_imports(file_path)
        results.append(import_result)
        if not import_result.is_valid:
            return import_result
        
        # 4. 动态加载模块
        try:
            module = self._load_module(file_path)
        except Exception as e:
            return ValidationResult(
                is_valid=False,
                level=ValidationLevel.ERROR,
                message="Failed to load module",
                details=str(e),
                suggestions=["Check for import errors or syntax issues"]
            )
        
        # 5. 组件特定校验
        component_results = self.validate_component_specific(module)
        results.extend(component_results)
        
        # 合并所有结果
        return self._merge_results(results)
    
    def validate_component(self, component_id: str) -> ValidationResult:
        """
        校验已存储的组件
        
        Args:
            component_id(str): 组件ID
            
        Returns:
            ValidationResult: 校验结果
        """
        try:
            from ginkgo.data.operations import get_file
            
            # 获取组件信息
            file_df = get_file(component_id)
            if file_df.shape[0] == 0:
                return ValidationResult(
                    is_valid=False,
                    level=ValidationLevel.ERROR,
                    message="Component not found",
                    details=f"No component found with ID: {component_id}"
                )
            
            # 获取组件代码
            file_data = file_df.iloc[0]
            if 'data' not in file_data or not file_data['data']:
                return ValidationResult(
                    is_valid=False,
                    level=ValidationLevel.ERROR,
                    message="Component has no code data",
                    details=f"Component {component_id} exists but has no code content"
                )
            
            # 解码代码内容
            try:
                code = file_data['data'].decode('utf-8')
            except (UnicodeDecodeError, AttributeError) as e:
                return ValidationResult(
                    is_valid=False,
                    level=ValidationLevel.ERROR,
                    message="Failed to decode component code",
                    details=str(e)
                )
            
            return self.validate_code(code)
            
        except Exception as e:
            return ValidationResult(
                is_valid=False,
                level=ValidationLevel.ERROR,
                message="Failed to retrieve component",
                details=str(e)
            )
    
    def _validate_syntax(self, file_path: str) -> ValidationResult:
        """
        校验Python语法
        
        Args:
            file_path(str): 文件路径
            
        Returns:
            ValidationResult: 语法校验结果
        """
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                code = f.read()
            
            # 使用AST检查语法
            ast.parse(code)
            
            return ValidationResult(
                is_valid=True,
                level=ValidationLevel.INFO,
                message="Syntax validation passed",
                details="Python syntax is correct"
            )
            
        except SyntaxError as e:
            return ValidationResult(
                is_valid=False,
                level=ValidationLevel.ERROR,
                message="Syntax error",
                details=f"Line {e.lineno}: {e.msg}",
                suggestions=["Fix syntax errors before proceeding"]
            )
        except Exception as e:
            return ValidationResult(
                is_valid=False,
                level=ValidationLevel.ERROR,
                message="Failed to validate syntax",
                details=str(e)
            )
    
    def _validate_imports(self, file_path: str) -> ValidationResult:
        """
        校验导入依赖
        
        Args:
            file_path(str): 文件路径
            
        Returns:
            ValidationResult: 导入校验结果
        """
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                code = f.read()
            
            # 解析AST获取导入信息
            tree = ast.parse(code)
            imports = []
            missing_imports = []
            
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        imports.append(alias.name)
                elif isinstance(node, ast.ImportFrom):
                    if node.module:
                        imports.append(node.module)
            
            # 检查导入可用性
            for import_name in imports:
                try:
                    # 尝试导入模块
                    importlib.import_module(import_name.split('.')[0])
                except ImportError:
                    missing_imports.append(import_name)
            
            if missing_imports:
                return ValidationResult(
                    is_valid=False,
                    level=ValidationLevel.ERROR,
                    message="Missing dependencies",
                    details=f"Cannot import: {', '.join(missing_imports)}",
                    suggestions=[
                        "Install missing packages",
                        "Check import paths",
                        "Ensure Ginkgo environment is properly set up"
                    ]
                )
            
            return ValidationResult(
                is_valid=True,
                level=ValidationLevel.INFO,
                message="Import validation passed",
                details=f"All imports are available: {', '.join(imports)}"
            )
            
        except Exception as e:
            return ValidationResult(
                is_valid=False,
                level=ValidationLevel.ERROR,
                message="Failed to validate imports",
                details=str(e)
            )
    
    def _load_module(self, file_path: str):
        """
        动态加载模块
        
        Args:
            file_path(str): 文件路径
            
        Returns:
            module: 加载的模块对象
        """
        spec = importlib.util.spec_from_file_location("user_component", file_path)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module
    
    def _merge_results(self, results: List[ValidationResult]) -> ValidationResult:
        """
        合并多个校验结果
        
        Args:
            results(List[ValidationResult]): 校验结果列表
            
        Returns:
            ValidationResult: 合并后的结果
        """
        if not results:
            return ValidationResult(
                is_valid=True,
                level=ValidationLevel.INFO,
                message="No validation performed"
            )
        
        # 检查是否有错误
        has_errors = any(not r.is_valid for r in results)
        has_warnings = any(r.level == ValidationLevel.WARNING for r in results)
        
        # 合并消息和建议
        messages = [r.message for r in results if r.message]
        details = [r.details for r in results if r.details]
        suggestions = []
        for r in results:
            suggestions.extend(r.suggestions)
        
        if has_errors:
            level = ValidationLevel.ERROR
            is_valid = False
            message = "Validation failed with errors"
        elif has_warnings:
            level = ValidationLevel.WARNING
            is_valid = True
            message = "Validation passed with warnings"
        else:
            level = ValidationLevel.INFO
            is_valid = True
            message = "Validation passed successfully"
        
        return ValidationResult(
            is_valid=is_valid,
            level=level,
            message=message,
            details="; ".join(details),
            suggestions=list(set(suggestions))  # 去重
        )
    
    def _validate_method_return_type(self, method: Any, expected_types: List[str], method_name: str) -> ValidationResult:
        """
        使用AST分析验证方法返回值类型
        
        Args:
            method: 方法对象
            expected_types: 期望的返回类型列表，如 ['Order', 'None', 'List[Signal]']
            method_name: 方法名称
            
        Returns:
            ValidationResult: 验证结果
        """
        try:
            # 获取方法源代码
            source = inspect.getsource(method)
            
            # 处理缩进问题
            import textwrap
            source = textwrap.dedent(source)
            
            # 解析AST
            tree = ast.parse(source)
            
            # 查找所有return语句
            return_statements = []
            for node in ast.walk(tree):
                if isinstance(node, ast.Return):
                    return_statements.append(node)
            
            if not return_statements:
                return ValidationResult(
                    is_valid=False,
                    level=ValidationLevel.WARNING,
                    message=f"Method '{method_name}' has no return statements",
                    details="Method should explicitly return a value",
                    suggestions=[f"Add return statement that returns {' or '.join(expected_types)}"]
                )
            
            # 分析每个return语句
            problematic_returns = []
            return_analysis = []
            
            for i, ret_node in enumerate(return_statements):
                analysis = self._analyze_return_statement(ret_node, expected_types)
                return_analysis.append(analysis)
                
                if not analysis['is_valid']:
                    problematic_returns.append(f"Line {ret_node.lineno}: {analysis['description']}")
            
            # 如果有问题的返回语句
            if problematic_returns:
                # 处理列表元素问题
                all_details = []
                for ret_return in problematic_returns:
                    all_details.append(ret_return)
                
                # 添加列表元素的详细问题
                for analysis in return_analysis:
                    if 'element_issues' in analysis:
                        for issue in analysis['element_issues']:
                            all_details.append(f"List element issue: {issue}")
                
                return ValidationResult(
                    is_valid=False,
                    level=ValidationLevel.WARNING,
                    message=f"Method '{method_name}' may have incorrect return types",
                    details=f"Potential issues: {'; '.join(all_details)}",
                    suggestions=[
                        f"Ensure all return statements return {' or '.join(expected_types)}",
                        "Check variable types and method call return values",
                        "For lists, ensure all elements are of the correct type",
                        "Consider adding type hints for better validation"
                    ]
                )
            
            return ValidationResult(
                is_valid=True,
                level=ValidationLevel.INFO,
                message=f"Method '{method_name}' return type validation passed",
                details=f"Found {len(return_statements)} return statement(s), all appear correct"
            )
            
        except Exception as e:
            return ValidationResult(
                is_valid=True,
                level=ValidationLevel.WARNING,
                message=f"Could not validate return type for '{method_name}'",
                details=f"Analysis error: {str(e)}",
                suggestions=["Manual review of return statements recommended"]
            )
    
    def _analyze_return_statement(self, ret_node: ast.Return, expected_types: List[str]) -> Dict[str, Any]:
        """
        分析单个return语句
        
        Args:
            ret_node: AST Return节点
            expected_types: 期望的返回类型列表
            
        Returns:
            Dict: 分析结果
        """
        if ret_node.value is None:
            # return 或 return None
            return {
                'is_valid': 'None' in expected_types,
                'description': 'returns None',
                'type_hint': 'None'
            }
        
        # 分析返回值类型
        value = ret_node.value
        
        if isinstance(value, ast.Constant):
            # 常量值: return None, return 123, return "string"
            if value.value is None:
                return {
                    'is_valid': 'None' in expected_types,
                    'description': 'returns None constant',
                    'type_hint': 'None'
                }
            else:
                return {
                    'is_valid': False,  # 通常期望的不是基本常量
                    'description': f'returns constant {type(value.value).__name__}',
                    'type_hint': type(value.value).__name__
                }
        
        elif isinstance(value, ast.Name):
            # 变量返回: return order, return signals
            var_name = value.id
            return {
                'is_valid': True,  # 假设变量类型正确，无法静态确定
                'description': f'returns variable "{var_name}"',
                'type_hint': 'Variable'
            }
        
        elif isinstance(value, ast.List):
            # 列表返回: return [], return [signal1, signal2]
            is_list_expected = any('List' in expected or '[]' in expected for expected in expected_types)
            
            if not is_list_expected:
                return {
                    'is_valid': False,
                    'description': f'returns list with {len(value.elts)} elements',
                    'type_hint': 'List'
                }
            
            # 检查空列表
            if len(value.elts) == 0:
                return {
                    'is_valid': True,
                    'description': 'returns empty list',
                    'type_hint': 'List[]'
                }
            
            # 分析列表中的元素类型
            element_issues = []
            for i, element in enumerate(value.elts):
                element_analysis = self._analyze_list_element(element, expected_types, i)
                if not element_analysis['is_valid']:
                    element_issues.append(element_analysis['description'])
            
            if element_issues:
                return {
                    'is_valid': False,
                    'description': f'returns list with {len(value.elts)} elements, but some elements may be wrong type',
                    'type_hint': f'List[{len(element_issues)} issues]',
                    'element_issues': element_issues
                }
            
            return {
                'is_valid': True,
                'description': f'returns list with {len(value.elts)} elements',
                'type_hint': 'List'
            }
        
        elif isinstance(value, ast.Call):
            # 方法调用返回: return self.method(), return Order()
            if isinstance(value.func, ast.Name):
                func_name = value.func.id
                # 检查是否是构造函数调用与期望类型匹配
                is_valid = any(func_name in expected for expected in expected_types)
                # 特别检查：如果期望List但返回单个对象，则无效
                if any('List' in expected for expected in expected_types) and func_name not in ['list', 'List']:
                    is_valid = False
                return {
                    'is_valid': is_valid,
                    'description': f'returns result of {func_name}()',
                    'type_hint': f'{func_name}()'
                }
            elif isinstance(value.func, ast.Attribute):
                # self.method() 或 obj.method()
                return {
                    'is_valid': True,  # 假设方法调用正确
                    'description': 'returns method call result',
                    'type_hint': 'MethodCall'
                }
        
        elif isinstance(value, ast.Attribute):
            # 属性访问: return self.order, return obj.value
            return {
                'is_valid': True,  # 假设属性类型正确
                'description': 'returns attribute value',
                'type_hint': 'Attribute'
            }
        
        # 其他复杂表达式
        return {
            'is_valid': True,  # 保守假设正确
            'description': 'returns complex expression',
            'type_hint': 'Expression'
        }
    
    def _analyze_list_element(self, element: ast.AST, expected_types: List[str], index: int) -> Dict[str, Any]:
        """
        分析列表中的单个元素类型
        
        Args:
            element: AST元素节点
            expected_types: 期望的返回类型列表
            index: 元素在列表中的索引
            
        Returns:
            Dict: 元素分析结果
        """
        # 提取期望的元素类型
        expected_element_types = []
        for expected in expected_types:
            if 'List[' in expected:
                # 从 List[Signal] 提取 Signal
                element_type = expected.split('List[')[1].rstrip(']')
                expected_element_types.append(element_type)
        
        if not expected_element_types:
            # 如果没有指定具体的元素类型，假设正确
            return {
                'is_valid': True,
                'description': f'element {index} type unknown',
                'type_hint': 'Unknown'
            }
        
        # 分析元素类型
        if isinstance(element, ast.Constant):
            # 常量元素: [1, 2, 3] 或 ["a", "b", "c"]
            const_type = type(element.value).__name__
            is_valid = any(const_type.lower() in expected.lower() for expected in expected_element_types)
            return {
                'is_valid': is_valid,
                'description': f'element {index} is {const_type} constant',
                'type_hint': const_type
            }
        
        elif isinstance(element, ast.Name):
            # 变量元素: [signal1, signal2]
            var_name = element.id
            # 检查变量名是否暗示正确的类型
            is_valid = any(expected.lower() in var_name.lower() for expected in expected_element_types)
            return {
                'is_valid': is_valid,
                'description': f'element {index} is variable "{var_name}"',
                'type_hint': 'Variable'
            }
        
        elif isinstance(element, ast.Call):
            # 构造函数调用: [Signal(), Signal()]
            if isinstance(element.func, ast.Name):
                func_name = element.func.id
                is_valid = any(func_name in expected for expected in expected_element_types)
                return {
                    'is_valid': is_valid,
                    'description': f'element {index} is {func_name}() call',
                    'type_hint': f'{func_name}()'
                }
            else:
                # 方法调用: [self.create_signal(), obj.method()]
                return {
                    'is_valid': True,  # 假设方法调用正确
                    'description': f'element {index} is method call',
                    'type_hint': 'MethodCall'
                }
        
        elif isinstance(element, ast.Attribute):
            # 属性访问: [self.signal, obj.value]
            return {
                'is_valid': True,  # 假设属性类型正确
                'description': f'element {index} is attribute access',
                'type_hint': 'Attribute'
            }
        
        # 其他复杂表达式
        return {
            'is_valid': True,  # 保守假设正确
            'description': f'element {index} is complex expression',
            'type_hint': 'Expression'
        }