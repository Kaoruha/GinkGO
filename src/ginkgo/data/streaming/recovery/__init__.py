# Upstream: 流式查询引擎, StreamingQueryEngine
# Downstream: ErrorHandler, ErrorClassifier, ErrorSeverity, RecoveryAction, RetryStrategy
# Role: 流式错误恢复子包入口，导出错误分类处理器和重试策略组件






"""
流式查询错误恢复模块

提供智能错误处理、查询恢复管理、重试策略等
错误恢复机制，确保流式查询的稳定性和可靠性。

主要组件：
- ErrorHandler: 错误分类处理器
- RecoveryManager: 查询恢复管理器
- RetryStrategy: 重试策略实现
- CircuitBreaker: 断路器模式实现
"""

from ginkgo.data.streaming.recovery.error_handler import ErrorHandler, ErrorClassifier, ErrorSeverity, RecoveryAction, RetryStrategy

# 暂时注释未实现的模块
# from .recovery_manager import RecoveryManager, RecoveryContext, RecoveryResult
# from .circuit_breaker import CircuitBreaker, CircuitState, CircuitBreakerConfig

__all__ = [
    "ErrorHandler",
    "ErrorClassifier",
    "ErrorSeverity",
    "RecoveryAction",
    "RetryStrategy",
    # "RecoveryManager",
    # "RecoveryContext", 
    # "RecoveryResult",
    # "CircuitBreaker",
    # "CircuitState",
    # "CircuitBreakerConfig",
]

