"""
测试基础配置和装饰器 - Trading Framework Enhancement

为Protocol接口和Mixin功能提供专门的测试支持：
1. Protocol接口兼容性测试装饰器
2. Mixin功能验证装饰器
3. 增强的TDD度量工具
4. 类型安全验证工具
5. 量化交易专用测试工具
"""

import pytest
from typing import Any, Dict, List, Type, Callable, Optional
from dataclasses import dataclass
from datetime import datetime
import warnings
import time
import functools
from decimal import Decimal

# Protocol接口导入
from ginkgo.trading.interfaces.protocols.strategy import IStrategy
from ginkgo.trading.interfaces.protocols.risk_management import IRiskManagement
from ginkgo.trading.interfaces.protocols.portfolio import IPortfolio
from ginkgo.trading.interfaces.protocols.engine import IEngine


@dataclass
class TestMetrics:
    """测试度量数据"""
    start_time: float
    end_time: float
    memory_usage: float
    success: bool
    error_message: Optional[str] = None
    protocol_compliance: bool = True
    mixin_functionality: bool = True


class TestMetricsCollector:
    """测试度量收集器"""

    def __init__(self):
        self.metrics: List[TestMetrics] = []
        self.current_test: Optional[TestMetrics] = None

    def start_test(self) -> None:
        """开始测试计时"""
        self.current_test = TestMetrics(
            start_time=time.time(),
            end_time=0.0,
            memory_usage=0.0,
            success=True
        )

    def end_test(self, success: bool = True, error_message: str = None) -> TestMetrics:
        """结束测试计时"""
        if self.current_test:
            self.current_test.end_time = time.time()
            self.current_test.success = success
            self.current_test.error_message = error_message
            self.metrics.append(self.current_test)
            result = self.current_test
            self.current_test = None
            return result
        return None

    def get_summary(self) -> Dict[str, Any]:
        """获取测试摘要"""
        if not self.metrics:
            return {}

        total_tests = len(self.metrics)
        successful_tests = sum(1 for m in self.metrics if m.success)
        total_time = sum(m.end_time - m.start_time for m in self.metrics)

        return {
            "total_tests": total_tests,
            "successful_tests": successful_tests,
            "failed_tests": total_tests - successful_tests,
            "success_rate": successful_tests / total_tests if total_tests > 0 else 0,
            "total_time": total_time,
            "average_time": total_time / total_tests if total_tests > 0 else 0,
            "protocol_compliance_rate": sum(1 for m in self.metrics if m.protocol_compliance) / total_tests if total_tests > 0 else 0,
            "mixin_functionality_rate": sum(1 for m in self.metrics if m.mixin_functionality) / total_tests if total_tests > 0 else 0
        }


# 全局测试度量收集器
metrics_collector = TestMetricsCollector()


def protocol_compliance_test(protocol_class: Type, strict_mode: bool = True):
    """
    Protocol接口兼容性测试装饰器

    自动验证测试对象是否符合指定Protocol接口的所有要求，包括方法签名、
    返回类型注解和文档字符串完整性。

    Args:
        protocol_class: Protocol接口类 (IStrategy, IRiskManagement, IPortfolio, IEngine)
        strict_mode: 严格模式，启用更详细的验证

    Example:
        @protocol_compliance_test(IStrategy, strict_mode=True)
        def test_my_strategy():
            strategy = MyStrategy()
            return strategy
    """
    def decorator(test_func: Callable) -> Callable:
        @functools.wraps(test_func)
        def wrapper(*args, **kwargs):
            metrics_collector.start_test()
            try:
                # 执行原始测试函数
                result = test_func(*args, **kwargs)

                # Protocol接口验证
                compliance_result = _validate_protocol_compliance(result, protocol_class, strict_mode)

                if not compliance_result.compliant:
                    metrics_collector.end_test(False, compliance_result.error_message)
                    raise AssertionError(f"Protocol兼容性测试失败: {compliance_result.error_message}")

                metrics_collector.end_test(True)
                return result

            except Exception as e:
                metrics_collector.end_test(False, str(e))
                raise

        # 添加测试标记
        wrapper.protocol_test = True
        wrapper.protocol_class = protocol_class
        wrapper.strict_mode = strict_mode

        return wrapper
    return decorator


@dataclass
class ProtocolComplianceResult:
    """Protocol兼容性验证结果"""
    compliant: bool
    error_message: Optional[str] = None
    missing_methods: List[str] = None
    invalid_signatures: List[str] = None
    missing_annotations: List[str] = None
    missing_docs: List[str] = None

    def __post_init__(self):
        if self.missing_methods is None:
            self.missing_methods = []
        if self.invalid_signatures is None:
            self.invalid_signatures = []
        if self.missing_annotations is None:
            self.missing_annotations = []
        if self.missing_docs is None:
            self.missing_docs = []


def _validate_protocol_compliance(obj: Any, protocol_class: Type, strict_mode: bool) -> ProtocolComplianceResult:
    """验证对象是否符合Protocol接口要求"""
    import inspect

    result = ProtocolComplianceResult(compliant=True)

    # 检查是否支持runtime_checkable
    if hasattr(protocol_class, '__instancecheck__'):
        if not isinstance(obj, protocol_class):
            result.compliant = False
            result.error_message = f"对象不符合 {protocol_class.__name__} 接口要求"
            return result

    # 手动验证方法
    protocol_methods = {}
    for name, method in inspect.getmembers(protocol_class, predicate=inspect.isfunction):
        if not name.startswith('_'):
            sig = inspect.signature(method)
            protocol_methods[name] = sig

    # 检查必需方法是否存在
    for method_name, expected_sig in protocol_methods.items():
        if not hasattr(obj, method_name):
            result.missing_methods.append(method_name)
            continue

        # 获取对象方法
        obj_method = getattr(obj, method_name)
        if not callable(obj_method):
            result.missing_methods.append(f"{method_name} (不可调用)")
            continue

        if strict_mode:
            # 验证方法签名
            try:
                obj_sig = inspect.signature(obj_method)
                if not _signatures_compatible(obj_sig, expected_sig):
                    result.invalid_signatures.append(method_name)
            except (ValueError, TypeError):
                result.invalid_signatures.append(f"{method_name} (签名无法解析)")

            # 验证类型注解
            if not _has_type_annotations(obj_method):
                result.missing_annotations.append(method_name)

            # 验证文档字符串
            if not obj_method.__doc__ or len(obj_method.__doc__.strip()) < 10:
                result.missing_docs.append(method_name)

    # 设置最终结果
    if any([result.missing_methods, result.invalid_signatures,
            result.missing_annotations, result.missing_docs]):
        result.compliant = False
        error_parts = []
        if result.missing_methods:
            error_parts.append(f"缺少方法: {', '.join(result.missing_methods)}")
        if result.invalid_signatures:
            error_parts.append(f"签名不匹配: {', '.join(result.invalid_signatures)}")
        if result.missing_annotations:
            error_parts.append(f"缺少类型注解: {', '.join(result.missing_annotations)}")
        if result.missing_docs:
            error_parts.append(f"缺少文档: {', '.join(result.missing_docs)}")
        result.error_message = "; ".join(error_parts)

    return result


def _signatures_compatible(actual_sig, expected_sig) -> bool:
    """检查方法签名是否兼容"""
    # 简化的签名兼容性检查
    actual_params = list(actual_sig.parameters.values())
    expected_params = list(expected_sig.parameters.values())

    if len(actual_params) != len(expected_params):
        return False

    for actual, expected in zip(actual_params, expected_params):
        if actual.kind != expected.kind:
            return False

    return True


def _has_type_annotations(method: Callable) -> bool:
    """检查方法是否有类型注解"""
    import inspect
    sig = inspect.signature(method)

    # 检查参数注解
    for param in sig.parameters.values():
        if param.annotation == inspect.Parameter.empty:
            return False

    # 检查返回值注解
    if sig.return_annotation == inspect.Signature.empty:
        return False

    return True


def mixin_functionality_test(mixin_class: Type, base_class: Type = None, required_methods: List[str] = None):
    """
    Mixin功能验证装饰器

    验证Mixin类是否正确增强了基础类功能，包括方法继承、
    功能正确性和与基础类的兼容性。

    Args:
        mixin_class: Mixin类
        base_class: 期望的基础类
        required_methods: Mixin必须提供的方法列表

    Example:
        @mixin_functionality_test(StrategyMixin, BaseStrategy, ['enhanced_cal', 'validate_signal'])
        def test_strategy_mixin():
            class TestStrategy(BaseStrategy, StrategyMixin):
                pass
            return TestStrategy()
    """
    def decorator(test_func: Callable) -> Callable:
        @functools.wraps(test_func)
        def wrapper(*args, **kwargs):
            metrics_collector.start_test()
            try:
                result = test_func(*args, **kwargs)

                # Mixin功能验证
                functionality_result = _validate_mixin_functionality(
                    result, mixin_class, base_class, required_methods
                )

                if not functionality_result.functional:
                    metrics_collector.end_test(False, functionality_result.error_message)
                    raise AssertionError(f"Mixin功能测试失败: {functionality_result.error_message}")

                metrics_collector.end_test(True)
                return result

            except Exception as e:
                metrics_collector.end_test(False, str(e))
                raise

        # 添加测试标记
        wrapper.mixin_test = True
        wrapper.mixin_class = mixin_class
        wrapper.base_class = base_class

        return wrapper
    return decorator


@dataclass
class MixinFunctionalityResult:
    """Mixin功能验证结果"""
    functional: bool
    error_message: Optional[str] = None
    inheritance_issues: List[str] = None
    missing_methods: List[str] = None
    method_call_failures: List[str] = None

    def __post_init__(self):
        if self.inheritance_issues is None:
            self.inheritance_issues = []
        if self.missing_methods is None:
            self.missing_methods = []
        if self.method_call_failures is None:
            self.method_call_failures = []


def _validate_mixin_functionality(obj: Any, mixin_class: Type, base_class: Type = None, required_methods: List[str] = None) -> MixinFunctionalityResult:
    """验证Mixin功能"""
    import inspect

    result = MixinFunctionalityResult(functional=True)

    # 检查继承关系
    if base_class and not isinstance(obj, base_class):
        result.inheritance_issues.append(f"未正确继承基类: {base_class.__name__}")

    if not isinstance(obj, mixin_class):
        result.inheritance_issues.append(f"未正确继承Mixin: {mixin_class.__name__}")

    # 获取Mixin的公共方法
    mixin_methods = {}
    for name, method in inspect.getmembers(mixin_class, predicate=inspect.isfunction):
        if not name.startswith('_'):
            mixin_methods[name] = method

    # 检查必需方法
    if required_methods:
        for method_name in required_methods:
            if method_name not in mixin_methods:
                result.missing_methods.append(f"指定的必需方法不存在: {method_name}")

    # 检查对象是否具有Mixin方法
    for method_name in mixin_methods:
        if not hasattr(obj, method_name):
            result.missing_methods.append(f"Mixin方法未正确添加: {method_name}")
            continue

        # 尝试调用方法（仅检查可调用性，不实际执行）
        try:
            obj_method = getattr(obj, method_name)
            if not callable(obj_method):
                result.method_call_failures.append(f"{method_name} (不可调用)")
        except Exception:
            result.method_call_failures.append(f"{method_name} (访问失败)")

    # 设置最终结果
    if any([result.inheritance_issues, result.missing_methods, result.method_call_failures]):
        result.functional = False
        error_parts = []
        if result.inheritance_issues:
            error_parts.append(f"继承问题: {', '.join(result.inheritance_issues)}")
        if result.missing_methods:
            error_parts.append(f"缺少方法: {', '.join(result.missing_methods)}")
        if result.method_call_failures:
            error_parts.append(f"方法调用失败: {', '.join(result.method_call_failures)}")
        result.error_message = "; ".join(error_parts)

    return result


def enhanced_financial_precision_test(decimal_places: int = 4, check_zero_division: bool = True):
    """
    增强的金融精度测试装饰器

    自动为测试函数添加金融数据精度验证，包括零除法检查、
    数值范围验证和精度一致性检查。

    Args:
        decimal_places: 小数位数精度
        check_zero_division: 是否检查零除法

    Example:
        @enhanced_financial_precision_test(decimal_places=4, check_zero_division=True)
        def test_portfolio_calculation():
            # 金融计算逻辑
            return portfolio_value
    """
    def decorator(test_func: Callable) -> Callable:
        @functools.wraps(test_func)
        def wrapper(*args, **kwargs):
            try:
                result = test_func(*args, **kwargs)

                # 执行增强的金融精度验证
                _validate_enhanced_financial_precision(result, decimal_places, check_zero_division)

                return result
            except Exception as e:
                raise AssertionError(f"金融精度测试失败: {e}")

        wrapper.financial_test = True
        wrapper.decimal_places = decimal_places
        wrapper.check_zero_division = check_zero_division

        return wrapper
    return decorator


def _validate_enhanced_financial_precision(data: Any, decimal_places: int, check_zero_division: bool) -> None:
    """增强的金融精度验证"""
    from decimal import Decimal, InvalidOperation, DivisionByZero

    def check_value(value, path="root"):
        if isinstance(value, Decimal):
            # 检查精度
            tuple_parts = value.as_tuple()
            if tuple_parts.exponent < -decimal_places:
                raise ValueError(f"数值精度超出限制: {value} (路径: {path}, 小数位数: {-tuple_parts.exponent})")

            # 检查是否为NaN或无穷
            if value.is_nan():
                raise ValueError(f"数值为NaN: {value} (路径: {path})")
            if value.is_infinite():
                raise ValueError(f"数值为无穷: {value} (路径: {path})")

        elif isinstance(value, (int, float)):
            # 检查数值范围
            if abs(value) > 1e18:
                raise ValueError(f"数值超出合理范围: {value} (路径: {path})")

            # 检查是否为特殊浮点值
            if isinstance(value, float):
                if value != value:  # NaN检查
                    raise ValueError(f"浮点数为NaN: {value} (路径: {path})")
                if value in (float('inf'), float('-inf')):
                    raise ValueError(f"浮点数为无穷: {value} (路径: {path})")

        elif isinstance(value, dict):
            for key, val in value.items():
                check_value(val, f"{path}.{key}")

        elif isinstance(value, (list, tuple)):
            for i, val in enumerate(value):
                check_value(val, f"{path}[{i}]")

    check_value(data)


def trading_scenario_test(scenario_type: str, **scenario_params):
    """
    量化交易场景测试装饰器

    为测试函数提供模拟的量化交易场景数据，包括市场数据、
    投资组合状态和风险指标。

    Args:
        scenario_type: 场景类型
            - 'bull_market': 牛市场景
            - 'bear_market': 熊市场景
            - 'volatile_market': 震荡市场场景
            - 'low_liquidity': 低流动性场景
            - 'high_volatility': 高波动率场景
        **scenario_params: 额外的场景参数

    Example:
        @trading_scenario_test('bull_market', volatility=0.02, trend_strength=0.8)
        def test_strategy_in_bull_market(scenario_data):
            # scenario_data包含完整的交易场景
            portfolio_info = scenario_data['portfolio_info']
            market_data = scenario_data['market_data']
            # 测试逻辑...
    """
    def decorator(test_func: Callable) -> Callable:
        @functools.wraps(test_func)
        def wrapper(*args, **kwargs):
            scenario_data = _create_trading_scenario(scenario_type, **scenario_params)
            kwargs['scenario_data'] = scenario_data
            return test_func(*args, **kwargs)

        wrapper.scenario_test = True
        wrapper.scenario_type = scenario_type
        wrapper.scenario_params = scenario_params

        return wrapper
    return decorator


def _create_trading_scenario(scenario_type: str, **params) -> Dict[str, Any]:
    """创建量化交易场景数据"""
    base_timestamp = datetime(2024, 1, 15, 9, 30, 0)

    scenarios = {
        'bull_market': {
            'portfolio_info': {
                'uuid': 'test_portfolio',
                'cash': Decimal('100000.0'),
                'total_value': Decimal('150000.0'),
                'positions': {
                    '000001.SZ': {
                        'code': '000001.SZ',
                        'volume': 1000,
                        'cost': Decimal('10.0'),
                        'current_price': Decimal('12.0'),
                        'market_value': Decimal('12000.0'),
                        'profit_loss': Decimal('2000.0'),
                        'profit_loss_ratio': 0.2
                    }
                },
                'risk_metrics': {
                    'var': Decimal('0.02'),
                    'max_drawdown': Decimal('0.05'),
                    'sharpe_ratio': Decimal('1.5')
                }
            },
            'market_data': {
                'trend': 'up',
                'volatility': params.get('volatility', Decimal('0.015')),
                'momentum': params.get('trend_strength', Decimal('0.7')),
                'liquidity_ratio': Decimal('1.2'),
                'price_changes': [Decimal('0.02'), Decimal('0.015'), Decimal('0.03'), Decimal('0.01'), Decimal('0.025')]
            }
        },
        'bear_market': {
            'portfolio_info': {
                'uuid': 'losing_portfolio',
                'cash': Decimal('100000.0'),
                'total_value': Decimal('85000.0'),
                'positions': {
                    '000001.SZ': {
                        'code': '000001.SZ',
                        'volume': 1000,
                        'cost': Decimal('10.0'),
                        'current_price': Decimal('8.5'),
                        'market_value': Decimal('8500.0'),
                        'profit_loss': Decimal('-1500.0'),
                        'profit_loss_ratio': -0.15
                    }
                },
                'risk_metrics': {
                    'var': Decimal('0.04'),
                    'max_drawdown': Decimal('0.12'),
                    'sharpe_ratio': Decimal('-0.8')
                }
            },
            'market_data': {
                'trend': 'down',
                'volatility': params.get('volatility', Decimal('0.025')),
                'momentum': params.get('trend_strength', Decimal('-0.6')),
                'liquidity_ratio': Decimal('0.8'),
                'price_changes': [Decimal('-0.02'), Decimal('-0.03'), Decimal('-0.015'), Decimal('-0.025'), Decimal('-0.01')]
            }
        },
        'volatile_market': {
            'portfolio_info': {
                'uuid': 'volatile_portfolio',
                'cash': Decimal('100000.0'),
                'total_value': Decimal('105000.0'),
                'positions': {
                    '000001.SZ': {
                        'code': '000001.SZ',
                        'volume': 1000,
                        'cost': Decimal('10.0'),
                        'current_price': Decimal('10.5'),
                        'market_value': Decimal('10500.0'),
                        'profit_loss': Decimal('500.0'),
                        'profit_loss_ratio': 0.05
                    }
                },
                'risk_metrics': {
                    'var': Decimal('0.06'),
                    'max_drawdown': Decimal('0.08'),
                    'sharpe_ratio': Decimal('0.3')
                }
            },
            'market_data': {
                'trend': 'sideways',
                'volatility': params.get('volatility', Decimal('0.04')),
                'momentum': params.get('trend_strength', Decimal('0.1')),
                'liquidity_ratio': Decimal('1.5'),
                'price_changes': [Decimal('0.03'), Decimal('-0.02'), Decimal('0.025'), Decimal('-0.035'), Decimal('0.01')]
            }
        }
    }

    scenario = scenarios.get(scenario_type, scenarios['bull_market'])
    scenario.update(params)
    scenario['timestamp'] = base_timestamp
    scenario['scenario_type'] = scenario_type

    return scenario


# ===== pytest标记 =====

pytest_plugins = []

def pytest_configure(config):
    """添加自定义标记"""
    config.addinivalue_line("markers", "protocol_compliance: Protocol接口兼容性测试")
    config.addinivalue_line("markers", "mixin_functionality: Mixin功能测试")
    config.addinivalue_line("markers", "enhanced_financial: 增强金融精度测试")
    config.addinivalue_line("markers", "trading_scenario: 量化交易场景测试")
    config.addinivalue_line("markers", "framework_enhancement: 框架增强测试")


# ===== 测试报告生成 =====

def generate_test_report() -> Dict[str, Any]:
    """生成测试报告"""
    summary = metrics_collector.get_summary()

    return {
        "test_summary": summary,
        "timestamp": datetime.now().isoformat(),
        "framework": "Ginkgo Trading Framework Enhancement",
        "version": "1.0.0",
        "test_categories": {
            "protocol_compliance": len([m for m in metrics_collector.metrics if hasattr(m, 'protocol_test')]),
            "mixin_functionality": len([m for m in metrics_collector.metrics if hasattr(m, 'mixin_test')]),
            "financial_precision": len([m for m in metrics_collector.metrics if hasattr(m, 'financial_test')]),
            "trading_scenario": len([m for m in metrics_collector.metrics if hasattr(m, 'scenario_test')])
        }
    }


# ===== 测试清理工具 =====

@pytest.fixture(scope="function", autouse=True)
def metrics_collection_cleanup():
    """自动清理测试度量"""
    yield
    # 测试结束后可以执行清理逻辑
    pass


def pytest_sessionfinish(session, exitstatus):
    """测试会话结束时生成报告"""
    report = generate_test_report()
    print("\n" + "="*50)
    print("TRADING FRAMEWORK ENHANCEMENT TEST REPORT")
    print("="*50)
    print(f"Total Tests: {report['test_summary'].get('total_tests', 0)}")
    print(f"Success Rate: {report['test_summary'].get('success_rate', 0):.2%}")
    print(f"Protocol Compliance Rate: {report['test_summary'].get('protocol_compliance_rate', 0):.2%}")
    print(f"Mixin Functionality Rate: {report['test_summary'].get('mixin_functionality_rate', 0):.2%}")
    print("="*50)