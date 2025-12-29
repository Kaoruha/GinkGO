# Upstream: All Modules
# Downstream: Standard Library
# Role: Analyzer Validator验证器检查AnalyzerValidator分析器配置合理性支持相关功能






"""
分析器组件校验器
专门用于校验用户自定义的分析器组件
"""

import ast
import inspect
import re
from typing import List, Any

from ginkgo.libs.validators.base_validator import BaseValidator, ValidationResult, ValidationLevel
from ginkgo.libs.validators.validation_rules import ValidationRules


class AnalyzerValidator(BaseValidator):
    """分析器组件校验器"""
    
    def __init__(self):
        super().__init__()
        self.rules = ValidationRules.get_rules('analyzer')
        self.required_base_class = self.rules['required_base_class']
        self.required_methods = self.rules['required_methods']
    
    def validate_component_specific(self, module: Any) -> List[ValidationResult]:
        """
        分析器组件特定校验
        
        Args:
            module: 动态加载的分析器模块
            
        Returns:
            List[ValidationResult]: 校验结果列表
        """
        results = []
        
        # 1. 查找分析器类
        analyzer_classes = self._find_analyzer_classes(module)
        if not analyzer_classes:
            results.append(ValidationResult(
                is_valid=False,
                level=ValidationLevel.ERROR,
                message="No analyzer class found",
                details=f"Must define a class that inherits from {self.required_base_class}",
                suggestions=[
                    f"Create a class that inherits from {self.required_base_class}",
                    "Import the base class: from ginkgo.trading.analysis.analyzers.base_analyzer import BaseAnalyzer"
                ]
            ))
            return results
        
        # 2. 校验每个分析器类
        for analyzer_class in analyzer_classes:
            class_results = self._validate_analyzer_class(analyzer_class)
            results.extend(class_results)
        
        # 3. 校验代码安全性
        security_result = self._validate_security(module)
        results.append(security_result)
        
        # 4. 校验必需的导入
        import_result = self._validate_required_imports(module)
        results.append(import_result)
        
        return results
    
    def _find_analyzer_classes(self, module: Any) -> List[type]:
        """
        查找分析器类
        
        Args:
            module: 模块对象
            
        Returns:
            List[type]: 分析器类列表
        """
        analyzer_classes = []
        
        for name in dir(module):
            obj = getattr(module, name)
            if (inspect.isclass(obj) and 
                hasattr(obj, '__bases__') and
                any(base.__name__ == self.required_base_class for base in obj.__mro__)):
                analyzer_classes.append(obj)
        
        return analyzer_classes
    
    def _validate_analyzer_class(self, analyzer_class: type) -> List[ValidationResult]:
        """
        校验分析器类
        
        Args:
            analyzer_class: 分析器类
            
        Returns:
            List[ValidationResult]: 校验结果列表
        """
        results = []
        
        # 1. 校验基类继承
        inheritance_result = self._validate_inheritance(analyzer_class)
        results.append(inheritance_result)
        
        # 2. 校验必需方法
        for method_sig in self.required_methods:
            method_result = self._validate_method(analyzer_class, method_sig)
            results.append(method_result)
        
        # 3. 校验构造函数
        constructor_result = self._validate_constructor(analyzer_class)
        results.append(constructor_result)
        
        # 4. 校验分析器特定属性
        attributes_result = self._validate_analyzer_attributes(analyzer_class)
        results.append(attributes_result)
        
        return results
    
    def _validate_inheritance(self, analyzer_class: type) -> ValidationResult:
        """
        校验基类继承
        
        Args:
            analyzer_class: 分析器类
            
        Returns:
            ValidationResult: 校验结果
        """
        base_class_names = [base.__name__ for base in analyzer_class.__mro__]
        
        if self.required_base_class not in base_class_names:
            return ValidationResult(
                is_valid=False,
                level=ValidationLevel.ERROR,
                message=f"Class {analyzer_class.__name__} does not inherit from {self.required_base_class}",
                details=f"Current inheritance: {' -> '.join(base_class_names)}",
                suggestions=[
                    f"Make your class inherit from {self.required_base_class}",
                    f"Example: class MyAnalyzer({self.required_base_class}):"
                ]
            )
        
        return ValidationResult(
            is_valid=True,
            level=ValidationLevel.INFO,
            message=f"Inheritance validation passed for {analyzer_class.__name__}",
            details=f"Correctly inherits from {self.required_base_class}"
        )
    
    def _validate_method(self, analyzer_class: type, method_sig) -> ValidationResult:
        """
        校验方法实现
        
        Args:
            analyzer_class: 分析器类
            method_sig: 方法签名定义
            
        Returns:
            ValidationResult: 校验结果
        """
        method_name = method_sig.name
        
        # 检查方法是否存在
        if not hasattr(analyzer_class, method_name):
            return ValidationResult(
                is_valid=False,
                level=ValidationLevel.ERROR,
                message=f"Required method '{method_name}' not found",
                details=f"Class {analyzer_class.__name__} must implement {method_name} method",
                suggestions=[
                    f"Add the {method_name} method to your class",
                    f"Method signature: def {method_name}({', '.join(method_sig.required_args)}):"
                ]
            )
        
        # 获取方法对象
        method = getattr(analyzer_class, method_name)
        
        # 检查是否为方法
        if not callable(method):
            return ValidationResult(
                is_valid=False,
                level=ValidationLevel.ERROR,
                message=f"'{method_name}' is not callable",
                details=f"{method_name} must be a method, not {type(method).__name__}"
            )
        
        # 校验方法签名
        try:
            sig = inspect.signature(method)
            param_names = list(sig.parameters.keys())
            
            # 检查必需参数
            missing_params = []
            for required_arg in method_sig.required_args:
                if required_arg not in param_names:
                    missing_params.append(required_arg)
            
            if missing_params:
                return ValidationResult(
                    is_valid=False,
                    level=ValidationLevel.ERROR,
                    message=f"Method '{method_name}' missing required parameters",
                    details=f"Missing: {', '.join(missing_params)}",
                    suggestions=[
                        f"Update method signature to include: {', '.join(missing_params)}",
                        f"Expected signature: def {method_name}({', '.join(method_sig.required_args)}):"
                    ]
                )
            
            # 使用AST分析检查方法实现质量
            implementation_result = self._validate_method_implementation(method, method_name)
            if not implementation_result.is_valid:
                return implementation_result
            
        except Exception as e:
            return ValidationResult(
                is_valid=False,
                level=ValidationLevel.WARNING,
                message=f"Could not validate method signature for '{method_name}'",
                details=str(e)
            )
        
        return ValidationResult(
            is_valid=True,
            level=ValidationLevel.INFO,
            message=f"Method '{method_name}' validation passed",
            details=f"Method signature is correct"
        )
    
    def _validate_constructor(self, analyzer_class: type) -> ValidationResult:
        """
        校验构造函数
        
        Args:
            analyzer_class: 分析器类
            
        Returns:
            ValidationResult: 校验结果
        """
        try:
            # 尝试实例化（使用默认参数）
            instance = analyzer_class("test_analyzer")
            
            # 检查基本属性
            required_attrs = ['name', '_active_stage', '_record_stage', '_data']
            missing_attrs = []
            
            for attr in required_attrs:
                if not hasattr(instance, attr):
                    missing_attrs.append(attr)
            
            if missing_attrs:
                return ValidationResult(
                    is_valid=False,
                    level=ValidationLevel.WARNING,
                    message="Constructor may not properly initialize base class",
                    details=f"Missing attributes: {', '.join(missing_attrs)}",
                    suggestions=[
                        "Call super().__init__() in your constructor",
                        "Ensure base class is properly initialized"
                    ]
                )
            
            return ValidationResult(
                is_valid=True,
                level=ValidationLevel.INFO,
                message="Constructor validation passed",
                details="Class can be instantiated and has required attributes"
            )
            
        except Exception as e:
            return ValidationResult(
                is_valid=False,
                level=ValidationLevel.ERROR,
                message="Constructor validation failed",
                details=f"Cannot instantiate class: {str(e)}",
                suggestions=[
                    "Check constructor parameters",
                    "Ensure constructor accepts at least a 'name' parameter",
                    "Call super().__init__(name) in constructor"
                ]
            )
    
    def _validate_analyzer_attributes(self, analyzer_class: type) -> ValidationResult:
        """
        校验分析器特定属性
        
        Args:
            analyzer_class: 分析器类
            
        Returns:
            ValidationResult: 校验结果
        """
        try:
            instance = analyzer_class("test_analyzer")
            
            # 检查stage配置方法
            stage_methods = ['add_active_stage', 'set_record_stage']
            missing_methods = []
            
            for method in stage_methods:
                if not hasattr(instance, method) or not callable(getattr(instance, method)):
                    missing_methods.append(method)
            
            if missing_methods:
                return ValidationResult(
                    is_valid=False,
                    level=ValidationLevel.WARNING,
                    message="Missing stage configuration methods",
                    details=f"Missing: {', '.join(missing_methods)}",
                    suggestions=[
                        "Ensure base class is properly inherited",
                        "These methods should be available from BaseAnalyzer"
                    ]
                )
            
            # 检查数据管理方法
            data_methods = ['add_data', 'get_data']
            missing_data_methods = []
            
            for method in data_methods:
                if not hasattr(instance, method) or not callable(getattr(instance, method)):
                    missing_data_methods.append(method)
            
            if missing_data_methods:
                return ValidationResult(
                    is_valid=False,
                    level=ValidationLevel.WARNING,
                    message="Missing data management methods",
                    details=f"Missing: {', '.join(missing_data_methods)}",
                    suggestions=[
                        "Ensure base class is properly inherited",
                        "These methods should be available from BaseAnalyzer"
                    ]
                )
            
            return ValidationResult(
                is_valid=True,
                level=ValidationLevel.INFO,
                message="Analyzer attributes validation passed",
                details="All required methods and attributes are available"
            )
            
        except Exception as e:
            return ValidationResult(
                is_valid=False,
                level=ValidationLevel.WARNING,
                message="Could not validate analyzer attributes",
                details=str(e)
            )
    
    def _validate_security(self, module: Any) -> ValidationResult:
        """
        校验代码安全性
        
        Args:
            module: 模块对象
            
        Returns:
            ValidationResult: 校验结果
        """
        try:
            # 获取模块源代码
            source = inspect.getsource(module)
            
            # 检查禁止的操作
            forbidden_ops = self.rules.get('forbidden_operations', [])
            found_forbidden = []
            
            for op in forbidden_ops:
                if op in source:
                    found_forbidden.append(op)
            
            if found_forbidden:
                return ValidationResult(
                    is_valid=False,
                    level=ValidationLevel.ERROR,
                    message="Forbidden operations detected",
                    details=f"Found: {', '.join(found_forbidden)}",
                    suggestions=[
                        "Remove dangerous operations from your code",
                        "Use only Ginkgo framework APIs for data access"
                    ]
                )
            
            # 检查必需的代码模式
            required_patterns = ValidationRules.get_required_patterns('analyzer')
            missing_patterns = []
            
            for pattern in required_patterns:
                if not re.search(pattern, source):
                    missing_patterns.append(pattern)
            
            if missing_patterns:
                return ValidationResult(
                    is_valid=False,
                    level=ValidationLevel.WARNING,
                    message="Some expected patterns not found",
                    details=f"Missing patterns: {len(missing_patterns)}",
                    suggestions=[
                        "Ensure your analyzer follows the expected structure",
                        "Check that you implement _do_activate and _do_record methods"
                    ]
                )
            
            return ValidationResult(
                is_valid=True,
                level=ValidationLevel.INFO,
                message="Security validation passed",
                details="No forbidden operations detected"
            )
            
        except Exception as e:
            return ValidationResult(
                is_valid=False,
                level=ValidationLevel.WARNING,
                message="Could not validate security",
                details=str(e)
            )
    
    def _validate_required_imports(self, module: Any) -> ValidationResult:
        """
        校验必需的导入
        
        Args:
            module: 模块对象
            
        Returns:
            ValidationResult: 校验结果
        """
        try:
            # 获取模块源代码
            source = inspect.getsource(module)
            
            # 解析导入
            tree = ast.parse(source)
            imports = set()
            
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        imports.add(alias.name)
                elif isinstance(node, ast.ImportFrom):
                    if node.module:
                        imports.add(node.module)
            
            # 检查必需的导入
            required_imports = self.rules.get('required_imports', [])
            missing_imports = []
            
            for required in required_imports:
                if not any(required in imp for imp in imports):
                    missing_imports.append(required)
            
            if missing_imports:
                return ValidationResult(
                    is_valid=False,
                    level=ValidationLevel.ERROR,
                    message="Missing required imports",
                    details=f"Missing: {', '.join(missing_imports)}",
                    suggestions=[
                        f"Add import: from {imp} import ..." for imp in missing_imports
                    ]
                )
            
            return ValidationResult(
                is_valid=True,
                level=ValidationLevel.INFO,
                message="Import validation passed",
                details=f"Found {len(imports)} imports"
            )
            
        except Exception as e:
            return ValidationResult(
                is_valid=False,
                level=ValidationLevel.WARNING,
                message="Could not validate imports",
                details=str(e)
            )
    
    def _validate_method_implementation(self, method: Any, method_name: str) -> ValidationResult:
        """
        使用AST分析验证方法实现质量
        
        Args:
            method: 方法对象
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
            
            # 分析方法体
            method_body = None
            for node in ast.walk(tree):
                if isinstance(node, ast.FunctionDef) and node.name == method_name:
                    method_body = node.body
                    break
            
            if not method_body:
                return ValidationResult(
                    is_valid=False,
                    level=ValidationLevel.ERROR,
                    message=f"Could not analyze method '{method_name}' body",
                    details="Method structure could not be parsed"
                )
            
            # 检查是否只有pass语句
            if len(method_body) == 1 and isinstance(method_body[0], ast.Pass):
                return ValidationResult(
                    is_valid=False,
                    level=ValidationLevel.WARNING,
                    message=f"Method '{method_name}' appears to be a stub",
                    details="Method only contains 'pass' statement",
                    suggestions=[
                        f"Implement the logic for {method_name} method",
                        "Add meaningful code to perform analyzer calculations"
                    ]
                )
            
            # 检查是否抛出NotImplementedError
            for stmt in method_body:
                if isinstance(stmt, ast.Raise):
                    if isinstance(stmt.exc, ast.Call) and isinstance(stmt.exc.func, ast.Name):
                        if stmt.exc.func.id == 'NotImplementedError':
                            return ValidationResult(
                                is_valid=False,
                                level=ValidationLevel.ERROR,
                                message=f"Method '{method_name}' raises NotImplementedError",
                                details="Method must be implemented",
                                suggestions=[
                                    f"Replace NotImplementedError with actual implementation",
                                    "Implement the required analyzer logic"
                                ]
                            )
                    elif isinstance(stmt.exc, ast.Name) and stmt.exc.id == 'NotImplementedError':
                        return ValidationResult(
                            is_valid=False,
                            level=ValidationLevel.ERROR,
                            message=f"Method '{method_name}' raises NotImplementedError",
                            details="Method must be implemented",
                            suggestions=[
                                f"Replace NotImplementedError with actual implementation",
                                "Implement the required analyzer logic"
                            ]
                        )
            
            # 检查方法复杂度（语句数量）
            total_statements = len(method_body)
            if total_statements == 1:
                # 单语句方法，检查是否有意义
                stmt = method_body[0]
                if isinstance(stmt, ast.Return):
                    return ValidationResult(
                        is_valid=False,
                        level=ValidationLevel.WARNING,
                        message=f"Method '{method_name}' has minimal implementation",
                        details="Method only contains a return statement",
                        suggestions=[
                            "Add analyzer logic before returning",
                            "Consider data processing, calculations, or state updates"
                        ]
                    )
            
            return ValidationResult(
                is_valid=True,
                level=ValidationLevel.INFO,
                message=f"Method '{method_name}' implementation validation passed",
                details=f"Method has {total_statements} statements and appears to be implemented"
            )
            
        except Exception as e:
            return ValidationResult(
                is_valid=True,
                level=ValidationLevel.WARNING,
                message=f"Could not validate method implementation for '{method_name}'",
                details=f"Analysis error: {str(e)}",
                suggestions=["Manual review of method implementation recommended"]
            )