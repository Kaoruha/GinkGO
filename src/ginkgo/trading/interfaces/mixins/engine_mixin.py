# Upstream: Backtest Engines, Portfolio Manager
# Downstream: Data Layer, Event System
# Role: EngineMixin引擎混入类提供引擎交互能力支持引擎绑定和方法调用功能集成实现组件协作支持交易系统功能和组件集成提供完整业务支持






"""
EngineMixin - 引擎功能混入类

提供事件上下文追踪和性能监控功能，增强BaseEngine的能力。

主要功能：
1. 事件上下文追踪 - 追踪事件的完整生命周期
2. 性能监控 - 监控引擎运行性能指标
3. 事件统计 - 详细的事件处理统计
4. 调试支持 - 提供调试和诊断信息

使用方式：
    class MyEngine(BaseEngine, EngineMixin):
        def __init__(self, **kwargs):
            super().__init__(**kwargs)
            # 自动获得EngineMixin的所有功能

Author: TDD Framework
Created: 2024-01-17
"""

import time
import threading
from typing import Dict, Any, List, Optional, Callable
from datetime import datetime, timedelta
from collections import defaultdict, deque
from dataclasses import dataclass, field
import uuid


@dataclass
class EventContext:
    """事件上下文信息"""
    event_id: str
    event_type: str
    timestamp: datetime
    source: Optional[str] = None
    correlation_id: Optional[str] = None
    session_id: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class PerformanceMetrics:
    """性能指标"""
    total_events: int = 0
    processed_events: int = 0
    failed_events: int = 0
    average_processing_time: float = 0.0
    max_processing_time: float = 0.0
    min_processing_time: float = float('inf')
    queue_size_history: deque = field(default_factory=lambda: deque(maxlen=1000))
    throughput_history: deque = field(default_factory=lambda: deque(maxlen=100))
    error_rate: float = 0.0
    uptime_seconds: float = 0.0


class EngineMixin:
    """
    引擎功能混入类

    为BaseEngine提供增强功能，包括事件追踪、性能监控和调试支持。
    """

    def __init__(self, *args, **kwargs):
        """
        初始化Mixin功能
        注意：这个方法会在BaseEngine.__init__之后调用
        """
        # 确保父类已经初始化
        if not hasattr(self, '_engine_id'):
            raise RuntimeError("EngineMixin requires BaseEngine to be initialized first")

        # 事件上下文追踪
        self._event_contexts: Dict[str, EventContext] = {}
        self._context_lock = threading.Lock()

        # 性能监控
        self._performance_metrics = PerformanceMetrics()
        self._performance_lock = threading.Lock()

        # 事件处理时间记录
        self._event_processing_times: Dict[str, float] = {}
        self._processing_times_lock = threading.Lock()

        # 错误记录
        self._error_log: List[Dict[str, Any]] = []
        self._error_log_lock = threading.Lock()

        # 调试模式
        self._debug_mode: bool = kwargs.get('debug_mode', False)
        self._trace_events: bool = kwargs.get('trace_events', False)

        # 性能监控线程
        self._monitoring_active: bool = False
        self._monitoring_thread: Optional[threading.Thread] = None

        # 启动时间
        self._start_time: Optional[datetime] = None

        # 事件处理器注册
        self._event_handlers: Dict[str, List[Callable]] = defaultdict(list)
        self._handlers_lock = threading.Lock()

        # 统计计数器
        self._event_counters: Dict[str, int] = defaultdict(int)
        self._counters_lock = threading.Lock()

    # ========== 事件上下文追踪 ==========

    def _create_event_context(self, event: Any) -> EventContext:
        """
        创建事件上下文

        Args:
            event: 事件对象

        Returns:
            EventContext: 事件上下文信息
        """
        # 生成唯一事件ID
        event_id = f"evt_{uuid.uuid4().hex[:12]}_{int(time.time() * 1000)}"

        # 提取事件类型
        event_type = event.__class__.__name__ if hasattr(event, '__class__') else 'Unknown'

        # 创建上下文
        context = EventContext(
            event_id=event_id,
            event_type=event_type,
            timestamp=datetime.now(),
            source=getattr(event, 'source', None),
            correlation_id=getattr(event, 'correlation_id', None),
            session_id=getattr(self, 'run_id', None),
            metadata={
                'engine_id': self.engine_id,
                'thread_id': threading.current_thread().ident,
            }
        )

        # 添加事件特定信息
        if hasattr(event, 'code'):
            context.metadata['symbol'] = event.code
        if hasattr(event, 'timestamp'):
            context.metadata['event_timestamp'] = event.timestamp

        return context

    def _track_event_start(self, event: Any) -> str:
        """
        开始追踪事件

        Args:
            event: 事件对象

        Returns:
            str: 事件ID
        """
        context = self._create_event_context(event)

        with self._context_lock:
            self._event_contexts[context.event_id] = context

        # 更新计数器
        with self._counters_lock:
            self._event_counters[context.event_type] += 1
            self._event_counters['total_events'] += 1

        # 调试日志
        if self._debug_mode or self._trace_events:
            self.log("DEBUG", f"Event tracking started: {context.event_id} ({context.event_type})")

        return context.event_id

    def _track_event_end(self, event_id: str, success: bool = True,
                        processing_time: float = 0.0, error: Optional[Exception] = None):
        """
        结束事件追踪

        Args:
            event_id: 事件ID
            success: 处理是否成功
            processing_time: 处理时间（秒）
            error: 错误信息（如果有）
        """
        with self._context_lock:
            context = self._event_contexts.get(event_id)
            if context is None:
                return

        # 记录处理时间
        with self._processing_times_lock:
            self._event_processing_times[event_id] = processing_time

        # 更新性能指标
        self._update_performance_metrics(processing_time, success)

        # 记录错误
        if not success and error:
            self._log_error(event_id, context, error)

        # 清理上下文（保留最近1000个）
        with self._context_lock:
            if len(self._event_contexts) > 1000:
                # 删除最旧的200个上下文
                old_ids = list(self._event_contexts.keys())[:200]
                for old_id in old_ids:
                    del self._event_contexts[old_id]

        # 调试日志
        if self._debug_mode or self._trace_events:
            status = "SUCCESS" if success else "FAILED"
            self.log("DEBUG", f"Event tracking ended: {event_id} ({context.event_type}) - {status} in {processing_time:.4f}s")

    def _update_performance_metrics(self, processing_time: float, success: bool):
        """更新性能指标"""
        with self._performance_lock:
            metrics = self._performance_metrics

            # 更新基本计数
            metrics.total_events += 1
            if success:
                metrics.processed_events += 1
            else:
                metrics.failed_events += 1

            # 更新处理时间统计
            if processing_time > 0:
                # 计算新的平均时间
                total_processed = metrics.processed_events + metrics.failed_events
                if total_processed == 1:
                    metrics.average_processing_time = processing_time
                else:
                    metrics.average_processing_time = (
                        (metrics.average_processing_time * (total_processed - 1) + processing_time) / total_processed
                    )

                # 更新最大最小时间
                metrics.max_processing_time = max(metrics.max_processing_time, processing_time)
                metrics.min_processing_time = min(metrics.min_processing_time, processing_time)

            # 更新错误率
            if metrics.total_events > 0:
                metrics.error_rate = metrics.failed_events / metrics.total_events

            # 更新运行时间
            if self._start_time:
                metrics.uptime_seconds = (datetime.now() - self._start_time).total_seconds()

    def _log_error(self, event_id: str, context: EventContext, error: Exception):
        """记录错误信息"""
        error_record = {
            'timestamp': datetime.now(),
            'event_id': event_id,
            'context': context,
            'error_type': error.__class__.__name__,
            'error_message': str(error),
            'thread_id': threading.current_thread().ident
        }

        with self._error_log_lock:
            self._error_log.append(error_record)
            # 只保留最近100个错误
            if len(self._error_log) > 100:
                self._error_log.pop(0)

    # ========== 事件处理增强 ==========

    def put(self, event) -> None:
        """
        增强的事件投递方法

        添加事件追踪和性能监控
        """
        # 追踪事件开始
        event_id = self._track_event_start(event)

        try:
            # 调用父类的put
            super().put(event)
        except Exception as e:
            # 追踪事件失败
            self._track_event_end(event_id, success=False, error=e)
            raise

    def handle_event_with_monitoring(self, event) -> None:
        """
        带监控的事件处理方法

        子类可以重写这个方法来实现具体的事件处理逻辑
        """
        event_id = None
        start_time = time.time()

        try:
            # 尝试获取事件ID（如果已经在put中创建）
            # 这里简化处理，实际实现可能需要更复杂的逻辑
            if hasattr(event, '_event_id'):
                event_id = event._event_id

            # 调用具体的事件处理逻辑
            self.handle_event(event)

            # 记录成功处理
            processing_time = time.time() - start_time
            if event_id:
                self._track_event_end(event_id, success=True, processing_time=processing_time)

        except Exception as e:
            # 记录处理失败
            processing_time = time.time() - start_time
            if event_id:
                self._track_event_end(event_id, success=False, processing_time=processing_time, error=e)
            raise

    # ========== 性能监控 ==========

    def start_performance_monitoring(self, interval: float = 1.0):
        """
        启动性能监控

        Args:
            interval: 监控间隔（秒）
        """
        if self._monitoring_active:
            return

        self._monitoring_active = True
        self._start_time = datetime.now()

        def monitor_loop():
            while self._monitoring_active:
                try:
                    self._collect_performance_sample()
                    time.sleep(interval)
                except Exception as e:
                    self.log("ERROR", f"Performance monitoring error: {e}")

        self._monitoring_thread = threading.Thread(target=monitor_loop, daemon=True)
        self._monitoring_thread.start()

        self.log("INFO", f"Performance monitoring started with interval {interval}s")

    def stop_performance_monitoring(self):
        """停止性能监控"""
        self._monitoring_active = False
        if self._monitoring_thread:
            self._monitoring_thread.join(timeout=5.0)

        self.log("INFO", "Performance monitoring stopped")

    def _collect_performance_sample(self):
        """收集性能样本"""
        with self._performance_lock:
            metrics = self._performance_metrics

            # 记录队列大小
            current_queue_size = 0
            if hasattr(self, '_event_queue'):
                current_queue_size = self._event_queue.qsize()
            metrics.queue_size_history.append(current_queue_size)

            # 计算吞吐量（每秒处理的事件数）
            if len(metrics.queue_size_history) >= 2:
                # 简化的吞吐量计算
                recent_throughput = metrics.processed_events / max(metrics.uptime_seconds, 1.0)
                metrics.throughput_history.append(recent_throughput)

    # ========== 统计和诊断方法 ==========

    def get_performance_metrics(self) -> Dict[str, Any]:
        """
        获取性能指标

        Returns:
            Dict: 详细的性能指标
        """
        with self._performance_lock:
            metrics = self._performance_metrics

            # 计算队列大小统计
            queue_sizes = list(metrics.queue_size_history)
            queue_stats = {}
            if queue_sizes:
                queue_stats = {
                    'current': queue_sizes[-1] if queue_sizes else 0,
                    'average': sum(queue_sizes) / len(queue_sizes),
                    'max': max(queue_sizes),
                    'min': min(queue_sizes)
                }

            # 计算吞吐量统计
            throughputs = list(metrics.throughput_history)
            throughput_stats = {}
            if throughputs:
                throughput_stats = {
                    'current': throughputs[-1] if throughputs else 0.0,
                    'average': sum(throughputs) / len(throughputs),
                    'max': max(throughputs),
                    'min': min(throughputs)
                }

            return {
                'total_events': metrics.total_events,
                'processed_events': metrics.processed_events,
                'failed_events': metrics.failed_events,
                'success_rate': (metrics.processed_events / max(metrics.total_events, 1)) * 100,
                'error_rate': metrics.error_rate * 100,
                'average_processing_time': metrics.average_processing_time,
                'max_processing_time': metrics.max_processing_time,
                'min_processing_time': metrics.min_processing_time if metrics.min_processing_time != float('inf') else 0.0,
                'uptime_seconds': metrics.uptime_seconds,
                'queue_stats': queue_stats,
                'throughput_stats': throughput_stats
            }

    def get_event_statistics(self) -> Dict[str, Any]:
        """
        获取事件统计信息

        Returns:
            Dict: 事件统计信息
        """
        with self._counters_lock:
            stats = dict(self._event_counters)

        # 添加处理中的事件信息
        with self._context_lock:
            stats['processing_events'] = len(self._event_contexts)

        return stats

    def get_recent_errors(self, limit: int = 10) -> List[Dict[str, Any]]:
        """
        获取最近的错误

        Args:
            limit: 返回的错误数量限制

        Returns:
            List: 错误记录列表
        """
        with self._error_log_lock:
            return self._error_log[-limit:] if self._error_log else []

    def get_active_event_contexts(self) -> List[EventContext]:
        """
        获取当前活跃的事件上下文

        Returns:
            List: 活跃的事件上下文列表
        """
        with self._context_lock:
            return list(self._event_contexts.values())

    # ========== 调试支持 ==========

    def enable_debug_mode(self, trace_events: bool = True):
        """
        启用调试模式

        Args:
            trace_events: 是否追踪事件详情
        """
        self._debug_mode = True
        self._trace_events = trace_events
        self.log("INFO", "Debug mode enabled")

    def disable_debug_mode(self):
        """禁用调试模式"""
        self._debug_mode = False
        self._trace_events = False
        self.log("INFO", "Debug mode disabled")

    def dump_event_history(self, limit: int = 100) -> Dict[str, Any]:
        """
        导出事件历史（用于调试）

        Args:
            limit: 导出的事件数量限制

        Returns:
            Dict: 事件历史信息
        """
        with self._processing_times_lock:
            # 获取最近的事件处理时间
            recent_events = sorted(
                self._event_processing_times.items(),
                key=lambda x: x[1],
                reverse=True
            )[:limit]

        with self._context_lock:
            contexts = {
                event_id: self._event_contexts.get(event_id)
                for event_id, _ in recent_events
                if event_id in self._event_contexts
            }

        return {
            'event_count': len(recent_events),
            'processing_times': dict(recent_events),
            'contexts': {k: v for k, v in contexts.items() if v is not None}
        }

    # ========== 生命周期管理 ==========

    def start(self) -> bool:
        """
        增强的启动方法

        添加性能监控启动
        """
        result = super().start()

        if result:
            # 启动性能监控
            if self._debug_mode:
                self.start_performance_monitoring()

            self.log("INFO", f"Engine started with monitoring: debug={self._debug_mode}")

        return result

    def stop(self) -> bool:
        """
        增强的停止方法

        添加性能监控停止和统计输出
        """
        # 停止性能监控
        self.stop_performance_monitoring()

        # 输出最终统计
        if self._debug_mode:
            self._log_final_statistics()

        result = super().stop()

        return result

    def _log_final_statistics(self):
        """输出最终统计信息"""
        metrics = self.get_performance_metrics()
        stats = self.get_event_statistics()

        self.log("INFO", "=== Final Engine Statistics ===")
        self.log("INFO", f"Total Events: {metrics['total_events']}")
        self.log("INFO", f"Processed Events: {metrics['processed_events']}")
        self.log("INFO", f"Failed Events: {metrics['failed_events']}")
        self.log("INFO", f"Success Rate: {metrics['success_rate']:.2f}%")
        self.log("INFO", f"Average Processing Time: {metrics['average_processing_time']:.4f}s")
        self.log("INFO", f"Uptime: {metrics['uptime_seconds']:.2f}s")
        self.log("INFO", "=== End Statistics ===")

    # ========== 事件处理器注册 ==========

    def register_event_handler(self, event_type: str, handler: Callable):
        """
        注册事件处理器

        Args:
            event_type: 事件类型
            handler: 处理函数
        """
        with self._handlers_lock:
            self._event_handlers[event_type].append(handler)

        self.log("INFO", f"Registered handler for {event_type}")

    def unregister_event_handler(self, event_type: str, handler: Callable):
        """
        注销事件处理器

        Args:
            event_type: 事件类型
            handler: 处理函数
        """
        with self._handlers_lock:
            if handler in self._event_handlers[event_type]:
                self._event_handlers[event_type].remove(handler)

        self.log("INFO", f"Unregistered handler for {event_type}")

    def _notify_event_handlers(self, event_type: str, event: Any):
        """
        通知注册的事件处理器

        Args:
            event_type: 事件类型
            event: 事件对象
        """
        with self._handlers_lock:
            handlers = self._event_handlers.get(event_type, [])

        for handler in handlers:
            try:
                handler(event)
            except Exception as e:
                self.log("ERROR", f"Event handler error: {e}")

    # ========== 清理方法 ==========

    def cleanup_monitoring_data(self):
        """清理监控数据"""
        with self._context_lock:
            self._event_contexts.clear()

        with self._performance_lock:
            self._performance_metrics = PerformanceMetrics()

        with self._processing_times_lock:
            self._event_processing_times.clear()

        with self._error_log_lock:
            self._error_log.clear()

        with self._counters_lock:
            self._event_counters.clear()

        self.log("INFO", "Monitoring data cleaned up")