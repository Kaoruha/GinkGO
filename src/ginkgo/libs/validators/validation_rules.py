"""
校验规则定义模块
定义各种组件类型的校验规则和标准
"""

from typing import Dict, List, Any
from dataclasses import dataclass


@dataclass
class MethodSignature:
    """方法签名定义"""
    name: str
    required_args: List[str]
    optional_args: List[str] = None
    return_type: str = None
    
    def __post_init__(self):
        if self.optional_args is None:
            self.optional_args = []


class ValidationRules:
    """校验规则集合"""
    
    # 策略组件规则
    STRATEGY_RULES = {
        'required_base_class': 'BaseStrategy',
        'required_methods': [
            MethodSignature(
                name='cal',
                required_args=['self', 'portfolio_info', 'event'],
                optional_args=['*args', '**kwargs'],
                return_type='List[Signal]'
            )
        ],
        'required_imports': [
            'ginkgo.trading.strategy.strategies.base_strategy',
            'ginkgo.trading.signal'
        ],
        'forbidden_operations': [
            # 禁止的危险操作
            'os.system',
            'subprocess.call',
            'eval',
            'exec',
            '__import__'
        ],
        'performance_limits': {
            'max_execution_time': 5.0,  # 秒
            'max_memory_usage': 100,    # MB
        }
    }
    
    # 分析器组件规则
    ANALYZER_RULES = {
        'required_base_class': 'BaseAnalyzer',
        'required_methods': [
            MethodSignature(
                name='_do_activate',
                required_args=['self', 'stage', 'portfolio_info'],
                optional_args=['*args', '**kwargs'],
                return_type='None'
            ),
            MethodSignature(
                name='_do_record',
                required_args=['self', 'stage', 'portfolio_info'],
                optional_args=['*args', '**kwargs'],
                return_type='None'
            )
        ],
        'required_imports': [
            'ginkgo.trading.analysis.analyzers.base_analyzer'
        ],
        'forbidden_operations': [
            'os.system',
            'subprocess.call',
            'eval',
            'exec',
            '__import__'
        ],
        'performance_limits': {
            'max_execution_time': 3.0,
            'max_memory_usage': 50,
        }
    }
    
    # 风控组件规则
    RISK_RULES = {
        'required_base_class': 'BaseRiskManagement',
        'required_methods': [
            MethodSignature(
                name='cal',
                required_args=['self', 'portfolio_info', 'order'],
                optional_args=['*args', '**kwargs'],
                return_type='Order'
            ),
            MethodSignature(
                name='generate_signals',
                required_args=['self', 'portfolio_info', 'event'],
                optional_args=['*args', '**kwargs'],
                return_type='List[Signal]'
            )
        ],
        'required_imports': [
            'ginkgo.trading.strategy.risk_managements.base_risk'
        ],
        'forbidden_operations': [
            'os.system',
            'subprocess.call',
            'eval',
            'exec',
            '__import__'
        ],
        'performance_limits': {
            'max_execution_time': 2.0,
            'max_memory_usage': 30,
        }
    }
    
    # 仓位管理组件规则
    SIZER_RULES = {
        'required_base_class': 'BaseSizer',
        'required_methods': [
            MethodSignature(
                name='cal',
                required_args=['self', 'portfolio_info', 'signal'],
                optional_args=['*args', '**kwargs'],
                return_type='Signal'
            )
        ],
        'required_imports': [
            'ginkgo.trading.strategy.sizers.base_sizer'
        ],
        'forbidden_operations': [
            'os.system',
            'subprocess.call',
            'eval',
            'exec',
            '__import__'
        ],
        'performance_limits': {
            'max_execution_time': 1.0,
            'max_memory_usage': 20,
        }
    }
    
    @classmethod
    def get_rules(cls, component_type: str) -> Dict[str, Any]:
        """
        获取指定组件类型的校验规则
        
        Args:
            component_type(str): 组件类型
            
        Returns:
            Dict[str, Any]: 校验规则字典
        """
        rules_map = {
            'strategy': cls.STRATEGY_RULES,
            'analyzer': cls.ANALYZER_RULES,
            'risk': cls.RISK_RULES,
            'sizer': cls.SIZER_RULES
        }
        
        return rules_map.get(component_type, {})
    
    @classmethod
    def get_standard_test_data(cls) -> Dict[str, Any]:
        """
        获取标准测试数据
        
        Returns:
            Dict[str, Any]: 标准测试数据集
        """
        return {
            'portfolio_info': {
                'uuid': 'test-portfolio-123',
                'name': 'Test Portfolio',
                'cash': 100000.0,
                'worth': 100000.0,
                'positions': {},
                'now': '2024-01-01 09:30:00'
            },
            'market_event': {
                'type': 'PRICEUPDATE',
                'timestamp': '2024-01-01 09:30:00',
                'data': {
                    'code': '000001.SZ',
                    'open': 10.0,
                    'high': 10.5,
                    'low': 9.8,
                    'close': 10.2,
                    'volume': 1000000
                }
            },
            'signal': {
                'portfolio_id': 'test-portfolio-123',
                'engine_id': 'test-engine-123',
                'code': '000001.SZ',
                'direction': 'LONG',
                'timestamp': '2024-01-01 09:30:00',
                'reason': 'Test Signal'
            },
            'order': {
                'portfolio_id': 'test-portfolio-123',
                'code': '000001.SZ',
                'direction': 'LONG',
                'order_type': 'MARKETORDER',
                'quantity': 100,
                'timestamp': '2024-01-01 09:30:00'
            }
        }
    
    @classmethod
    def get_forbidden_patterns(cls) -> List[str]:
        """
        获取禁止的代码模式
        
        Returns:
            List[str]: 禁止的代码模式列表
        """
        return [
            # 文件系统操作
            r'open\s*\(',
            r'with\s+open\s*\(',
            r'os\..*',
            r'sys\..*',
            
            # 网络操作
            r'urllib\.',
            r'requests\.',
            r'socket\.',
            r'http\.',
            
            # 执行操作
            r'eval\s*\(',
            r'exec\s*\(',
            r'__import__\s*\(',
            r'subprocess\.',
            
            # 反射操作
            r'getattr\s*\(',
            r'setattr\s*\(',
            r'hasattr\s*\(',
            r'globals\s*\(',
            r'locals\s*\(',
        ]
    
    @classmethod
    def get_required_patterns(cls, component_type: str) -> List[str]:
        """
        获取必需的代码模式
        
        Args:
            component_type(str): 组件类型
            
        Returns:
            List[str]: 必需的代码模式列表
        """
        patterns = {
            'strategy': [
                r'class\s+\w+\s*\(\s*BaseStrategy\s*\)',
                r'def\s+cal\s*\(',
                r'return\s+.*Signal.*'
            ],
            'analyzer': [
                r'class\s+\w+\s*\(\s*BaseAnalyzer\s*\)',
                r'def\s+_do_activate\s*\(',
                r'def\s+_do_record\s*\('
            ],
            'risk': [
                r'class\s+\w+\s*\(\s*BaseRiskManagement\s*\)',
                r'def\s+cal\s*\(',
                r'def\s+generate_signals\s*\('
            ],
            'sizer': [
                r'class\s+\w+\s*\(\s*BaseSizer\s*\)',
                r'def\s+cal\s*\('
            ]
        }
        
        return patterns.get(component_type, [])