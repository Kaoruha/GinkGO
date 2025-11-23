"""
T5架构事件追踪模块

提供分布式追踪和事件链路监控功能
"""

import time
import threading
from datetime import datetime
from ginkgo.trading.time.clock import now as clock_now
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any, Set
from uuid import uuid4
from contextlib import contextmanager
from enum import Enum

from ginkgo.libs import GLOG


class SpanKind(Enum):
    """Span类型"""
    CLIENT = "client"
    SERVER = "server"
    PRODUCER = "producer"
    CONSUMER = "consumer"
    INTERNAL = "internal"


class SpanStatus(Enum):
    """Span状态"""
    OK = "ok"
    ERROR = "error"
    TIMEOUT = "timeout"
    CANCELED = "canceled"


@dataclass
class TraceContext:
    """追踪上下文"""
    trace_id: str
    span_id: str
    parent_span_id: Optional[str] = None
    baggage: Dict[str, str] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            'trace_id': self.trace_id,
            'span_id': self.span_id,
            'parent_span_id': self.parent_span_id,
            'baggage': self.baggage
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'TraceContext':
        """从字典创建"""
        return cls(
            trace_id=data['trace_id'],
            span_id=data['span_id'],
            parent_span_id=data.get('parent_span_id'),
            baggage=data.get('baggage', {})
        )
    
    def child_context(self) -> 'TraceContext':
        """创建子上下文"""
        return TraceContext(
            trace_id=self.trace_id,
            span_id=uuid4().hex[:16],
            parent_span_id=self.span_id,
            baggage=self.baggage.copy()
        )


@dataclass
class TraceSpan:
    """追踪span"""
    trace_id: str
    span_id: str
    parent_span_id: Optional[str]
    operation_name: str
    kind: SpanKind
    start_time: datetime
    end_time: Optional[datetime] = None
    duration_ms: Optional[float] = None
    status: SpanStatus = SpanStatus.OK
    tags: Dict[str, str] = field(default_factory=dict)
    logs: List[Dict[str, Any]] = field(default_factory=list)
    
    def finish(self, status: SpanStatus = SpanStatus.OK) -> None:
        """完成span"""
        if self.end_time is None:
            self.end_time = clock_now()
            self.duration_ms = (self.end_time - self.start_time).total_seconds() * 1000
            self.status = status
    
    def set_tag(self, key: str, value: str) -> None:
        """设置标签"""
        self.tags[key] = value
    
    def log(self, message: str, level: str = "info", **kwargs) -> None:
        """记录日志"""
        log_entry = {
            'timestamp': clock_now().isoformat(),
            'message': message,
            'level': level,
            **kwargs
        }
        self.logs.append(log_entry)
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            'trace_id': self.trace_id,
            'span_id': self.span_id,
            'parent_span_id': self.parent_span_id,
            'operation_name': self.operation_name,
            'kind': self.kind.value,
            'start_time': self.start_time.isoformat(),
            'end_time': self.end_time.isoformat() if self.end_time else None,
            'duration_ms': self.duration_ms,
            'status': self.status.value,
            'tags': self.tags,
            'logs': self.logs
        }


class EventTracer:
    """事件追踪器"""
    
    def __init__(self, max_spans: int = 10000):
        self.max_spans = max_spans
        self._spans: Dict[str, TraceSpan] = {}
        self._active_spans: Dict[int, TraceContext] = {}  # thread_id -> context
        self._traces: Dict[str, List[str]] = {}  # trace_id -> [span_ids]
        self._lock = threading.Lock()
        self._exporters: List['SpanExporter'] = []
        
    def start_trace(self, operation_name: str, kind: SpanKind = SpanKind.INTERNAL,
                   parent_context: Optional[TraceContext] = None) -> TraceContext:
        """开始新的追踪"""
        if parent_context:
            context = parent_context.child_context()
        else:
            context = TraceContext(
                trace_id=uuid4().hex[:16],
                span_id=uuid4().hex[:16]
            )
        
        span = TraceSpan(
            trace_id=context.trace_id,
            span_id=context.span_id,
            parent_span_id=context.parent_span_id,
            operation_name=operation_name,
            kind=kind,
            start_time=clock_now()
        )
        
        with self._lock:
            self._spans[span.span_id] = span
            
            if span.trace_id not in self._traces:
                self._traces[span.trace_id] = []
            self._traces[span.trace_id].append(span.span_id)
            
            # 设置当前线程的活跃span
            thread_id = threading.get_ident()
            self._active_spans[thread_id] = context
            
            # 限制span数量
            if len(self._spans) > self.max_spans:
                self._cleanup_old_spans()
        
        return context
    
    def finish_span(self, context: TraceContext, status: SpanStatus = SpanStatus.OK) -> None:
        """完成span"""
        with self._lock:
            if context.span_id in self._spans:
                span = self._spans[context.span_id]
                span.finish(status)
                
                # 导出span
                self._export_span(span)
                
                # 清理当前线程的活跃span
                thread_id = threading.get_ident()
                if (thread_id in self._active_spans and 
                    self._active_spans[thread_id].span_id == context.span_id):
                    if context.parent_span_id and context.parent_span_id in self._spans:
                        # 恢复父span为活跃span
                        parent_span = self._spans[context.parent_span_id]
                        self._active_spans[thread_id] = TraceContext(
                            trace_id=parent_span.trace_id,
                            span_id=parent_span.span_id,
                            parent_span_id=parent_span.parent_span_id,
                            baggage=context.baggage
                        )
                    else:
                        del self._active_spans[thread_id]
    
    def get_current_context(self) -> Optional[TraceContext]:
        """获取当前线程的追踪上下文"""
        thread_id = threading.get_ident()
        return self._active_spans.get(thread_id)
    
    def set_tag(self, key: str, value: str, context: Optional[TraceContext] = None) -> None:
        """设置标签"""
        if context is None:
            context = self.get_current_context()
        
        if context and context.span_id in self._spans:
            self._spans[context.span_id].set_tag(key, value)
    
    def log(self, message: str, level: str = "info", 
            context: Optional[TraceContext] = None, **kwargs) -> None:
        """记录日志"""
        if context is None:
            context = self.get_current_context()
        
        if context and context.span_id in self._spans:
            self._spans[context.span_id].log(message, level, **kwargs)
    
    def get_span(self, span_id: str) -> Optional[TraceSpan]:
        """获取span"""
        return self._spans.get(span_id)
    
    def get_trace(self, trace_id: str) -> List[TraceSpan]:
        """获取完整追踪链路"""
        span_ids = self._traces.get(trace_id, [])
        return [self._spans[span_id] for span_id in span_ids if span_id in self._spans]
    
    def get_active_traces(self) -> List[str]:
        """获取活跃的trace ID列表"""
        active_traces = set()
        for context in self._active_spans.values():
            active_traces.add(context.trace_id)
        return list(active_traces)
    
    def add_exporter(self, exporter: 'SpanExporter') -> None:
        """添加span导出器"""
        self._exporters.append(exporter)
    
    @contextmanager
    def trace(self, operation_name: str, kind: SpanKind = SpanKind.INTERNAL,
              parent_context: Optional[TraceContext] = None):
        """追踪上下文管理器"""
        context = self.start_trace(operation_name, kind, parent_context)
        try:
            yield context
        except Exception as e:
            self.log(f"Exception in {operation_name}: {str(e)}", "error")
            self.finish_span(context, SpanStatus.ERROR)
            raise
        else:
            self.finish_span(context, SpanStatus.OK)
    
    def _export_span(self, span: TraceSpan) -> None:
        """导出span"""
        for exporter in self._exporters:
            try:
                exporter.export_span(span)
            except Exception as e:
                GLOG.WARN(f"导出span失败: {e}")
    
    def _cleanup_old_spans(self) -> None:
        """清理旧的span"""
        # 按结束时间排序，删除最旧的10%
        completed_spans = [
            (span_id, span) for span_id, span in self._spans.items()
            if span.end_time is not None
        ]
        
        if len(completed_spans) > self.max_spans * 0.1:
            # 按结束时间排序
            completed_spans.sort(key=lambda x: x[1].end_time or datetime.min)
            
            # 删除最旧的10%
            to_remove = int(len(completed_spans) * 0.1)
            for span_id, span in completed_spans[:to_remove]:
                del self._spans[span_id]
                
                # 从traces中移除
                if span.trace_id in self._traces:
                    if span_id in self._traces[span.trace_id]:
                        self._traces[span.trace_id].remove(span_id)
                    
                    # 如果trace没有span了，删除trace
                    if not self._traces[span.trace_id]:
                        del self._traces[span.trace_id]


class SpanExporter:
    """Span导出器基类"""
    
    def export_span(self, span: TraceSpan) -> None:
        """导出span"""
        raise NotImplementedError


class ConsoleSpanExporter(SpanExporter):
    """控制台span导出器"""
    
    def export_span(self, span: TraceSpan) -> None:
        """导出到控制台"""
        if span.status == SpanStatus.ERROR:
            GLOG.ERROR(f"TRACE [{span.trace_id[:8]}] {span.operation_name} "
                      f"({span.duration_ms:.1f}ms) - {span.status.value}")
        else:
            GLOG.DEBUG(f"TRACE [{span.trace_id[:8]}] {span.operation_name} "
                      f"({span.duration_ms:.1f}ms) - {span.status.value}")


class FileSpanExporter(SpanExporter):
    """文件span导出器"""
    
    def __init__(self, filename: str):
        self.filename = filename
        self._lock = threading.Lock()
    
    def export_span(self, span: TraceSpan) -> None:
        """导出到文件"""
        import json
        
        with self._lock:
            try:
                with open(self.filename, 'a', encoding='utf-8') as f:
                    json.dump(span.to_dict(), f, ensure_ascii=False)
                    f.write('\n')
            except Exception as e:
                GLOG.WARN(f"写入trace文件失败: {e}")


class MemorySpanExporter(SpanExporter):
    """内存span导出器（用于测试）"""
    
    def __init__(self, max_spans: int = 1000):
        self.max_spans = max_spans
        self.spans: List[TraceSpan] = []
        self._lock = threading.Lock()
    
    def export_span(self, span: TraceSpan) -> None:
        """导出到内存"""
        with self._lock:
            self.spans.append(span)
            
            # 限制数量
            if len(self.spans) > self.max_spans:
                self.spans = self.spans[-self.max_spans:]
    
    def get_spans(self) -> List[TraceSpan]:
        """获取所有spans"""
        with self._lock:
            return self.spans.copy()
    
    def clear(self) -> None:
        """清空spans"""
        with self._lock:
            self.spans.clear()


# 追踪装饰器
def traced(operation_name: str = None, kind: SpanKind = SpanKind.INTERNAL):
    """追踪装饰器"""
    def decorator(func):
        nonlocal operation_name
        if operation_name is None:
            operation_name = f"{func.__module__}.{func.__name__}"
        
        def wrapper(*args, **kwargs):
            tracer = get_tracer()
            with tracer.trace(operation_name, kind):
                return func(*args, **kwargs)
        
        return wrapper
    return decorator


# 全局追踪器实例
_global_tracer = EventTracer()
_global_tracer.add_exporter(ConsoleSpanExporter())


def get_tracer() -> EventTracer:
    """获取全局追踪器"""
    return _global_tracer


def start_trace(operation_name: str, kind: SpanKind = SpanKind.INTERNAL,
               parent_context: Optional[TraceContext] = None) -> TraceContext:
    """便捷函数：开始追踪"""
    return _global_tracer.start_trace(operation_name, kind, parent_context)


def finish_span(context: TraceContext, status: SpanStatus = SpanStatus.OK) -> None:
    """便捷函数：完成span"""
    _global_tracer.finish_span(context, status)


def get_current_context() -> Optional[TraceContext]:
    """便捷函数：获取当前上下文"""
    return _global_tracer.get_current_context()


def trace(operation_name: str, kind: SpanKind = SpanKind.INTERNAL,
          parent_context: Optional[TraceContext] = None):
    """便捷函数：追踪上下文管理器"""
    return _global_tracer.trace(operation_name, kind, parent_context)
