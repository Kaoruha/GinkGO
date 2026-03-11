# Upstream: LogService, GLOG (日志输出层)
# Downstream: MClickBase (继承提供ClickHouse模型基础能力), LEVEL_TYPES, LOG_CATEGORY_TYPES
# Role: 日志表Model类，定义回测日志/组件日志/性能日志的ClickHouse表结构和字段映射

from datetime import datetime
from decimal import Decimal
from typing import Optional

from sqlalchemy import String, Integer, DateTime, Float, DECIMAL
from sqlalchemy.orm import Mapped, mapped_column
from clickhouse_sqlalchemy import engines, types

from ginkgo.data.models.model_clickbase import MClickBase
from ginkgo.enums import LEVEL_TYPES, SOURCE_TYPES


class MBacktestLog(MClickBase):
    """回测日志表 Model

    记录回测任务的业务日志，包括：
    - 策略信号生成
    - 风控触发
    - 订单执行
    - 组合状态变化
    """

    __tablename__ = "ginkgo_logs_backtest"
    __table_args__ = (
        engines.MergeTree(
            order_by=("timestamp", "portfolio_id", "trace_id")
        ),
        {"extend_existing": True},
    )

    # 基础字段
    level: Mapped[str] = mapped_column(String(), default="INFO")
    message: Mapped[str] = mapped_column(String(), default="")
    logger_name: Mapped[str] = mapped_column(String(), default="")

    # 追踪字段
    trace_id: Mapped[Optional[str]] = mapped_column(String(), default=None)
    span_id: Mapped[Optional[str]] = mapped_column(String(), default=None)

    # 业务字段
    portfolio_id: Mapped[Optional[str]] = mapped_column(String(), default=None)
    strategy_id: Mapped[Optional[str]] = mapped_column(String(), default=None)
    event_type: Mapped[Optional[str]] = mapped_column(String(), default=None)
    symbol: Mapped[Optional[str]] = mapped_column(String(), default=None)
    direction: Mapped[Optional[str]] = mapped_column(String(), default=None)
    volume: Mapped[Optional[Decimal]] = mapped_column(DECIMAL(16, 2), default=None)
    price: Mapped[Optional[Decimal]] = mapped_column(DECIMAL(16, 2), default=None)

    # 元数据字段
    hostname: Mapped[Optional[str]] = mapped_column(String(), default=None)
    pid: Mapped[Optional[int]] = mapped_column(Integer, default=None)
    container_id: Mapped[Optional[str]] = mapped_column(String(), default=None)
    task_id: Mapped[Optional[str]] = mapped_column(String(), default=None)
    ingested_at: Mapped[Optional[datetime]] = mapped_column(DateTime, default=None)


class MComponentLog(MClickBase):
    """组件日志表 Model

    记录各核心组件的运行日志，包括：
    - Strategy（策略组件）
    - Analyzer（分析器组件）
    - RiskManagement（风控组件）
    - Sizer（仓位管理组件）
    - Portfolio（组合组件）
    - Engine（引擎组件）
    - DataWorker（数据工作者）
    - ExecutionNode（执行节点）
    """

    __tablename__ = "ginkgo_logs_component"
    __table_args__ = (
        engines.MergeTree(
            order_by=("timestamp", "component_name", "trace_id")
        ),
        {"extend_existing": True},
    )

    # 基础字段
    level: Mapped[str] = mapped_column(String(), default="INFO")
    message: Mapped[str] = mapped_column(String(), default="")
    logger_name: Mapped[str] = mapped_column(String(), default="")

    # 追踪字段
    trace_id: Mapped[Optional[str]] = mapped_column(String(), default=None)
    span_id: Mapped[Optional[str]] = mapped_column(String(), default=None)

    # 组件字段
    component_name: Mapped[Optional[str]] = mapped_column(String(), default=None)
    component_version: Mapped[Optional[str]] = mapped_column(String(), default=None)
    component_instance: Mapped[Optional[str]] = mapped_column(String(), default=None)
    module_name: Mapped[Optional[str]] = mapped_column(String(), default=None)

    # 元数据字段
    hostname: Mapped[Optional[str]] = mapped_column(String(), default=None)
    pid: Mapped[Optional[int]] = mapped_column(Integer, default=None)
    container_id: Mapped[Optional[str]] = mapped_column(String(), default=None)
    task_id: Mapped[Optional[str]] = mapped_column(String(), default=None)
    ingested_at: Mapped[Optional[datetime]] = mapped_column(DateTime, default=None)


class MPerformanceLog(MClickBase):
    """性能日志表 Model

    记录性能监控数据，包括：
    - 方法执行耗时
    - 内存使用情况
    - CPU 使用率
    - 吞吐量指标
    - 自定义性能指标
    """

    __tablename__ = "ginkgo_logs_performance"
    __table_args__ = (
        engines.MergeTree(
            order_by=("timestamp", "trace_id", "function_name")
        ),
        {"extend_existing": True},
    )

    # 基础字段
    level: Mapped[str] = mapped_column(String(), default="INFO")
    message: Mapped[str] = mapped_column(String(), default="")
    logger_name: Mapped[str] = mapped_column(String(), default="")

    # 追踪字段
    trace_id: Mapped[Optional[str]] = mapped_column(String(), default=None)
    span_id: Mapped[Optional[str]] = mapped_column(String(), default=None)

    # 性能字段
    duration_ms: Mapped[Optional[float]] = mapped_column(Float, default=None)
    memory_mb: Mapped[Optional[float]] = mapped_column(Float, default=None)
    cpu_percent: Mapped[Optional[float]] = mapped_column(Float, default=None)
    throughput: Mapped[Optional[float]] = mapped_column(Float, default=None)
    custom_metrics: Mapped[Optional[str]] = mapped_column(String(), default=None)

    # 上下文字段
    function_name: Mapped[Optional[str]] = mapped_column(String(), default=None)
    module_name: Mapped[Optional[str]] = mapped_column(String(), default=None)
    call_site: Mapped[Optional[str]] = mapped_column(String(), default=None)

    # 元数据字段
    hostname: Mapped[Optional[str]] = mapped_column(String(), default=None)
    pid: Mapped[Optional[int]] = mapped_column(Integer, default=None)
    container_id: Mapped[Optional[str]] = mapped_column(String(), default=None)
    task_id: Mapped[Optional[str]] = mapped_column(String(), default=None)
    ingested_at: Mapped[Optional[datetime]] = mapped_column(DateTime, default=None)
