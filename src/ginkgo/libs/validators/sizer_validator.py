"""
仓位管理组件校验器
专门用于校验用户自定义的仓位管理组件
"""

import ast
import inspect
import re
from typing import List, Any

from ginkgo.libs.validators.base_validator import BaseValidator, ValidationResult, ValidationLevel
from ginkgo.libs.validators.validation_rules import ValidationRules


class SizerValidator(BaseValidator):
    """仓位管理组件校验器"""
    
    def __init__(self):
        super().__init__()
        self.rules = ValidationRules.get_rules('sizer')
        self.required_base_class = self.rules['required_base_class']
        self.required_methods = self.rules['required_methods']
    
    def validate_component_specific(self, module: Any) -> List[ValidationResult]:
        """
        仓位管理组件特定校验
        
        Args:
            module: 动态加载的仓位管理模块
            
        Returns:
            List[ValidationResult]: 校验结果列表
        """
        results = []
        
        # 1. 查找仓位管理类
        sizer_classes = self._find_sizer_classes(module)
        if not sizer_classes:
            results.append(ValidationResult(
                is_valid=False,
                level=ValidationLevel.ERROR,
                message="No sizer class found",
                details=f"Must define a class that inherits from {self.required_base_class}",
                suggestions=[
                    f"Create a class that inherits from {self.required_base_class}",
                    "Import the base class: from ginkgo.trading.sizers.base_sizer import BaseSizer"
                ]
            ))
            return results
        
        # 2. 校验每个仓位管理类
        for sizer_class in sizer_classes:
            class_results = self._validate_sizer_class(sizer_class)
            results.extend(class_results)
        
        # 3. 校验代码安全性
        security_result = self._validate_security(module)
        results.append(security_result)
        
        # 4. 校验必需的导入
        import_result = self._validate_required_imports(module)
        results.append(import_result)
        
        return results
    
    def _find_sizer_classes(self, module: Any) -> List[type]:
        """
        查找仓位管理类
        
        Args:
            module: 模块对象
            
        Returns:
            List[type]: 仓位管理类列表
        """
        sizer_classes = []
        
        for name in dir(module):
            obj = getattr(module, name)
            if (inspect.isclass(obj) and 
                hasattr(obj, '__bases__') and
                any(base.__name__ == self.required_base_class for base in obj.__mro__)):
                sizer_classes.append(obj)
        
        return sizer_classes
    
    def _validate_sizer_class(self, sizer_class: type) -> List[ValidationResult]:
        """
        校验仓位管理类
        
        Args:
            sizer_class: 仓位管理类
            
        Returns:
            List[ValidationResult]: 校验结果列表
        """
        results = []
        
        # 1. 校验基类继承
        inheritance_result = self._validate_inheritance(sizer_class)
        results.append(inheritance_result)
        
        # 2. 校验必需方法
        for method_sig in self.required_methods:
            method_result = self._validate_method(sizer_class, method_sig)
            results.append(method_result)
        
        # 3. 校验构造函数
        constructor_result = self._validate_constructor(sizer_class)
        results.append(constructor_result)
        
        # 4. 校验仓位计算逻辑
        sizing_logic_result = self._validate_sizing_logic(sizer_class)
        results.append(sizing_logic_result)
        
        return results
    
    def _validate_inheritance(self, sizer_class: type) -> ValidationResult:
        """
        校验基类继承
        
        Args:
            sizer_class: 仓位管理类
            
        Returns:
            ValidationResult: 校验结果
        """
        base_class_names = [base.__name__ for base in sizer_class.__mro__]
        
        if self.required_base_class not in base_class_names:
            return ValidationResult(
                is_valid=False,
                level=ValidationLevel.ERROR,
                message=f"Class {sizer_class.__name__} does not inherit from {self.required_base_class}",
                details=f"Current inheritance: {' -> '.join(base_class_names)}",
                suggestions=[
                    f"Make your class inherit from {self.required_base_class}",
                    f"Example: class MySizer({self.required_base_class}):"
                ]
            )
        
        return ValidationResult(
            is_valid=True,
            level=ValidationLevel.INFO,
            message=f"Inheritance validation passed for {sizer_class.__name__}",
            details=f"Correctly inherits from {self.required_base_class}"
        )
    
    def _validate_method(self, sizer_class: type, method_sig) -> ValidationResult:
        """
        校验方法实现
        
        Args:
            sizer_class: 仓位管理类
            method_sig: 方法签名定义
            
        Returns:
            ValidationResult: 校验结果
        """
        method_name = method_sig.name
        
        # 检查方法是否存在
        if not hasattr(sizer_class, method_name):
            return ValidationResult(
                is_valid=False,
                level=ValidationLevel.ERROR,
                message=f"Required method '{method_name}' not found",
                details=f"Class {sizer_class.__name__} must implement {method_name} method",
                suggestions=[
                    f"Add the {method_name} method to your class",
                    f"Method signature: def {method_name}({', '.join(method_sig.required_args)}):"
                ]
            )
        
        # 获取方法对象
        method = getattr(sizer_class, method_name)
        
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
            
            # 使用AST分析检查返回类型
            if method_sig.return_type and method_name == 'cal':
                # cal方法应该返回修改后的Signal
                return_type_result = self._validate_method_return_type(
                    method, ['Signal', 'signal'], method_name
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
    
    def _validate_constructor(self, sizer_class: type) -> ValidationResult:
        """
        校验构造函数
        
        Args:
            sizer_class: 仓位管理类
            
        Returns:
            ValidationResult: 校验结果
        """
        try:
            # 尝试实例化（使用默认参数）
            instance = sizer_class()
            
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
    
    def _validate_sizing_logic(self, sizer_class: type) -> ValidationResult:
        """
        校验仓位计算逻辑
        
        Args:
            sizer_class: 仓位管理类
            
        Returns:
            ValidationResult: 校验结果
        """
        try:
            # 检查cal方法的逻辑
            if hasattr(sizer_class, 'cal'):
                cal_method = getattr(sizer_class, 'cal')
                try:
                    source = inspect.getsource(cal_method)
                    
                    # 检查是否使用了portfolio_info参数
                    if 'portfolio_info' not in source:
                        return ValidationResult(
                            is_valid=False,
                            level=ValidationLevel.WARNING,
                            message="Sizing method doesn't use portfolio_info",
                            details="Position sizing should consider portfolio state",
                            suggestions=[
                                "Use portfolio_info to access cash, positions, worth, etc.",
                                "Calculate position size based on available cash",
                                "Consider risk management in position sizing"
                            ]
                        )
                    
                    # 检查是否修改了signal的quantity
                    if 'signal.quantity' not in source and 'quantity' not in source:
                        return ValidationResult(
                            is_valid=False,
                            level=ValidationLevel.WARNING,
                            message="Sizing method may not modify signal quantity",
                            details="Sizer should calculate and set appropriate position size",
                            suggestions=[
                                "Modify signal.quantity based on sizing calculations",
                                "Calculate quantity based on cash, price, and risk limits",
                                "Return the modified signal object"
                            ]
                        )
                    
                    # 检查是否考虑了风险管理
                    risk_keywords = ['cash', 'worth', 'risk', 'limit', 'percentage', 'ratio']
                    has_risk_consideration = any(keyword in source.lower() for keyword in risk_keywords)
                    
                    if not has_risk_consideration:
                        return ValidationResult(
                            is_valid=True,
                            level=ValidationLevel.INFO,
                            message="Consider adding risk management to sizing logic",
                            details="Position sizing could benefit from risk considerations",
                            suggestions=[
                                "Consider portfolio cash limits",
                                "Implement percentage-based position sizing",
                                "Add risk management calculations"
                            ]
                        )
                        
                except:
                    pass  # 无法获取源代码时忽略
            
            return ValidationResult(
                is_valid=True,
                level=ValidationLevel.INFO,
                message="Sizing logic validation passed",
                details="Position sizing method is properly implemented"
            )
            
        except Exception as e:
            return ValidationResult(
                is_valid=False,
                level=ValidationLevel.WARNING,
                message="Could not validate sizing logic",
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
            required_patterns = ValidationRules.get_required_patterns('sizer')
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
                        "Ensure your sizer follows the expected structure",
                        "Check that you implement the cal method properly"
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
            
            # 检查是否抛出NotImplementedError
            for stmt in method_body:
                if isinstance(stmt, ast.Raise):
                    if isinstance(stmt.exc, ast.Call) and isinstance(stmt.exc.func, ast.Name):
                        if stmt.exc.func.id in ['NotImplementedError', 'NotImplemented']:
                            return ValidationResult(
                                is_valid=False,
                                level=ValidationLevel.ERROR,
                                message=f"Method '{method_name}' raises NotImplementedError",
                                details="Method must be implemented with actual sizing logic",
                                suggestions=[
                                    f"Replace 'raise NotImplementedError' with actual implementation",
                                    "Implement position sizing calculations based on portfolio_info and signal"
                                ]
                            )
                    elif isinstance(stmt.exc, ast.Name) and stmt.exc.id in ['NotImplementedError', 'NotImplemented']:
                        return ValidationResult(
                            is_valid=False,
                            level=ValidationLevel.ERROR,
                            message=f"Method '{method_name}' raises NotImplementedError",
                            details="Method must be implemented with actual sizing logic",
                            suggestions=[
                                f"Replace 'raise NotImplementedError' with actual implementation",
                                "Implement position sizing calculations based on portfolio_info and signal"
                            ]
                        )
            
            # 对于cal方法，检查是否有仓位计算逻辑
            if method_name == 'cal':
                has_quantity_modification = False
                has_portfolio_usage = False
                
                # 检查是否有实际的仓位计算逻辑
                for node in ast.walk(tree):
                    if isinstance(node, ast.Attribute):
                        if isinstance(node.value, ast.Name) and node.value.id == 'signal' and node.attr == 'quantity':
                            has_quantity_modification = True
                        elif isinstance(node.value, ast.Name) and node.value.id == 'portfolio_info':
                            has_portfolio_usage = True
                
                # 检查是否只是简单返回signal
                if len(method_body) == 1 and isinstance(method_body[0], ast.Return):
                    return ValidationResult(
                        is_valid=False,
                        level=ValidationLevel.WARNING,
                        message=f"Method '{method_name}' appears to be a stub",
                        details="cal method should calculate and modify signal quantity",
                        suggestions=[
                            "Add position sizing logic to calculate appropriate quantity",
                            "Consider portfolio cash, risk limits, and signal strength",
                            "Modify signal.quantity before returning"
                        ]
                    )
                
                # 检查是否修改了signal.quantity
                if not has_quantity_modification:
                    return ValidationResult(
                        is_valid=False,
                        level=ValidationLevel.WARNING,
                        message=f"Method '{method_name}' may not modify signal quantity",
                        details="Sizer should calculate and set appropriate position size",
                        suggestions=[
                            "Modify signal.quantity based on sizing calculations",
                            "Calculate quantity based on cash, price, and risk limits",
                            "Return the modified signal object"
                        ]
                    )
                
                # 检查是否使用了portfolio_info
                if not has_portfolio_usage:
                    return ValidationResult(
                        is_valid=False,
                        level=ValidationLevel.WARNING,
                        message=f"Method '{method_name}' doesn't use portfolio_info",
                        details="Position sizing should consider portfolio state",
                        suggestions=[
                            "Use portfolio_info to access cash, positions, worth, etc.",
                            "Calculate position size based on available cash",
                            "Consider risk management in position sizing"
                        ]
                    )
            
            return ValidationResult(
                is_valid=True,
                level=ValidationLevel.INFO,
                message=f"Method '{method_name}' implementation validation passed",
                details=f"Method appears to be properly implemented"
            )
            
        except Exception as e:
            return ValidationResult(
                is_valid=True,
                level=ValidationLevel.WARNING,
                message=f"Could not validate method implementation for '{method_name}'",
                details=f"Analysis error: {str(e)}",
                suggestions=["Manual review of method implementation recommended"]
            )