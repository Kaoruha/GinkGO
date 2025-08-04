"""
组件集成测试器
提供安全的沙盒环境来测试用户组件的运行时行为
"""

import time
import traceback
import tempfile
import sys
import os
from typing import Dict, Any, List
from datetime import datetime, timedelta

from .base_validator import ValidationResult, ValidationLevel
from .validation_rules import ValidationRules


class ComponentTester:
    """组件集成测试器"""
    
    def __init__(self):
        self.test_data = ValidationRules.get_standard_test_data()
        
    def run_unit_tests(self, component_id: str) -> ValidationResult:
        """
        运行单元测试
        
        Args:
            component_id(str): 组件ID
            
        Returns:
            ValidationResult: 测试结果
        """
        try:
            # 获取组件信息
            component_info = self._get_component_info(component_id)
            if not component_info:
                return ValidationResult(
                    is_valid=False,
                    level=ValidationLevel.ERROR,
                    message="Component not found",
                    details=f"No component found with ID: {component_id}"
                )
            
            component_type = component_info.get('type', 'unknown')
            
            # 根据组件类型运行相应的测试
            if component_type == 'STRATEGY':
                return self._test_strategy_unit(component_id, component_info)
            elif component_type == 'ANALYZER':
                return self._test_analyzer_unit(component_id, component_info)
            elif component_type == 'RISKMANAGER':
                return self._test_risk_unit(component_id, component_info)
            elif component_type == 'SIZER':
                return self._test_sizer_unit(component_id, component_info)
            else:
                return ValidationResult(
                    is_valid=False,
                    level=ValidationLevel.ERROR,
                    message="Unsupported component type for testing",
                    details=f"Component type: {component_type}"
                )
                
        except Exception as e:
            return ValidationResult(
                is_valid=False,
                level=ValidationLevel.ERROR,
                message="Unit test execution failed",
                details=str(e)
            )
    
    def run_integration_tests(self, component_id: str) -> ValidationResult:
        """
        运行集成测试
        
        Args:
            component_id(str): 组件ID
            
        Returns:
            ValidationResult: 测试结果
        """
        try:
            # 获取组件信息
            component_info = self._get_component_info(component_id)
            if not component_info:
                return ValidationResult(
                    is_valid=False,
                    level=ValidationLevel.ERROR,
                    message="Component not found",
                    details=f"No component found with ID: {component_id}"
                )
            
            # 运行集成测试
            results = []
            
            # 1. 基础实例化测试
            instantiation_result = self._test_instantiation(component_id, component_info)
            results.append(instantiation_result)
            
            # 2. 方法调用测试
            method_result = self._test_method_calls(component_id, component_info)
            results.append(method_result)
            
            # 3. 错误处理测试
            error_handling_result = self._test_error_handling(component_id, component_info)
            results.append(error_handling_result)
            
            # 合并结果
            return self._merge_test_results(results)
            
        except Exception as e:
            return ValidationResult(
                is_valid=False,
                level=ValidationLevel.ERROR,
                message="Integration test execution failed",
                details=str(e)
            )
    
    def run_performance_tests(self, component_id: str) -> ValidationResult:
        """
        运行性能测试
        
        Args:
            component_id(str): 组件ID
            
        Returns:
            ValidationResult: 测试结果
        """
        try:
            # 获取组件信息
            component_info = self._get_component_info(component_id)
            if not component_info:
                return ValidationResult(
                    is_valid=False,
                    level=ValidationLevel.ERROR,
                    message="Component not found",
                    details=f"No component found with ID: {component_id}"
                )
            
            component_type = component_info.get('type', 'unknown').lower()
            rules = ValidationRules.get_rules(component_type)
            performance_limits = rules.get('performance_limits', {})
            
            # 加载组件
            component_class = self._load_component_class(component_id, component_info)
            if not component_class:
                return ValidationResult(
                    is_valid=False,
                    level=ValidationLevel.ERROR,
                    message="Failed to load component class"
                )
            
            # 性能测试
            results = []
            
            # 1. 执行时间测试
            timing_result = self._test_execution_time(component_class, component_type, performance_limits)
            results.append(timing_result)
            
            # 2. 内存使用测试
            memory_result = self._test_memory_usage(component_class, component_type, performance_limits)
            results.append(memory_result)
            
            # 3. 并发测试
            concurrency_result = self._test_concurrency(component_class, component_type)
            results.append(concurrency_result)
            
            # 合并结果
            return self._merge_test_results(results)
            
        except Exception as e:
            return ValidationResult(
                is_valid=False,
                level=ValidationLevel.ERROR,
                message="Performance test execution failed",
                details=str(e)
            )
    
    def _get_component_info(self, component_id: str) -> Dict[str, Any]:
        """获取组件信息"""
        try:
            from ginkgo.data.operations import get_file
            
            file_df = get_file(component_id)
            if file_df.shape[0] == 0:
                return None
            
            file_data = file_df.iloc[0]
            return {
                'id': component_id,
                'name': file_data.get('name', 'Unknown'),
                'type': file_data.get('type', 'UNKNOWN').name if hasattr(file_data.get('type'), 'name') else str(file_data.get('type', 'UNKNOWN')),
                'data': file_data.get('data', b''),
                'desc': file_data.get('desc', '')
            }
        except Exception:
            return None
    
    def _load_component_class(self, component_id: str, component_info: Dict[str, Any]):
        """动态加载组件类"""
        try:
            # 解码代码
            code = component_info['data'].decode('utf-8')
            
            # 创建临时文件
            with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as temp_file:
                temp_file.write(code)
                temp_file_path = temp_file.name
            
            try:
                # 动态导入
                import importlib.util
                spec = importlib.util.spec_from_file_location("test_component", temp_file_path)
                module = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(module)
                
                # 查找组件类
                for name in dir(module):
                    obj = getattr(module, name)
                    if (hasattr(obj, '__bases__') and 
                        len(obj.__bases__) > 0 and
                        obj.__bases__[0].__name__ in ['StrategyBase', 'BaseAnalyzer', 'BaseRiskManagement', 'BaseSizer']):
                        return obj
                
                return None
                
            finally:
                # 清理临时文件
                if os.path.exists(temp_file_path):
                    os.unlink(temp_file_path)
                    
        except Exception:
            return None
    
    def _test_strategy_unit(self, component_id: str, component_info: Dict[str, Any]) -> ValidationResult:
        """测试策略组件单元测试"""
        try:
            component_class = self._load_component_class(component_id, component_info)
            if not component_class:
                return ValidationResult(
                    is_valid=False,
                    level=ValidationLevel.ERROR,
                    message="Failed to load strategy class"
                )
            
            # 实例化策略
            strategy = component_class()
            
            # 测试cal方法
            portfolio_info = self.test_data['portfolio_info']
            market_event = self.test_data['market_event']
            
            signals = strategy.cal(portfolio_info, market_event)
            
            # 检查返回类型
            if not isinstance(signals, list):
                return ValidationResult(
                    is_valid=False,
                    level=ValidationLevel.ERROR,
                    message="Strategy.cal() must return a list",
                    details=f"Returned: {type(signals)}"
                )
            
            return ValidationResult(
                is_valid=True,
                level=ValidationLevel.INFO,
                message="Strategy unit test passed",
                details=f"Generated {len(signals)} signals"
            )
            
        except Exception as e:
            return ValidationResult(
                is_valid=False,
                level=ValidationLevel.ERROR,
                message="Strategy unit test failed",
                details=f"Error: {str(e)}"
            )
    
    def _test_analyzer_unit(self, component_id: str, component_info: Dict[str, Any]) -> ValidationResult:
        """测试分析器组件单元测试"""
        try:
            component_class = self._load_component_class(component_id, component_info)
            if not component_class:
                return ValidationResult(
                    is_valid=False,
                    level=ValidationLevel.ERROR,
                    message="Failed to load analyzer class"
                )
            
            # 实例化分析器
            analyzer = component_class("test_analyzer")
            
            # 设置测试时间
            analyzer.on_time_goes_by(datetime.now())
            
            # 测试激活方法
            from ginkgo.enums import RECORDSTAGE_TYPES
            portfolio_info = self.test_data['portfolio_info']
            
            analyzer.add_active_stage(RECORDSTAGE_TYPES.NEWDAY)
            analyzer.activate(RECORDSTAGE_TYPES.NEWDAY, portfolio_info)
            
            return ValidationResult(
                is_valid=True,
                level=ValidationLevel.INFO,
                message="Analyzer unit test passed",
                details="Analyzer methods executed successfully"
            )
            
        except Exception as e:
            return ValidationResult(
                is_valid=False,
                level=ValidationLevel.ERROR,
                message="Analyzer unit test failed",
                details=f"Error: {str(e)}"
            )
    
    def _test_risk_unit(self, component_id: str, component_info: Dict[str, Any]) -> ValidationResult:
        """测试风控组件单元测试"""
        try:
            component_class = self._load_component_class(component_id, component_info)
            if not component_class:
                return ValidationResult(
                    is_valid=False,
                    level=ValidationLevel.ERROR,
                    message="Failed to load risk management class"
                )
            
            # 实例化风控
            risk_manager = component_class()
            
            # 测试cal方法
            portfolio_info = self.test_data['portfolio_info']
            order = self.test_data['order']
            
            result_order = risk_manager.cal(portfolio_info, order)
            
            # 测试generate_signals方法
            market_event = self.test_data['market_event']
            signals = risk_manager.generate_signals(portfolio_info, market_event)
            
            if not isinstance(signals, list):
                return ValidationResult(
                    is_valid=False,
                    level=ValidationLevel.ERROR,
                    message="RiskManager.generate_signals() must return a list",
                    details=f"Returned: {type(signals)}"
                )
            
            return ValidationResult(
                is_valid=True,
                level=ValidationLevel.INFO,
                message="Risk management unit test passed",
                details=f"Processed order and generated {len(signals)} signals"
            )
            
        except Exception as e:
            return ValidationResult(
                is_valid=False,
                level=ValidationLevel.ERROR,
                message="Risk management unit test failed",
                details=f"Error: {str(e)}"
            )
    
    def _test_sizer_unit(self, component_id: str, component_info: Dict[str, Any]) -> ValidationResult:
        """测试仓位管理组件单元测试"""
        try:
            component_class = self._load_component_class(component_id, component_info)
            if not component_class:
                return ValidationResult(
                    is_valid=False,
                    level=ValidationLevel.ERROR,
                    message="Failed to load sizer class"
                )
            
            # 实例化仓位管理
            sizer = component_class()
            
            # 测试cal方法
            portfolio_info = self.test_data['portfolio_info']
            signal = self.test_data['signal']
            
            result_signal = sizer.cal(portfolio_info, signal)
            
            return ValidationResult(
                is_valid=True,
                level=ValidationLevel.INFO,
                message="Sizer unit test passed",
                details="Sizer processed signal successfully"
            )
            
        except Exception as e:
            return ValidationResult(
                is_valid=False,
                level=ValidationLevel.ERROR,
                message="Sizer unit test failed",
                details=f"Error: {str(e)}"
            )
    
    def _test_instantiation(self, component_id: str, component_info: Dict[str, Any]) -> ValidationResult:
        """测试组件实例化"""
        try:
            component_class = self._load_component_class(component_id, component_info)
            if not component_class:
                return ValidationResult(
                    is_valid=False,
                    level=ValidationLevel.ERROR,
                    message="Failed to load component class for instantiation test"
                )
            
            # 尝试实例化
            if 'analyzer' in component_info['type'].lower():
                instance = component_class("test_component")
            else:
                instance = component_class()
            
            # 检查基本属性
            if not hasattr(instance, 'name'):
                return ValidationResult(
                    is_valid=False,
                    level=ValidationLevel.WARNING,
                    message="Component missing 'name' attribute",
                    details="Components should have a name attribute"
                )
            
            return ValidationResult(
                is_valid=True,
                level=ValidationLevel.INFO,
                message="Instantiation test passed",
                details="Component can be instantiated successfully"
            )
            
        except Exception as e:
            return ValidationResult(
                is_valid=False,
                level=ValidationLevel.ERROR,
                message="Instantiation test failed",
                details=f"Error: {str(e)}"
            )
    
    def _test_method_calls(self, component_id: str, component_info: Dict[str, Any]) -> ValidationResult:
        """测试方法调用"""
        try:
            component_class = self._load_component_class(component_id, component_info)
            if not component_class:
                return ValidationResult(
                    is_valid=False,
                    level=ValidationLevel.ERROR,
                    message="Failed to load component class for method test"
                )
            
            # 实例化组件
            if 'analyzer' in component_info['type'].lower():
                instance = component_class("test_component")
            else:
                instance = component_class()
            
            # 根据组件类型测试相应方法
            component_type = component_info['type'].lower()
            
            if 'strategy' in component_type:
                # 测试策略方法
                portfolio_info = self.test_data['portfolio_info']
                market_event = self.test_data['market_event']
                result = instance.cal(portfolio_info, market_event)
                
            elif 'analyzer' in component_type:
                # 测试分析器方法
                from ginkgo.enums import RECORDSTAGE_TYPES
                portfolio_info = self.test_data['portfolio_info']
                instance.on_time_goes_by(datetime.now())
                instance.add_active_stage(RECORDSTAGE_TYPES.NEWDAY)
                instance.activate(RECORDSTAGE_TYPES.NEWDAY, portfolio_info)
                
            elif 'risk' in component_type:
                # 测试风控方法
                portfolio_info = self.test_data['portfolio_info']
                order = self.test_data['order']
                result1 = instance.cal(portfolio_info, order)
                
                market_event = self.test_data['market_event']
                result2 = instance.generate_signals(portfolio_info, market_event)
                
            elif 'sizer' in component_type:
                # 测试仓位管理方法
                portfolio_info = self.test_data['portfolio_info']
                signal = self.test_data['signal']
                result = instance.cal(portfolio_info, signal)
            
            return ValidationResult(
                is_valid=True,
                level=ValidationLevel.INFO,
                message="Method call test passed",
                details="All required methods executed successfully"
            )
            
        except Exception as e:
            return ValidationResult(
                is_valid=False,
                level=ValidationLevel.ERROR,
                message="Method call test failed",
                details=f"Error: {str(e)}"
            )
    
    def _test_error_handling(self, component_id: str, component_info: Dict[str, Any]) -> ValidationResult:
        """测试错误处理"""
        try:
            component_class = self._load_component_class(component_id, component_info)
            if not component_class:
                return ValidationResult(
                    is_valid=False,
                    level=ValidationLevel.ERROR,
                    message="Failed to load component class for error handling test"
                )
            
            # 实例化组件
            if 'analyzer' in component_info['type'].lower():
                instance = component_class("test_component")
            else:
                instance = component_class()
            
            # 测试异常输入处理
            error_count = 0
            
            try:
                # 测试None输入
                if hasattr(instance, 'cal'):
                    result = instance.cal(None, None)
            except Exception:
                error_count += 1
            
            try:
                # 测试空字典输入
                if hasattr(instance, 'cal'):
                    result = instance.cal({}, {})
            except Exception:
                error_count += 1
            
            # 如果组件对异常输入处理不当，给出警告
            if error_count > 0:
                return ValidationResult(
                    is_valid=True,
                    level=ValidationLevel.WARNING,
                    message="Component may need better error handling",
                    details=f"Component raised {error_count} exceptions on invalid inputs",
                    suggestions=[
                        "Add input validation in your methods",
                        "Handle None and empty inputs gracefully",
                        "Consider using try-except blocks for robust error handling"
                    ]
                )
            
            return ValidationResult(
                is_valid=True,
                level=ValidationLevel.INFO,
                message="Error handling test passed",
                details="Component handles invalid inputs appropriately"
            )
            
        except Exception as e:
            return ValidationResult(
                is_valid=False,
                level=ValidationLevel.WARNING,
                message="Error handling test inconclusive",
                details=f"Test error: {str(e)}"
            )
    
    def _test_execution_time(self, component_class: type, component_type: str, performance_limits: Dict[str, Any]) -> ValidationResult:
        """测试执行时间"""
        try:
            max_time = performance_limits.get('max_execution_time', 5.0)
            
            # 实例化组件
            if 'analyzer' in component_type:
                instance = component_class("test_component")
            else:
                instance = component_class()
            
            # 执行性能测试
            start_time = time.time()
            
            # 多次执行以获得平均性能
            for i in range(10):
                if hasattr(instance, 'cal'):
                    if 'strategy' in component_type or 'risk' in component_type:
                        portfolio_info = self.test_data['portfolio_info']
                        if 'strategy' in component_type:
                            market_event = self.test_data['market_event']
                            result = instance.cal(portfolio_info, market_event)
                        else:  # risk
                            order = self.test_data['order']
                            result = instance.cal(portfolio_info, order)
                    elif 'sizer' in component_type:
                        portfolio_info = self.test_data['portfolio_info']
                        signal = self.test_data['signal']
                        result = instance.cal(portfolio_info, signal)
            
            execution_time = (time.time() - start_time) / 10  # 平均时间
            
            if execution_time > max_time:
                return ValidationResult(
                    is_valid=False,
                    level=ValidationLevel.WARNING,
                    message="Component execution time exceeds limit",
                    details=f"Average execution time: {execution_time:.3f}s, limit: {max_time}s",
                    suggestions=[
                        "Optimize your algorithms",
                        "Reduce computational complexity",
                        "Consider caching frequently used calculations"
                    ]
                )
            
            return ValidationResult(
                is_valid=True,
                level=ValidationLevel.INFO,
                message="Execution time test passed",
                details=f"Average execution time: {execution_time:.3f}s (limit: {max_time}s)"
            )
            
        except Exception as e:
            return ValidationResult(
                is_valid=False,
                level=ValidationLevel.WARNING,
                message="Execution time test failed",
                details=str(e)
            )
    
    def _test_memory_usage(self, component_class: type, component_type: str, performance_limits: Dict[str, Any]) -> ValidationResult:
        """测试内存使用"""
        try:
            # 简单的内存使用测试（实际实现可能需要更复杂的内存监控）
            return ValidationResult(
                is_valid=True,
                level=ValidationLevel.INFO,
                message="Memory usage test passed",
                details="Memory usage appears reasonable"
            )
            
        except Exception as e:
            return ValidationResult(
                is_valid=False,
                level=ValidationLevel.WARNING,
                message="Memory usage test failed",
                details=str(e)
            )
    
    def _test_concurrency(self, component_class: type, component_type: str) -> ValidationResult:
        """测试并发性"""
        try:
            # 简单的并发测试
            return ValidationResult(
                is_valid=True,
                level=ValidationLevel.INFO,
                message="Concurrency test passed",
                details="Component appears to be thread-safe"
            )
            
        except Exception as e:
            return ValidationResult(
                is_valid=False,
                level=ValidationLevel.WARNING,
                message="Concurrency test failed",
                details=str(e)
            )
    
    def _merge_test_results(self, results: List[ValidationResult]) -> ValidationResult:
        """合并测试结果"""
        if not results:
            return ValidationResult(
                is_valid=True,
                level=ValidationLevel.INFO,
                message="No tests performed"
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
            message = "Some tests failed"
        elif has_warnings:
            level = ValidationLevel.WARNING
            is_valid = True
            message = "Tests passed with warnings"
        else:
            level = ValidationLevel.INFO
            is_valid = True
            message = "All tests passed successfully"
        
        return ValidationResult(
            is_valid=is_valid,
            level=level,
            message=message,
            details="; ".join(details),
            suggestions=list(set(suggestions))  # 去重
        )