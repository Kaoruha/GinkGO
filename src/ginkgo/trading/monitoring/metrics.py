"""
T5架构指标收集模块

提供统一的指标收集、聚合和报告功能
"""

import time
import threading
from datetime import datetime, timedelta
from ginkgo.trading.time.clock import now as clock_now
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any, Callable
from collections import defaultdict, deque
from enum import Enum

from ginkgo.libs import GLOG


class MetricType(Enum):
    """指标类型"""
    COUNTER = "counter"
    GAUGE = "gauge"
    HISTOGRAM = "histogram"
    TIMER = "timer"


@dataclass
class MetricPoint:
    """指标点"""
    name: str
    value: float
    metric_type: MetricType
    timestamp: datetime
    labels: Dict[str, str] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            'name': self.name,
            'value': self.value,
            'type': self.metric_type.value,
            'timestamp': self.timestamp.isoformat(),
            'labels': self.labels
        }


@dataclass
class PerformanceMetrics:
    """性能指标"""
    # 时间指标
    avg_response_time: float = 0.0
    max_response_time: float = 0.0
    min_response_time: float = float('inf')
    p95_response_time: float = 0.0
    p99_response_time: float = 0.0
    
    # 吞吐量指标
    requests_per_second: float = 0.0
    total_requests: int = 0
    failed_requests: int = 0
    
    # 资源指标
    cpu_usage_percent: float = 0.0
    memory_usage_mb: float = 0.0
    
    # 更新时间
    last_update: datetime = field(default_factory=clock_now)
    
    @property
    def success_rate(self) -> float:
        """成功率"""
        if self.total_requests == 0:
            return 100.0
        return ((self.total_requests - self.failed_requests) / self.total_requests) * 100.0


@dataclass
class SystemMetrics:
    """系统指标"""
    # 系统状态
    uptime_seconds: float = 0.0
    
    # 线程和协程
    active_threads: int = 0
    active_tasks: int = 0
    
    # 网络指标
    network_connections: int = 0
    bytes_sent: int = 0
    bytes_received: int = 0
    
    # 数据库连接
    db_connections_active: int = 0
    db_connections_idle: int = 0
    
    # 缓存指标
    cache_hits: int = 0
    cache_misses: int = 0
    
    @property
    def cache_hit_rate(self) -> float:
        """缓存命中率"""
        total_cache_requests = self.cache_hits + self.cache_misses
        if total_cache_requests == 0:
            return 0.0
        return (self.cache_hits / total_cache_requests) * 100.0


@dataclass
class TradingMetrics:
    """交易指标"""
    # 订单指标
    total_orders: int = 0
    filled_orders: int = 0
    cancelled_orders: int = 0
    rejected_orders: int = 0
    
    # 成交指标
    total_trades: int = 0
    total_volume: float = 0.0
    total_turnover: float = 0.0
    
    # 延迟指标
    order_to_fill_latency_ms: float = 0.0
    market_data_latency_ms: float = 0.0
    
    # 风险指标
    position_count: int = 0
    total_pnl: float = 0.0
    max_drawdown: float = 0.0
    
    @property
    def fill_rate(self) -> float:
        """订单成交率"""
        if self.total_orders == 0:
            return 0.0
        return (self.filled_orders / self.total_orders) * 100.0
    
    @property
    def average_trade_size(self) -> float:
        """平均成交规模"""
        if self.total_trades == 0:
            return 0.0
        return self.total_volume / self.total_trades


class MetricsCollector:
    """指标收集器"""
    
    def __init__(self, max_history: int = 10000):
        self.max_history = max_history
        self._metrics: Dict[str, deque] = defaultdict(lambda: deque(maxlen=max_history))
        self._counters: Dict[str, float] = defaultdict(float)
        self._gauges: Dict[str, float] = defaultdict(float)
        self._timers: Dict[str, List[float]] = defaultdict(list)
        
        self._lock = threading.Lock()
        self._collectors: List[Callable[[], Dict[str, Any]]] = []
        self._start_time = clock_now()
        
        # 性能监控
        self.performance_metrics = PerformanceMetrics()
        self.system_metrics = SystemMetrics() 
        self.trading_metrics = TradingMetrics()
    
    def register_collector(self, collector_func: Callable[[], Dict[str, Any]]) -> None:
        """注册自定义指标收集器"""
        self._collectors.append(collector_func)
    
    def increment_counter(self, name: str, value: float = 1.0, labels: Dict[str, str] = None) -> None:
        """递增计数器"""
        with self._lock:
            key = self._build_metric_key(name, labels)
            self._counters[key] += value
            
            metric_point = MetricPoint(
                name=name,
                value=self._counters[key],
                metric_type=MetricType.COUNTER,
                timestamp=clock_now(),
                labels=labels or {}
            )
            self._metrics[key].append(metric_point)
    
    def set_gauge(self, name: str, value: float, labels: Dict[str, str] = None) -> None:
        """设置仪表值"""
        with self._lock:
            key = self._build_metric_key(name, labels)
            self._gauges[key] = value
            
            metric_point = MetricPoint(
                name=name,
                value=value,
                metric_type=MetricType.GAUGE,
                timestamp=clock_now(),
                labels=labels or {}
            )
            self._metrics[key].append(metric_point)
    
    def record_timer(self, name: str, duration_ms: float, labels: Dict[str, str] = None) -> None:
        """记录时间指标"""
        with self._lock:
            key = self._build_metric_key(name, labels)
            self._timers[key].append(duration_ms)
            
            # 保持最近1000个记录
            if len(self._timers[key]) > 1000:
                self._timers[key] = self._timers[key][-1000:]
            
            metric_point = MetricPoint(
                name=name,
                value=duration_ms,
                metric_type=MetricType.TIMER,
                timestamp=clock_now(),
                labels=labels or {}
            )
            self._metrics[key].append(metric_point)
    
    def time_it(self, name: str, labels: Dict[str, str] = None):
        """时间装饰器/上下文管理器"""
        class TimerContext:
            def __init__(self, collector, metric_name, metric_labels):
                self.collector = collector
                self.metric_name = metric_name
                self.metric_labels = metric_labels
                self.start_time = None
            
            def __enter__(self):
                self.start_time = time.time()
                return self
            
            def __exit__(self, exc_type, exc_val, exc_tb):
                duration_ms = (time.time() - self.start_time) * 1000
                self.collector.record_timer(self.metric_name, duration_ms, self.metric_labels)
        
        return TimerContext(self, name, labels)
    
    def record_histogram(self, name: str, value: float, labels: Dict[str, str] = None) -> None:
        """记录直方图值"""
        with self._lock:
            key = self._build_metric_key(name, labels)
            
            metric_point = MetricPoint(
                name=name,
                value=value,
                metric_type=MetricType.HISTOGRAM,
                timestamp=clock_now(),
                labels=labels or {}
            )
            self._metrics[key].append(metric_point)
    
    def get_current_metrics(self) -> Dict[str, Any]:
        """获取当前指标快照"""
        with self._lock:
            metrics = {
                'timestamp': clock_now().isoformat(),
                'uptime_seconds': (clock_now() - self._start_time).total_seconds(),
                'counters': dict(self._counters),
                'gauges': dict(self._gauges),
                'timers_summary': self._get_timer_summary()
            }
            
            # 添加性能指标
            metrics['performance'] = {
                'avg_response_time': self.performance_metrics.avg_response_time,
                'requests_per_second': self.performance_metrics.requests_per_second,
                'success_rate': self.performance_metrics.success_rate,
                'cpu_usage_percent': self.performance_metrics.cpu_usage_percent,
                'memory_usage_mb': self.performance_metrics.memory_usage_mb
            }
            
            # 添加系统指标
            metrics['system'] = {
                'active_threads': self.system_metrics.active_threads,
                'active_tasks': self.system_metrics.active_tasks,
                'cache_hit_rate': self.system_metrics.cache_hit_rate,
                'db_connections_active': self.system_metrics.db_connections_active
            }
            
            # 添加交易指标
            metrics['trading'] = {
                'total_orders': self.trading_metrics.total_orders,
                'fill_rate': self.trading_metrics.fill_rate,
                'total_trades': self.trading_metrics.total_trades,
                'total_pnl': self.trading_metrics.total_pnl
            }
            
            # 运行自定义收集器
            for collector in self._collectors:
                try:
                    custom_metrics = collector()
                    if isinstance(custom_metrics, dict):
                        metrics.update(custom_metrics)
                except Exception as e:
                    GLOG.ERROR(f"自定义指标收集器错误: {e}")
            
            return metrics
    
    def get_metrics_history(self, name: str, labels: Dict[str, str] = None, 
                           limit: int = 100) -> List[MetricPoint]:
        """获取指标历史"""
        key = self._build_metric_key(name, labels)
        with self._lock:
            if key not in self._metrics:
                return []
            
            history = list(self._metrics[key])
            return history[-limit:] if limit > 0 else history
    
    def get_metrics_summary(self, time_window: timedelta = None) -> Dict[str, Any]:
        """获取指标摘要"""
        if time_window is None:
            time_window = timedelta(minutes=5)
        
        cutoff_time = clock_now() - time_window
        summary = {}
        
        with self._lock:
            for metric_key, history in self._metrics.items():
                recent_points = [
                    point for point in history 
                    if point.timestamp >= cutoff_time
                ]
                
                if recent_points:
                    values = [point.value for point in recent_points]
                    summary[metric_key] = {
                        'count': len(values),
                        'avg': sum(values) / len(values),
                        'min': min(values),
                        'max': max(values),
                        'latest': recent_points[-1].value,
                        'metric_type': recent_points[-1].metric_type.value
                    }
        
        return summary
    
    def reset_metrics(self) -> None:
        """重置所有指标"""
        with self._lock:
            self._metrics.clear()
            self._counters.clear()
            self._gauges.clear()
            self._timers.clear()
            
            # 重置结构化指标
            self.performance_metrics = PerformanceMetrics()
            self.system_metrics = SystemMetrics()
            self.trading_metrics = TradingMetrics()
            
            self._start_time = clock_now()
    
    def export_prometheus_format(self) -> str:
        """导出Prometheus格式指标"""
        lines = []
        current_time = int(time.time() * 1000)
        
        with self._lock:
            # 导出计数器
            for key, value in self._counters.items():
                name, labels_str = self._parse_metric_key(key)
                lines.append(f"# TYPE {name} counter")
                lines.append(f"{name}{labels_str} {value} {current_time}")
            
            # 导出仪表
            for key, value in self._gauges.items():
                name, labels_str = self._parse_metric_key(key)
                lines.append(f"# TYPE {name} gauge")
                lines.append(f"{name}{labels_str} {value} {current_time}")
        
        return '\n'.join(lines)
    
    def _build_metric_key(self, name: str, labels: Dict[str, str] = None) -> str:
        """构建指标键"""
        if not labels:
            return name
        
        label_pairs = [f"{k}={v}" for k, v in sorted(labels.items())]
        return f"{name}{{{','.join(label_pairs)}}}"
    
    def _parse_metric_key(self, key: str) -> tuple:
        """解析指标键"""
        if '{' not in key:
            return key, ""
        
        name, labels_part = key.split('{', 1)
        labels_part = labels_part.rstrip('}')
        return name, f"{{{labels_part}}}"
    
    def _get_timer_summary(self) -> Dict[str, Dict[str, float]]:
        """获取时间器摘要"""
        summary = {}
        
        for key, durations in self._timers.items():
            if durations:
                sorted_durations = sorted(durations)
                count = len(sorted_durations)
                
                summary[key] = {
                    'count': count,
                    'avg': sum(sorted_durations) / count,
                    'min': sorted_durations[0],
                    'max': sorted_durations[-1],
                    'p50': sorted_durations[int(count * 0.5)],
                    'p95': sorted_durations[int(count * 0.95)],
                    'p99': sorted_durations[int(count * 0.99)],
                }
        
        return summary


# 全局指标收集器实例
_global_metrics_collector = MetricsCollector()


def get_metrics_collector() -> MetricsCollector:
    """获取全局指标收集器"""
    return _global_metrics_collector


def increment_counter(name: str, value: float = 1.0, labels: Dict[str, str] = None) -> None:
    """便捷函数：递增计数器"""
    _global_metrics_collector.increment_counter(name, value, labels)


def set_gauge(name: str, value: float, labels: Dict[str, str] = None) -> None:
    """便捷函数：设置仪表值"""
    _global_metrics_collector.set_gauge(name, value, labels)


def record_timer(name: str, duration_ms: float, labels: Dict[str, str] = None) -> None:
    """便捷函数：记录时间"""
    _global_metrics_collector.record_timer(name, duration_ms, labels)


def time_it(name: str, labels: Dict[str, str] = None):
    """便捷函数：时间上下文管理器"""
    return _global_metrics_collector.time_it(name, labels)
