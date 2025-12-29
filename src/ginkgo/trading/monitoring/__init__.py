# Upstream: Backtest Engines, Portfolio Manager
# Downstream: Data Layer, Event System
# Role: 监控模块公共接口，导出Dashboard仪表板、Health健康检查、Metrics指标监控、Tracing链路追踪等系统监控组件






"""
T5架构监控可观测性模块

提供统一的监控、指标收集和可观测性功能：
- 性能指标收集
- 健康状态监控
- 事件追踪
- 系统可观测性
"""

from .metrics import (
    MetricsCollector,
    PerformanceMetrics,
    SystemMetrics,
    TradingMetrics,
    get_metrics_collector,
    increment_counter,
    set_gauge,
    record_timer,
    time_it
)

from .health import (
    HealthChecker,
    HealthStatus,
    ComponentHealth,
    SystemHealth,
    get_health_checker,
    register_health_check,
    check_system_health
)

from .tracing import (
    EventTracer,
    TraceContext,
    TraceSpan,
    SpanKind,
    get_tracer,
    trace,
    traced,
    start_trace,
    finish_span,
    get_current_context
)

from .dashboard import (
    MonitoringDashboard,
    AlertManager,
    get_dashboard,
    start_monitoring,
    stop_monitoring,
    get_dashboard_data
)

__all__ = [
    # 指标收集
    'MetricsCollector',
    'PerformanceMetrics', 
    'SystemMetrics',
    'TradingMetrics',
    'get_metrics_collector',
    'increment_counter',
    'set_gauge', 
    'record_timer',
    'time_it',
    
    # 健康监控
    'HealthChecker',
    'HealthStatus',
    'ComponentHealth',
    'SystemHealth',
    'get_health_checker',
    'register_health_check',
    'check_system_health',
    
    # 事件追踪
    'EventTracer',
    'TraceContext',
    'TraceSpan',
    'SpanKind',
    'get_tracer',
    'trace',
    'traced',
    'start_trace',
    'finish_span',
    'get_current_context',
    
    # 监控面板
    'MonitoringDashboard',
    'AlertManager',
    'get_dashboard',
    'start_monitoring',
    'stop_monitoring',
    'get_dashboard_data'
]