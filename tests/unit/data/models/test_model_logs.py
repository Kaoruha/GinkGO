# Upstream: MBacktestLog/MComponentLog/MPerformanceLog (日志表Model类)
# Downstream: pytest (测试框架), clickhouse-sqlalchemy (数据库)
# Role: 日志Model类的单元测试，验证字段定义、继承关系和基础功能

import pytest
import datetime
from decimal import Decimal

from ginkgo.data.models.model_logs import MBacktestLog, MComponentLog, MPerformanceLog
from ginkgo.enums import LEVEL_TYPES, SOURCE_TYPES


class TestMBacktestLog:
    """MBacktestLog 回测日志表 Model 类测试"""

    def test_model_inheritance(self):
        """测试 Model 继承自 MClickBase"""
        # 验证基础字段存在
        log = MBacktestLog()
        assert hasattr(log, "uuid")
        assert hasattr(log, "timestamp")
        assert hasattr(log, "meta")
        assert hasattr(log, "source")

    def test_table_name(self):
        """测试表名定义"""
        assert MBacktestLog.__tablename__ == "ginkgo_logs_backtest"

    def test_basic_fields(self):
        """测试基础字段定义"""
        log = MBacktestLog()
        # 注意：mapped_column 默认值在数据库层面应用，Python对象层面为 None
        # 这与 MBar 等其他 Model 的行为一致
        assert log.level is None or log.level == "INFO"  # 允许两种情况
        assert log.message is None or log.message == ""
        assert log.logger_name is None or log.logger_name == ""

    def test_tracing_fields(self):
        """测试追踪字段定义"""
        log = MBacktestLog()
        assert log.trace_id is None
        assert log.span_id is None

        # 测试字段赋值
        log.trace_id = "test-trace-123"
        log.span_id = "test-span-456"
        assert log.trace_id == "test-trace-123"
        assert log.span_id == "test-span-456"

    def test_business_fields(self):
        """测试业务字段定义"""
        log = MBacktestLog()
        assert log.portfolio_id is None
        assert log.strategy_id is None
        assert log.event_type is None
        assert log.symbol is None
        assert log.direction is None

        # 测试字段赋值
        log.portfolio_id = "portfolio-001"
        log.strategy_id = "strategy-ma"
        log.event_type = "SIGNALGENERATION"
        log.symbol = "000001.SZ"
        log.direction = "LONG"
        assert log.portfolio_id == "portfolio-001"
        assert log.strategy_id == "strategy-ma"

    def test_metadata_fields(self):
        """测试元数据字段定义"""
        log = MBacktestLog()
        assert log.hostname is None
        assert log.pid is None
        assert log.container_id is None
        assert log.task_id is None
        assert log.ingested_at is None


class TestMComponentLog:
    """MComponentLog 组件日志表 Model 类测试"""

    def test_table_name(self):
        """测试表名定义"""
        assert MComponentLog.__tablename__ == "ginkgo_logs_component"

    def test_component_fields(self):
        """测试组件字段定义"""
        log = MComponentLog()
        assert log.component_name is None
        assert log.component_version is None
        assert log.component_instance is None
        assert log.module_name is None

        # 测试字段赋值
        log.component_name = "Strategy"
        log.component_version = "1.0.0"
        log.component_instance = "strategy-abc"
        log.module_name = "ginkgo.core.strategies"
        assert log.component_name == "Strategy"


class TestMPerformanceLog:
    """MPerformanceLog 性能日志表 Model 类测试"""

    def test_table_name(self):
        """测试表名定义"""
        assert MPerformanceLog.__tablename__ == "ginkgo_logs_performance"

    def test_performance_fields(self):
        """测试性能字段定义"""
        log = MPerformanceLog()
        assert log.duration_ms is None
        assert log.memory_mb is None
        assert log.cpu_percent is None
        assert log.throughput is None
        assert log.custom_metrics is None

        # 测试字段赋值
        log.duration_ms = 123.45
        log.memory_mb = 256.78
        log.cpu_percent = 45.6
        log.throughput = 1000.0
        log.custom_metrics = '{"cache_hit": 0.95}'
        assert log.duration_ms == 123.45

    def test_context_fields(self):
        """测试上下文字段定义"""
        log = MPerformanceLog()
        assert log.function_name is None
        assert log.module_name is None
        assert log.call_site is None

        # 测试字段赋值
        log.function_name = "calculate_signals"
        log.module_name = "ginkgo.core.strategies"
        log.call_site = "model_ma.py:45"
        assert log.function_name == "calculate_signals"
