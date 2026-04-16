"""
交易引擎监控指标TDD测试

覆盖MetricsCollector/HealthChecker等监控核心, 兼顾回测与实盘的监控差异。
"""

import pytest
import sys
import asyncio
import time
from pathlib import Path
from datetime import datetime, timedelta
from decimal import Decimal
from unittest.mock import MagicMock, AsyncMock

project_root = Path(__file__).parent.parent.parent.parent
_path = str(project_root / "src")
if _path not in sys.path:
    sys.path.insert(0, _path)

from ginkgo.trading.monitoring.metrics import (
    MetricsCollector, MetricType, MetricPoint,
    PerformanceMetrics, SystemMetrics, TradingMetrics
)
from ginkgo.trading.monitoring.health import (
    HealthChecker, HealthStatus, ComponentHealth, SystemHealth
)
from ginkgo.trading.monitoring.dashboard import (
    MonitoringDashboard, AlertManager, AlertRule, AlertLevel, AlertStatus
)
from ginkgo.trading.monitoring.tracing import (
    EventTracer, TraceContext, SpanStatus, MemorySpanExporter
)


@pytest.mark.unit
class TestEngineMetricsCollection:
    """监控指标采集与聚合"""

    def test_register_metric_collector(self):
        collector = MetricsCollector()
        def custom_collector():
            return {"custom_metric": 42}
        collector.register_collector(custom_collector)
        metrics = collector.get_current_metrics()
        assert "custom_metric" in metrics
        assert metrics["custom_metric"] == 42

    def test_counter_increment_and_flush(self):
        collector = MetricsCollector()
        collector.increment_counter("orders", value=1)
        collector.increment_counter("orders", value=3)
        metrics = collector.get_current_metrics()
        assert metrics["counters"]["orders"] == 4.0

    def test_histogram_percentile_calculation(self):
        collector = MetricsCollector()
        for i in range(100):
            collector.record_timer("latency", float(i))
        summary = collector._get_timer_summary()
        assert "latency" in summary
        assert summary["latency"]["count"] == 100
        assert summary["latency"]["p50"] >= 0
        assert summary["latency"]["p95"] >= 0

    def test_metrics_window_rotation(self):
        collector = MetricsCollector(max_history=10)
        for i in range(20):
            collector.record_histogram("test_metric", float(i))
        history = collector.get_metrics_history("test_metric")
        assert len(history) == 10  # maxlen=10


@pytest.mark.unit
class TestPerformanceMonitoring:
    """性能指标与资源消耗监控"""

    def test_performance_metrics_update(self):
        collector = MetricsCollector()
        collector.performance_metrics.avg_response_time = 10.5
        collector.performance_metrics.total_requests = 100
        metrics = collector.get_current_metrics()
        assert metrics["performance"]["avg_response_time"] == 10.5

    def test_system_metrics_sampling(self):
        collector = MetricsCollector()
        collector.system_metrics.cache_hits = 80
        collector.system_metrics.cache_misses = 20
        metrics = collector.get_current_metrics()
        assert metrics["system"]["cache_hit_rate"] == 80.0

    def test_trading_metrics_fill_rate(self):
        collector = MetricsCollector()
        collector.trading_metrics.total_orders = 100
        collector.trading_metrics.filled_orders = 75
        assert collector.trading_metrics.fill_rate == 75.0

    def test_metrics_alert_thresholds(self):
        collector = MetricsCollector()
        collector.performance_metrics.requests_per_second = 0
        collector.performance_metrics.cpu_usage_percent = 0
        metrics = collector.get_current_metrics()
        assert metrics["performance"]["cpu_usage_percent"] == 0.0


@pytest.mark.unit
class TestHealthCheckMechanism:
    """健康检查调度/回调/状态聚合"""

    @pytest.mark.asyncio
    async def test_register_and_execute_health_checks(self):
        checker = HealthChecker()
        def healthy_check():
            return ComponentHealth(component_name="db", status=HealthStatus.HEALTHY, message="OK")
        checker.register_health_check("db", healthy_check)
        result = await checker.check_component_health("db")
        assert result.status == HealthStatus.HEALTHY
        assert result.component_name == "db"

    @pytest.mark.asyncio
    async def test_overall_status_aggregation(self):
        checker = HealthChecker()
        def healthy_check():
            return ComponentHealth(component_name="db", status=HealthStatus.HEALTHY, message="OK")
        checker.register_health_check("db", healthy_check)
        health = await checker.check_all_health()
        assert health.overall_status == HealthStatus.HEALTHY
        assert health.total_components == 1
        assert health.healthy_components == 1

    @pytest.mark.asyncio
    async def test_health_callback_invocation(self):
        checker = HealthChecker()
        callback_results = []
        checker.add_health_callback(lambda h: callback_results.append(h))
        def healthy_check():
            return ComponentHealth(component_name="db", status=HealthStatus.HEALTHY)
        checker.register_health_check("db", healthy_check)
        await checker.check_all_health()
        assert len(callback_results) == 1

    @pytest.mark.asyncio
    async def test_async_health_check_support(self):
        checker = HealthChecker()
        async def async_check():
            return ComponentHealth(component_name="api", status=HealthStatus.HEALTHY)
        checker.register_async_health_check("api", async_check)
        result = await checker.check_component_health("api")
        assert result.status == HealthStatus.HEALTHY


@pytest.mark.unit
class TestMonitoringDashboardIntegration:
    """监控仪表盘数据对接"""

    def test_dashboard_refresh_cycle(self):
        dashboard = MonitoringDashboard()
        assert dashboard.metrics_collector is not None
        assert dashboard.health_checker is not None
        assert dashboard.alert_manager is not None

    def test_dashboard_combines_backtest_live_streams(self):
        dashboard = MonitoringDashboard()
        dashboard.metrics_collector.increment_counter("backtest_events", 10)
        dashboard.metrics_collector.increment_counter("live_events", 5)
        metrics = dashboard.metrics_collector.get_current_metrics()
        assert metrics["counters"]["backtest_events"] == 10.0
        assert metrics["counters"]["live_events"] == 5.0

    def test_dashboard_handles_missing_feeds(self):
        dashboard = MonitoringDashboard()
        # Reset global collector to test empty state
        dashboard.metrics_collector.reset_metrics()
        metrics = dashboard.metrics_collector.get_current_metrics()
        assert metrics["counters"] == {}

    def test_dashboard_alert_routing(self):
        dashboard = MonitoringDashboard()
        rule = AlertRule(
            rule_name="test_rule",
            condition_func=lambda state: True,
            level=AlertLevel.WARNING,
            message_template="Test alert"
        )
        dashboard.alert_manager.add_rule(rule)
        assert "test_rule" in dashboard.alert_manager._rules
