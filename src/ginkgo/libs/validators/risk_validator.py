# Upstream: All Modules
# Downstream: Standard Library
# Role: Risk Validator RiskValidator风控验证器检查风控组件配置合理性提供相关功能和接口实现






"""
风控组件校验器
专门用于校验用户自定义的风控组件
"""

import ast
import inspect
import re
from typing import List, Any

from ginkgo.libs.validators.base_validator import BaseValidator, ValidationResult, ValidationLevel
from ginkgo.libs.validators.validation_rules import ValidationRules


class RiskValidator(BaseValidator):
    """风控组件校验器"""
    
    def __init__(self):
        super().__init__()
        self.rules = ValidationRules.get_rules('risk')
        self.required_base_class = self.rules['required_base_class']
        self.required_methods = self.rules['required_methods']
    
    def validate_component_specific(self, module: Any) -> List[ValidationResult]:
        """
        风控组件特定校验
        
        Args:
            module: 动态加载的风控模块
            
        Returns:
            List[ValidationResult]: 校验结果列表
        """
        results = []
        
        # 1. 查找风控类
        risk_classes = self._find_risk_classes(module)
        if not risk_classes:
            results.append(ValidationResult(
                is_valid=False,
                level=ValidationLevel.ERROR,
                message="No risk management class found",
                details=f"Must define a class that inherits from {self.required_base_class}",
                suggestions=[
                    f"Create a class that inherits from {self.required_base_class}",
                    "Import the base class: from ginkgo.trading.risk_managementss.base_risk import BaseRiskManagement"
                ]
            ))
            return results
        
        # 2. 校验每个风控类
        for risk_class in risk_classes:
            class_results = self._validate_risk_class(risk_class)
            results.extend(class_results)
        
        # 3. 校验代码安全性
        security_result = self._validate_security(module)
        results.append(security_result)
        
        # 4. 校验必需的导入
        import_result = self._validate_required_imports(module)
        results.append(import_result)
        
        return results
    
    def _find_risk_classes(self, module: Any) -> List[type]:
        """
        查找风控类
        
        Args:
            module: 模块对象
            
        Returns:
            List[type]: 风控类列表
        """
        risk_classes = []
        
        for name in dir(module):
            obj = getattr(module, name)
            if (inspect.isclass(obj) and 
                hasattr(obj, '__bases__') and
                any(base.__name__ == self.required_base_class for base in obj.__mro__)):
                risk_classes.append(obj)
        
        return risk_classes
    
    def _validate_risk_class(self, risk_class: type) -> List[ValidationResult]:
        """
        校验风控类
        
        Args:
            risk_class: 风控类
            
        Returns:
            List[ValidationResult]: 校验结果列表
        """
        results = []
        
        # 1. 校验基类继承
        inheritance_result = self._validate_inheritance(risk_class)
        results.append(inheritance_result)
        
        # 2. 校验必需方法
        for method_sig in self.required_methods:
            method_result = self._validate_method(risk_class, method_sig)
            results.append(method_result)
        
        # 3. 校验构造函数
        constructor_result = self._validate_constructor(risk_class)
        results.append(constructor_result)
        
        # 4. 校验风控特定逻辑
        risk_logic_result = self._validate_risk_logic(risk_class)
        results.append(risk_logic_result)
        
        return results
    
    def _validate_inheritance(self, risk_class: type) -> ValidationResult:
        """
        校验基类继承
        
        Args:
            risk_class: 风控类
            
        Returns:
            ValidationResult: 校验结果
        """
        base_class_names = [base.__name__ for base in risk_class.__mro__]
        
        if self.required_base_class not in base_class_names:
            return ValidationResult(
                is_valid=False,
                level=ValidationLevel.ERROR,
                message=f"Class {risk_class.__name__} does not inherit from {self.required_base_class}",
                details=f"Current inheritance: {' -> '.join(base_class_names)}",
                suggestions=[
                    f"Make your class inherit from {self.required_base_class}",
                    f"Example: class MyRiskManager({self.required_base_class}):"
                ]
            )
        
        return ValidationResult(
            is_valid=True,
            level=ValidationLevel.INFO,
            message=f"Inheritance validation passed for {risk_class.__name__}",
            details=f"Correctly inherits from {self.required_base_class}"
        )
    
    def _validate_method(self, risk_class: type, method_sig) -> ValidationResult:
        """
        校验方法实现
        
        Args:
            risk_class: 风控类
            method_sig: 方法签名定义
            
        Returns:
            ValidationResult: 校验结果
        """
        method_name = method_sig.name
        
        # 检查方法是否存在
        if not hasattr(risk_class, method_name):
            return ValidationResult(
                is_valid=False,
                level=ValidationLevel.ERROR,
                message=f"Required method '{method_name}' not found",
                details=f"Class {risk_class.__name__} must implement {method_name} method",
                suggestions=[
                    f"Add the {method_name} method to your class",
                    f"Method signature: def {method_name}({', '.join(method_sig.required_args)}):"
                ]
            )
        
        # 获取方法对象
        method = getattr(risk_class, method_name)
        
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
            if method_sig.return_type:
                if method_name == 'cal':
                    # cal方法应该返回Order或None
                    return_type_result = self._validate_method_return_type(
                        method, ['Order', 'None'], method_name
                    )
                    if not return_type_result.is_valid:
                        return return_type_result
                elif method_name == 'generate_signals':
                    # generate_signals方法应该返回List[Signal]
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
    
    def _validate_constructor(self, risk_class: type) -> ValidationResult:
        """
        校验构造函数
        
        Args:
            risk_class: 风控类
            
        Returns:
            ValidationResult: 校验结果
        """
        try:
            # 尝试实例化（使用默认参数）
            instance = risk_class()
            
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
    
    def _validate_risk_logic(self, risk_class: type) -> ValidationResult:
        """
        校验风控特定逻辑
        
        Args:
            risk_class: 风控类
            
        Returns:
            ValidationResult: 校验结果
        """
        try:
            # 使用AST分析检查cal方法的风控逻辑
            if hasattr(risk_class, 'cal'):
                cal_method = getattr(risk_class, 'cal')
                cal_logic_result = self._validate_risk_method_logic(cal_method, 'cal')
                if not cal_logic_result.is_valid:
                    return cal_logic_result
            
            # 使用AST分析检查generate_signals方法的逻辑
            if hasattr(risk_class, 'generate_signals'):
                generate_method = getattr(risk_class, 'generate_signals')
                generate_logic_result = self._validate_risk_method_logic(generate_method, 'generate_signals')
                if not generate_logic_result.is_valid:
                    return generate_logic_result
            
            return ValidationResult(
                is_valid=True,
                level=ValidationLevel.INFO,
                message="Risk logic validation passed",
                details="Risk management methods are properly implemented"
            )
            
        except Exception as e:
            return ValidationResult(
                is_valid=False,
                level=ValidationLevel.WARNING,
                message="Could not validate risk logic",
                details=str(e)
            )
    
    def _validate_risk_method_logic(self, method: Any, method_name: str) -> ValidationResult:
        """
        使用AST分析验证风控方法的逻辑实现
        
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
                        "Add meaningful risk management logic"
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
                                details="Method must be implemented with actual risk management logic",
                                suggestions=[
                                    f"Replace NotImplementedError with actual implementation",
                                    "Implement risk management calculations and order filtering"
                                ]
                            )
                    elif isinstance(stmt.exc, ast.Name) and stmt.exc.id == 'NotImplementedError':
                        return ValidationResult(
                            is_valid=False,
                            level=ValidationLevel.ERROR,
                            message=f"Method '{method_name}' raises NotImplementedError",
                            details="Method must be implemented with actual risk management logic",
                            suggestions=[
                                f"Replace NotImplementedError with actual implementation",
                                "Implement risk management calculations and order filtering"
                            ]
                        )
            
            # 针对不同方法的特定检查
            if method_name == 'cal':
                # cal方法应该有风控逻辑
                has_portfolio_usage = False
                has_order_logic = False
                
                # 检查是否使用了portfolio_info参数
                for node in ast.walk(tree):
                    if isinstance(node, ast.Attribute):
                        if isinstance(node.value, ast.Name) and node.value.id == 'portfolio_info':
                            has_portfolio_usage = True
                        elif isinstance(node.value, ast.Name) and node.value.id == 'order':
                            has_order_logic = True
                
                # 检查是否只是简单返回order
                if len(method_body) == 1 and isinstance(method_body[0], ast.Return):
                    return ValidationResult(
                        is_valid=False,
                        level=ValidationLevel.WARNING,
                        message=f"Method '{method_name}' appears to be a stub",
                        details="cal method should implement risk management logic",
                        suggestions=[
                            "Add risk management logic to evaluate order safety",
                            "Consider portfolio cash, positions, and risk limits",
                            "Implement order filtering or modification logic"
                        ]
                    )
                
                # 检查是否使用了portfolio_info
                if not has_portfolio_usage:
                    return ValidationResult(
                        is_valid=False,
                        level=ValidationLevel.WARNING,
                        message=f"Method '{method_name}' doesn't use portfolio_info",
                        details="Risk management should consider portfolio state",
                        suggestions=[
                            "Use portfolio_info to access cash, positions, worth, etc.",
                            "Consider current portfolio risk exposure",
                            "Implement position size limits and risk controls"
                        ]
                    )
                
            elif method_name == 'generate_signals':
                # generate_signals方法可以是简单的空列表返回
                # 检查是否只是简单返回空列表
                if len(method_body) == 1 and isinstance(method_body[0], ast.Return):
                    ret_stmt = method_body[0]
                    if isinstance(ret_stmt.value, ast.List) and len(ret_stmt.value.elts) == 0:
                        return ValidationResult(
                            is_valid=True,
                            level=ValidationLevel.INFO,
                            message="generate_signals method is basic but valid",
                            details="Method returns empty list - this is acceptable for passive risk management"
                        )
            
            return ValidationResult(
                is_valid=True,
                level=ValidationLevel.INFO,
                message=f"Method '{method_name}' logic validation passed",
                details=f"Method appears to have proper risk management logic"
            )
            
        except Exception as e:
            return ValidationResult(
                is_valid=True,
                level=ValidationLevel.WARNING,
                message=f"Could not validate method logic for '{method_name}'",
                details=f"Analysis error: {str(e)}",
                suggestions=["Manual review of method implementation recommended"]
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
            required_patterns = ValidationRules.get_required_patterns('risk')
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
                        "Ensure your risk manager follows the expected structure",
                        "Check that you implement both cal and generate_signals methods"
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