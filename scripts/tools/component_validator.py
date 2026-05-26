"""
Ginkgo组件验证工具

CLI工具，用于验证用户自定义回测组件是否符合Ginkgo系统要求。
提供详细的合规性报告和修复建议，帮助开发者快速集成自定义组件。
"""

import sys
import argparse
import importlib.util
import inspect
from pathlib import Path
from typing import Dict, List, Any, Type
import json
from datetime import datetime

# 导入测试框架
sys.path.append(str(Path(__file__).parent.parent))
from unit.backtest.test_component_contracts import (
    ComponentDiscovery, 
    ComponentContractValidator,
    MockDataGenerator
)

try:
    from ginkgo.trading.strategies.strategy_base import BaseStrategy
    from ginkgo.trading.analysis.analyzers.base_analyzer import BaseAnalyzer  
    from ginkgo.trading.strategy.risk_managements.base_risk import BaseRiskManagement
    from ginkgo.trading.strategy.sizers.base_sizer import BaseSizer
    from ginkgo.trading.strategy.selectors.base_selector import BaseSelector
    from ginkgo.trading.computation.technical.base_indicator import BaseIndicator
    GINKGO_AVAILABLE = True
except ImportError:
    GINKGO_AVAILABLE = False
    print("Warning: Ginkgo modules not available. Some validations will be skipped.")


class ComponentValidator:
    """组件验证器"""
    
    BASE_CLASSES = {
        'strategy': BaseStrategy,
        'analyzer': BaseAnalyzer,
        'risk': BaseRiskManagement,
        'sizer': BaseSizer,
        'selector': BaseSelector,
        'indicator': BaseIndicator
    } if GINKGO_AVAILABLE else {}
    
    def __init__(self):
        self.validation_results = {}
    
    def load_component_from_file(self, file_path: str, component_type: str) -> List[Type]:
        """从文件加载组件类"""
        try:
            spec = importlib.util.spec_from_file_location("user_component", file_path)
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            
            base_class = self.BASE_CLASSES.get(component_type)
            if not base_class:
                return []
            
            components = []
            for name in dir(module):
                obj = getattr(module, name)
                if (inspect.isclass(obj) and 
                    issubclass(obj, base_class) and 
                    obj != base_class):
                    components.append(obj)
            
            return components
            
        except Exception as e:
            print(f"Error loading component from {file_path}: {e}")
            return []
    
    def validate_component(self, component_class: Type, base_class: Type) -> Dict[str, Any]:
        """验证单个组件"""
        validation_result = {
            'component_name': component_class.__name__,
            'base_class': base_class.__name__,
            'timestamp': datetime.now().isoformat(),
            'overall_status': 'PASS',
            'issues': [],
            'warnings': [],
            'recommendations': []
        }
        
        # 1. 验证抽象方法实现
        method_validation = ComponentContractValidator.validate_abstract_methods(
            component_class, base_class
        )
        if not method_validation['valid']:
            validation_result['overall_status'] = 'FAIL'
            validation_result['issues'].extend([
                f"Missing methods: {method_validation['missing_methods']}",
                f"Signature mismatches: {method_validation['signature_mismatches']}"
            ])
        
        # 2. 验证必需属性
        attr_validation = ComponentContractValidator.validate_required_attributes(
            component_class, base_class
        )
        if not attr_validation['valid']:
            validation_result['overall_status'] = 'FAIL'
            validation_result['issues'].extend([
                f"Missing attributes: {attr_validation['missing_attributes']}"
            ])
        
        # 3. 验证集成兼容性
        integration_validation = ComponentContractValidator.validate_component_integration(
            component_class, base_class
        )
        if not integration_validation['valid']:
            validation_result['warnings'].extend(
                integration_validation['integration_errors']
            )
        
        # 4. 提供修复建议
        validation_result['recommendations'] = self._generate_recommendations(
            component_class, base_class, validation_result['issues']
        )
        
        return validation_result
    
    def _generate_recommendations(self, component_class: Type, base_class: Type, issues: List[str]) -> List[str]:
        """生成修复建议"""
        recommendations = []
        
        for issue in issues:
            if "Missing methods" in issue:
                recommendations.append(
                    "Implement all abstract methods from the base class. "
                    "Check the base class documentation for method signatures and expected behavior."
                )
            
            if "Missing attributes" in issue:
                recommendations.append(
                    "Ensure all required attributes are initialized in __init__. "
                    "Call super().__init__() to properly initialize the base class."
                )
            
            if "Signature mismatches" in issue:
                recommendations.append(
                    "Check method signatures match the base class. "
                    "Use *args, **kwargs if your method needs additional parameters."
                )
        
        if not recommendations:
            recommendations.append(
                "Component appears to be compliant. Test it in a backtest to ensure proper integration."
            )
        
        return recommendations
    
    def validate_file(self, file_path: str, component_type: str) -> Dict[str, Any]:
        """验证文件中的所有组件"""
        components = self.load_component_from_file(file_path, component_type)
        
        if not components:
            return {
                'file_path': file_path,
                'component_type': component_type,
                'status': 'ERROR',
                'message': f'No {component_type} components found in file',
                'components': []
            }
        
        base_class = self.BASE_CLASSES[component_type]
        results = []
        
        for component_class in components:
            result = self.validate_component(component_class, base_class)
            results.append(result)
        
        # 计算整体状态
        overall_status = 'PASS'
        if any(r['overall_status'] == 'FAIL' for r in results):
            overall_status = 'FAIL'
        elif any(r['warnings'] for r in results):
            overall_status = 'WARNING'
        
        return {
            'file_path': file_path,
            'component_type': component_type,
            'status': overall_status,
            'components': results,
            'summary': {
                'total_components': len(results),
                'passed': len([r for r in results if r['overall_status'] == 'PASS']),
                'failed': len([r for r in results if r['overall_status'] == 'FAIL']),
                'warnings': sum(len(r['warnings']) for r in results)
            }
        }
    
    def print_validation_report(self, validation_result: Dict[str, Any]):
        """打印验证报告"""
        print(f"\n{'='*60}")
        print(f"Ginkgo Component Validation Report")
        print(f"{'='*60}")
        print(f"File: {validation_result['file_path']}")
        print(f"Component Type: {validation_result['component_type']}")
        print(f"Overall Status: {validation_result['status']}")
        
        if 'summary' in validation_result:
            summary = validation_result['summary']
            print(f"\nSummary:")
            print(f"  Total Components: {summary['total_components']}")
            print(f"  Passed: {summary['passed']}")
            print(f"  Failed: {summary['failed']}")
            print(f"  Warnings: {summary['warnings']}")
        
        print(f"\nDetailed Results:")
        print(f"{'-'*60}")
        
        for component_result in validation_result.get('components', []):
            print(f"\nComponent: {component_result['component_name']}")
            print(f"Status: {component_result['overall_status']}")
            
            if component_result['issues']:
                print(f"Issues:")
                for issue in component_result['issues']:
                    print(f"  ❌ {issue}")
            
            if component_result['warnings']:
                print(f"Warnings:")
                for warning in component_result['warnings']:
                    print(f"  ⚠️  {warning}")
            
            if component_result['recommendations']:
                print(f"Recommendations:")
                for rec in component_result['recommendations']:
                    print(f"  💡 {rec}")
        
        print(f"\n{'='*60}")
    
    def save_report(self, validation_result: Dict[str, Any], output_file: str):
        """保存验证报告到文件"""
        with open(output_file, 'w') as f:
            json.dump(validation_result, f, indent=2, default=str)
        print(f"Validation report saved to: {output_file}")


def main():
    """主函数"""
    if not GINKGO_AVAILABLE:
        print("Error: Ginkgo modules not available. Please install Ginkgo first.")
        sys.exit(1)
    
    parser = argparse.ArgumentParser(
        description='Validate Ginkgo component compliance',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog='''
Examples:
  python component_validator.py my_strategy.py strategy
  python component_validator.py custom_analyzer.py analyzer --output report.json
  python component_validator.py risk_manager.py risk --verbose
        '''
    )
    
    parser.add_argument('file', help='Path to Python file containing component')
    parser.add_argument('type', choices=['strategy', 'analyzer', 'risk', 'sizer', 'selector', 'indicator'],
                       help='Type of component to validate')
    parser.add_argument('--output', '-o', help='Output file for JSON report')
    parser.add_argument('--verbose', '-v', action='store_true', help='Verbose output')
    
    args = parser.parse_args()
    
    # 验证文件存在
    if not Path(args.file).exists():
        print(f"Error: File {args.file} not found")
        sys.exit(1)
    
    # 创建验证器并执行验证
    validator = ComponentValidator()
    result = validator.validate_file(args.file, args.type)
    
    # 打印报告
    validator.print_validation_report(result)
    
    # 保存报告（如果指定）
    if args.output:
        validator.save_report(result, args.output)
    
    # 根据验证结果设置退出码
    if result['status'] == 'FAIL':
        sys.exit(1)
    elif result['status'] == 'WARNING':
        sys.exit(2)
    else:
        sys.exit(0)

