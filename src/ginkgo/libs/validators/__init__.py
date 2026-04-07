# Upstream: libs顶层模块(__init__.py)、CLI/API层 (调用validate_component/test_component)
# Downstream: BaseValidator/ValidationResult/ValidationLevel, StrategyValidator, AnalyzerValidator, RiskValidator, SizerValidator, ComponentTester, ValidationRules
# Role: 组件校验器包入口，导出校验基类和策略/分析器/风控/仓位四类专用校验器，提供validate_component/test_component统一入口






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

def validate_component(component_type: str, code: str = None, file_path: str = None,
                        component_id: str = None, loader=None):
    """
    统一的组件校验入口函数

    Args:
        component_type(str): 组件类型 (strategy, analyzer, risk, sizer)
        code(str): 组件代码字符串
        file_path(str): 组件文件路径
        component_id(str): 已存储的组件ID
        loader(callable): 组件加载函数（使用 component_id 时必传）

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
        if loader is None:
            return ValidationResult(
                is_valid=False,
                level=ValidationLevel.ERROR,
                message="loader is required when validating by component_id",
                details="Pass a callable that accepts component_id and returns component data"
            )
        return validator.validate_component(component_id, loader)
    else:
        return ValidationResult(
            is_valid=False,
            level=ValidationLevel.ERROR,
            message="No source provided for validation",
            details="Must provide either code, file_path, or component_id"
        )

def test_component(component_id: str, test_type: str = "integration", loader=None):
    """
    统一的组件测试入口函数

    Args:
        component_id(str): 组件ID
        test_type(str): 测试类型 (unit, integration, performance)
        loader(callable): 组件加载函数（必传）

    Returns:
        ValidationResult: 测试结果
    """
    if loader is None:
        return ValidationResult(
            is_valid=False,
            level=ValidationLevel.ERROR,
            message="loader is required",
            details="Pass a callable that accepts component_id and returns component data"
        )
    tester = ComponentTester(loader=loader)
    
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
