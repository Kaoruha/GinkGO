"""
智能错误处理和分类系统

提供错误分类、严重程度评估、智能重试策略等功能，
确保流式查询在各种异常情况下的稳定性和可恢复性。

核心功能：
- 错误自动分类和严重程度评估
- 智能重试策略（指数退避、电路熔断）
- 错误模式识别和预防
- 详细错误报告和分析
"""

import time
import random
import threading
from typing import Any, Dict, List, Optional, Callable, Type, Union
from dataclasses import dataclass, field
from enum import Enum
from collections import defaultdict, deque

try:
    from ginkgo.libs import GLOG

    _has_ginkgo_logger = True
except ImportError:
    _has_ginkgo_logger = False
    import logging

    GLOG = logging.getLogger(__name__)


class ErrorSeverity(Enum):
    """错误严重程度"""

    LOW = "low"  # 轻微错误，可以忽略或简单重试
    MEDIUM = "medium"  # 中等错误，需要重试和监控
    HIGH = "high"  # 严重错误，需要特殊处理
    CRITICAL = "critical"  # 严重错误，可能导致系统不稳定


class RecoveryAction(Enum):
    """恢复动作"""

    RETRY = "retry"  # 简单重试
    RETRY_WITH_BACKOFF = "retry_backoff"  # 指数退避重试
    FALLBACK = "fallback"  # 降级处理
    ABORT = "abort"  # 终止操作
    RESET_CONNECTION = "reset_conn"  # 重置连接
    REDUCE_BATCH_SIZE = "reduce_batch"  # 减少批次大小


class RetryStrategy(Enum):
    """重试策略"""

    IMMEDIATE = "immediate"  # 立即重试
    LINEAR_BACKOFF = "linear"  # 线性退避
    EXPONENTIAL_BACKOFF = "exponential"  # 指数退避
    JITTERED_BACKOFF = "jittered"  # 带抖动的指数退避


@dataclass
class ErrorPattern:
    """错误模式"""

    error_type: str
    message_pattern: str
    severity: ErrorSeverity
    recovery_action: RecoveryAction
    retry_strategy: RetryStrategy
    max_retries: int = 3
    backoff_multiplier: float = 2.0
    description: str = ""


@dataclass
class ErrorContext:
    """错误上下文"""

    timestamp: float
    error: Exception
    error_type: str
    severity: ErrorSeverity
    retry_count: int
    operation: str
    additional_info: Dict[str, Any] = field(default_factory=dict)

    @property
    def error_message(self) -> str:
        """错误消息"""
        return str(self.error)


@dataclass
class RetryResult:
    """重试结果"""

    success: bool
    attempts: int
    total_delay: float
    final_error: Optional[Exception] = None
    recovery_action: Optional[RecoveryAction] = None


class ErrorClassifier:
    """错误分类器"""

    def __init__(self):
        # 预定义错误模式
        self.error_patterns = [
            # 数据库连接错误
            ErrorPattern(
                error_type="ConnectionError",
                message_pattern="connection.*failed|connection.*refused|connection.*timeout",
                severity=ErrorSeverity.HIGH,
                recovery_action=RecoveryAction.RESET_CONNECTION,
                retry_strategy=RetryStrategy.EXPONENTIAL_BACKOFF,
                max_retries=5,
                description="数据库连接失败",
            ),
            # 内存不足错误
            ErrorPattern(
                error_type="MemoryError",
                message_pattern="out of memory|memory.*exceed|insufficient.*memory",
                severity=ErrorSeverity.CRITICAL,
                recovery_action=RecoveryAction.REDUCE_BATCH_SIZE,
                retry_strategy=RetryStrategy.JITTERED_BACKOFF,
                max_retries=3,
                description="内存不足",
            ),
            # 超时错误
            ErrorPattern(
                error_type="TimeoutError",
                message_pattern="timeout|time.*out|deadline.*exceed",
                severity=ErrorSeverity.MEDIUM,
                recovery_action=RecoveryAction.RETRY_WITH_BACKOFF,
                retry_strategy=RetryStrategy.LINEAR_BACKOFF,
                max_retries=3,
                description="操作超时",
            ),
            # SQL错误
            ErrorPattern(
                error_type="DatabaseError",
                message_pattern="sql.*error|syntax.*error|table.*not.*found",
                severity=ErrorSeverity.HIGH,
                recovery_action=RecoveryAction.ABORT,
                retry_strategy=RetryStrategy.IMMEDIATE,
                max_retries=0,
                description="SQL查询错误",
            ),
            # 权限错误
            ErrorPattern(
                error_type="PermissionError",
                message_pattern="permission.*denied|access.*denied|unauthorized",
                severity=ErrorSeverity.HIGH,
                recovery_action=RecoveryAction.ABORT,
                retry_strategy=RetryStrategy.IMMEDIATE,
                max_retries=0,
                description="权限不足",
            ),
            # 网络错误
            ErrorPattern(
                error_type="NetworkError",
                message_pattern="network.*error|connection.*reset|host.*unreachable",
                severity=ErrorSeverity.MEDIUM,
                recovery_action=RecoveryAction.RETRY_WITH_BACKOFF,
                retry_strategy=RetryStrategy.EXPONENTIAL_BACKOFF,
                max_retries=4,
                description="网络连接问题",
            ),
        ]

        # 错误统计
        self.error_counts = defaultdict(int)
        self.error_history = deque(maxlen=1000)

    def classify_error(self, error: Exception, operation: str = "") -> ErrorContext:
        """
        分类错误并生成错误上下文

        Args:
            error: 异常对象
            operation: 操作描述

        Returns:
            错误上下文
        """
        import re

        error_type = type(error).__name__
        error_message = str(error).lower()

        # 匹配错误模式
        severity = ErrorSeverity.LOW
        for pattern in self.error_patterns:
            if pattern.error_type == error_type or re.search(pattern.message_pattern, error_message, re.IGNORECASE):
                severity = pattern.severity
                break

        # 创建错误上下文
        context = ErrorContext(
            timestamp=time.time(),
            error=error,
            error_type=error_type,
            severity=severity,
            retry_count=0,
            operation=operation,
            additional_info={
                "error_class": error.__class__.__module__ + "." + error.__class__.__name__,
                "error_args": error.args,
            },
        )

        # 更新统计
        self.error_counts[error_type] += 1
        self.error_history.append(context)

        return context

    def get_recovery_strategy(self, context: ErrorContext) -> Optional[ErrorPattern]:
        """
        获取恢复策略

        Args:
            context: 错误上下文

        Returns:
            匹配的错误模式
        """
        import re

        error_message = context.error_message.lower()

        for pattern in self.error_patterns:
            if pattern.error_type == context.error_type or re.search(
                pattern.message_pattern, error_message, re.IGNORECASE
            ):
                return pattern

        # 默认策略
        return ErrorPattern(
            error_type="Unknown",
            message_pattern=".*",
            severity=ErrorSeverity.MEDIUM,
            recovery_action=RecoveryAction.RETRY,
            retry_strategy=RetryStrategy.LINEAR_BACKOFF,
            max_retries=2,
            description="未知错误",
        )

    def get_error_statistics(self) -> Dict[str, Any]:
        """获取错误统计信息"""
        recent_errors = [ctx for ctx in self.error_history if time.time() - ctx.timestamp < 3600]  # 最近1小时

        severity_counts = defaultdict(int)
        for ctx in recent_errors:
            severity_counts[ctx.severity.value] += 1

        return {
            "total_errors": len(self.error_history),
            "recent_errors": len(recent_errors),
            "error_types": dict(self.error_counts),
            "severity_distribution": dict(severity_counts),
            "most_common_errors": [
                {"type": error_type, "count": count}
                for error_type, count in sorted(self.error_counts.items(), key=lambda x: x[1], reverse=True)[:5]
            ],
        }


class ErrorHandler:
    """错误处理器"""

    def __init__(self, max_consecutive_failures: int = 5):
        """
        初始化错误处理器

        Args:
            max_consecutive_failures: 最大连续失败次数
        """
        self.classifier = ErrorClassifier()
        self.max_consecutive_failures = max_consecutive_failures
        self.consecutive_failures = defaultdict(int)
        self._lock = threading.Lock()

        GLOG.DEBUG("ErrorHandler initialized")

    def handle_error(self, error: Exception, operation: str = "", retry_count: int = 0) -> ErrorContext:
        """
        处理错误

        Args:
            error: 异常对象
            operation: 操作描述
            retry_count: 当前重试次数

        Returns:
            错误上下文
        """
        context = self.classifier.classify_error(error, operation)
        context.retry_count = retry_count

        # 记录连续失败
        with self._lock:
            if context.severity in [ErrorSeverity.HIGH, ErrorSeverity.CRITICAL]:
                self.consecutive_failures[operation] += 1
            else:
                self.consecutive_failures[operation] = 0

        # 记录日志
        log_level = {
            ErrorSeverity.LOW: "DEBUG",
            ErrorSeverity.MEDIUM: "WARNING",
            ErrorSeverity.HIGH: "ERROR",
            ErrorSeverity.CRITICAL: "CRITICAL",
        }.get(context.severity, "ERROR")

        getattr(GLOG, log_level)(
            f"Error in operation '{operation}': {context.error_message} "
            f"(severity: {context.severity.value}, retry: {retry_count})"
        )

        return context

    def should_retry(self, context: ErrorContext, operation: str = "") -> bool:
        """
        判断是否应该重试

        Args:
            context: 错误上下文
            operation: 操作描述

        Returns:
            是否应该重试
        """
        # 检查连续失败次数
        if self.consecutive_failures.get(operation, 0) >= self.max_consecutive_failures:
            GLOG.ERROR(f"Too many consecutive failures for operation '{operation}'")
            return False

        # 获取恢复策略
        strategy = self.classifier.get_recovery_strategy(context)
        if not strategy:
            return False

        # 检查最大重试次数
        if context.retry_count >= strategy.max_retries:
            return False

        # 检查恢复动作
        if strategy.recovery_action == RecoveryAction.ABORT:
            return False

        return True

    def execute_with_retry(self, operation: Callable, operation_name: str = "", *args, **kwargs) -> RetryResult:
        """
        带重试的操作执行

        Args:
            operation: 要执行的操作
            operation_name: 操作名称
            *args, **kwargs: 操作参数

        Returns:
            重试结果
        """
        attempts = 0
        total_delay = 0.0
        start_time = time.time()

        while True:
            attempts += 1

            try:
                result = operation(*args, **kwargs)

                # 成功，重置连续失败计数
                with self._lock:
                    self.consecutive_failures[operation_name] = 0

                return RetryResult(success=True, attempts=attempts, total_delay=total_delay)

            except Exception as error:
                # 处理错误
                context = self.handle_error(error, operation_name, attempts - 1)

                # 检查是否应该重试
                if not self.should_retry(context, operation_name):
                    return RetryResult(success=False, attempts=attempts, total_delay=total_delay, final_error=error)

                # 计算延迟时间
                strategy = self.classifier.get_recovery_strategy(context)
                delay = self._calculate_delay(strategy, attempts - 1)

                if delay > 0:
                    GLOG.DEBUG(f"Retrying operation '{operation_name}' in {delay:.2f}s (attempt {attempts})")
                    time.sleep(delay)
                    total_delay += delay

                # 检查总时间限制（防止无限重试）
                if time.time() - start_time > 300:  # 5分钟
                    GLOG.ERROR(f"Operation '{operation_name}' timeout after {attempts} attempts")
                    return RetryResult(success=False, attempts=attempts, total_delay=total_delay, final_error=error)

    def _calculate_delay(self, strategy: ErrorPattern, attempt: int) -> float:
        """
        计算重试延迟时间

        Args:
            strategy: 错误模式
            attempt: 尝试次数

        Returns:
            延迟时间（秒）
        """
        base_delay = 1.0

        if strategy.retry_strategy == RetryStrategy.IMMEDIATE:
            return 0.0
        elif strategy.retry_strategy == RetryStrategy.LINEAR_BACKOFF:
            return base_delay * (attempt + 1)
        elif strategy.retry_strategy == RetryStrategy.EXPONENTIAL_BACKOFF:
            return base_delay * (strategy.backoff_multiplier**attempt)
        elif strategy.retry_strategy == RetryStrategy.JITTERED_BACKOFF:
            exponential_delay = base_delay * (strategy.backoff_multiplier**attempt)
            jitter = random.uniform(0.1, 0.5) * exponential_delay
            return exponential_delay + jitter

        return base_delay

    def reset_failure_count(self, operation: str):
        """重置操作的失败计数"""
        with self._lock:
            self.consecutive_failures[operation] = 0
        GLOG.DEBUG(f"Reset failure count for operation: {operation}")

    def get_failure_statistics(self) -> Dict[str, Any]:
        """获取失败统计信息"""
        with self._lock:
            failure_stats = dict(self.consecutive_failures)

        error_stats = self.classifier.get_error_statistics()

        return {
            "consecutive_failures": failure_stats,
            "error_statistics": error_stats,
            "high_failure_operations": [
                op for op, count in failure_stats.items() if count >= self.max_consecutive_failures // 2
            ],
        }
