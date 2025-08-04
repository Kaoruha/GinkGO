"""
策略组件校验器
专门用于校验用户自定义的策略组件
"""

import ast
import inspect
import re
from typing import List, Any

from .base_validator import BaseValidator, ValidationResult, ValidationLevel
from .validation_rules import ValidationRules


class StrategyValidator(BaseValidator):
    """策略组件校验器"""
    
    def __init__(self):
        super().__init__()
        self.rules = ValidationRules.get_rules('strategy')
        self.required_base_class = self.rules['required_base_class']
        self.required_methods = self.rules['required_methods']
    
    def validate_component_specific(self, module: Any) -> List[ValidationResult]:
        """
        策略组件特定校验
        
        Args:
            module: 动态加载的策略模块
            
        Returns:
            List[ValidationResult]: 校验结果列表
        """
        results = []
        
        # 1. 查找策略类
        strategy_classes = self._find_strategy_classes(module)
        if not strategy_classes:
            results.append(ValidationResult(
                is_valid=False,
                level=ValidationLevel.ERROR,
                message="No strategy class found",
                details=f"Must define a class that inherits from {self.required_base_class}",
                suggestions=[
                    f"Create a class that inherits from {self.required_base_class}",
                    "Import the base class: from ginkgo.backtest.strategy.strategies.base_strategy import StrategyBase"
                ]
            ))
            return results
        
        # 2. 校验每个策略类
        for strategy_class in strategy_classes:
            class_results = self._validate_strategy_class(strategy_class)
            results.extend(class_results)
        
        # 3. 校验代码安全性
        security_result = self._validate_security(module)
        results.append(security_result)
        
        # 4. 校验必需的导入
        import_result = self._validate_required_imports(module)
        results.append(import_result)
        
        return results
    
    def _find_strategy_classes(self, module: Any) -> List[type]:
        """
        查找策略类
        
        Args:
            module: 模块对象
            
        Returns:
            List[type]: 策略类列表
        """
        strategy_classes = []
        
        for name in dir(module):
            obj = getattr(module, name)
            if (inspect.isclass(obj) and 
                hasattr(obj, '__bases__') and
                any(base.__name__ == self.required_base_class for base in obj.__mro__)):
                strategy_classes.append(obj)
        
        return strategy_classes
    
    def _validate_strategy_class(self, strategy_class: type) -> List[ValidationResult]:
        """
        校验策略类
        
        Args:
            strategy_class: 策略类
            
        Returns:
            List[ValidationResult]: 校验结果列表
        """
        results = []
        
        # 1. 校验基类继承
        inheritance_result = self._validate_inheritance(strategy_class)
        results.append(inheritance_result)
        
        # 2. 校验必需方法
        for method_sig in self.required_methods:
            method_result = self._validate_method(strategy_class, method_sig)
            results.append(method_result)
        
        # 3. 校验构造函数
        constructor_result = self._validate_constructor(strategy_class)
        results.append(constructor_result)
        
        return results
    
    def _validate_inheritance(self, strategy_class: type) -> ValidationResult:
        """
        校验基类继承
        
        Args:
            strategy_class: 策略类
            
        Returns:
            ValidationResult: 校验结果
        """
        base_class_names = [base.__name__ for base in strategy_class.__mro__]
        
        if self.required_base_class not in base_class_names:
            return ValidationResult(
                is_valid=False,
                level=ValidationLevel.ERROR,
                message=f"Class {strategy_class.__name__} does not inherit from {self.required_base_class}",
                details=f"Current inheritance: {' -> '.join(base_class_names)}",
                suggestions=[
                    f"Make your class inherit from {self.required_base_class}",
                    f"Example: class MyStrategy({self.required_base_class}):"
                ]
            )
        
        return ValidationResult(
            is_valid=True,
            level=ValidationLevel.INFO,
            message=f"Inheritance validation passed for {strategy_class.__name__}",
            details=f"Correctly inherits from {self.required_base_class}"
        )
    
    def _validate_method(self, strategy_class: type, method_sig) -> ValidationResult:
        """
        校验方法实现
        
        Args:
            strategy_class: 策略类
            method_sig: 方法签名定义
            
        Returns:
            ValidationResult: 校验结果
        """
        method_name = method_sig.name
        
        # 检查方法是否存在
        if not hasattr(strategy_class, method_name):
            return ValidationResult(
                is_valid=False,
                level=ValidationLevel.ERROR,
                message=f"Required method '{method_name}' not found",
                details=f"Class {strategy_class.__name__} must implement {method_name} method",
                suggestions=[
                    f"Add the {method_name} method to your class",
                    f"Method signature: def {method_name}({', '.join(method_sig.required_args)}):"
                ]
            )
        
        # 获取方法对象
        method = getattr(strategy_class, method_name)
        
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
            
            # 使用AST分析检查返回类型
            if method_sig.return_type and method_name == 'cal':
                # cal方法应该返回List[Signal]
                return_type_result = self._validate_method_return_type(
                    method, ['List[Signal]', 'List', '[]'], method_name
                )
                if not return_type_result.is_valid:
                    return return_type_result
            
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
    
    def _validate_constructor(self, strategy_class: type) -> ValidationResult:
        """
        校验构造函数
        
        Args:
            strategy_class: 策略类
            
        Returns:
            ValidationResult: 校验结果
        """
        try:
            # 尝试实例化（使用默认参数）
            instance = strategy_class()
            
            # 检查基本属性
            required_attrs = ['name', '_data_feeder']
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
                    "Ensure all required dependencies are available",
                    "Call super().__init__() in constructor"
                ]
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
            required_patterns = ValidationRules.get_required_patterns('strategy')
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
                        "Ensure your strategy follows the expected structure",
                        "Check that you're returning the correct types"
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