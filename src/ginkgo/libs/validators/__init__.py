# Upstream: All Modules
# Downstream: Standard Library
# Role: 组件验证器模块导出基类/策略验证/风控验证/组件测试等验证工具支持交易系统功能和组件集成提供完整业务支持






"""
Ginkgo 组件校验器模块
提供用户自定义组件的校验和测试功能，确保组件能够顺利接入框架
"""

from ginkgo.libs.validators.base_validator import BaseValidator, ValidationResult, ValidationLevel
from ginkgo.libs.validators.strategy_validator import StrategyValidator
from ginkgo.libs.validators.analyzer_validator import AnalyzerValidator
from ginkgo.libs.validators.risk_validator import RiskValidator
from ginkgo.libs.validators.sizer_validator import SizerValidator
from ginkgo.libs.validators.component_tester import ComponentTester
from ginkgo.libs.validators.validation_rules import ValidationRules

# 导出所有校验器类
__all__ = [
    "BaseValidator",
    "ValidationResult", 
    "ValidationLevel",
    "StrategyValidator",
    "AnalyzerValidator", 
    "RiskValidator",
    "SizerValidator",
    "ComponentTester",
    "ValidationRules",
]

def validate_component(component_type: str, code: str = None, file_path: str = None, component_id: str = None):
    """
    统一的组件校验入口函数
    
    Args:
        component_type(str): 组件类型 (strategy, analyzer, risk, sizer)
        code(str): 组件代码字符串
        file_path(str): 组件文件路径
        component_id(str): 已存储的组件ID
        
    Returns:
        ValidationResult: 校验结果
    """
    validators = {
        'strategy': StrategyValidator,
        'analyzer': AnalyzerValidator,
        'risk': RiskValidator,
        'sizer': SizerValidator
    }
    
    if component_type not in validators:
        return ValidationResult(
            is_valid=False,
            level=ValidationLevel.ERROR,
            message=f"Unsupported component type: {component_type}",
            details=f"Supported types: {', '.join(validators.keys())}"
        )
    
    validator_class = validators[component_type]
    validator = validator_class()
    
    if code:
        return validator.validate_code(code)
    elif file_path:
        return validator.validate_file(file_path)
    elif component_id:
        return validator.validate_component(component_id)
    else:
        return ValidationResult(
            is_valid=False,
            level=ValidationLevel.ERROR,
            message="No source provided for validation",
            details="Must provide either code, file_path, or component_id"
        )

def test_component(component_id: str, test_type: str = "integration"):
    """
    统一的组件测试入口函数
    
    Args:
        component_id(str): 组件ID
        test_type(str): 测试类型 (unit, integration, performance)
        
    Returns:
        ValidationResult: 测试结果
    """
    tester = ComponentTester()
    
    if test_type == "unit":
        return tester.run_unit_tests(component_id)
    elif test_type == "integration":
        return tester.run_integration_tests(component_id)
    elif test_type == "performance":
        return tester.run_performance_tests(component_id)
    else:
        return ValidationResult(
            is_valid=False,
            level=ValidationLevel.ERROR,
            message=f"Unsupported test type: {test_type}",
            details="Supported types: unit, integration, performance"
        )