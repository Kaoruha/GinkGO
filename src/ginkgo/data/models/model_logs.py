# Upstream: LogService, GLOG (日志输出层)
# Downstream: MClickBase (继承提供ClickHouse模型基础能力), LEVEL_TYPES, LOG_CATEGORY_TYPES
# Role: 日志表Model类，定义回测日志/组件日志/性能日志的ClickHouse表结构和字段映射

import datetime as dt
from decimal import Decimal
from typing import Optional

from sqlalchemy import String, Integer, DateTime, Float, DECIMAL
from sqlalchemy.orm import Mapped, mapped_column
from clickhouse_sqlalchemy import engines, types
from sqlalchemy.orm import DeclarativeBase

import uuid


class Base(DeclarativeBase):
    pass


class MBacktestLog(Base):
    """回测日志表 Model - 宽表设计支持所有事件类型

    记录回测和实盘任务的业务日志，包括：
    - 信号事件：SIGNALGENERATION（信号生成）
    - 订单生命周期：ORDERSUBMITTED, ORDERACK, ORDERFILLED, ORDERREJECTED, ORDERCANCELACK, ORDEREXPIRED
    - 执行事件：EXECUTIONCONFIRMATION, EXECUTIONREJECTION, EXECUTIONTIMEOUT, EXECUTIONCANCELLATION
    - 组合状态：POSITIONUPDATE, CAPITALUPDATE
    - 风控事件：RISKBREACH, POSITIONLIMITEXCEEDED, DAILYLOSSLIMITEXCEEDED
    - 市场数据：PRICEUPDATE, BARCLOSE, MARKETSTATUS
    - 系统事件：ENGINESTART, ENGINESTOP, TIMEADVANCE
    - 新闻事件：NEWSRECIEVE

    使用宽表设计，根据 event_type 由代码决定读取哪些字段
    """

    __abstract__ = False
    __tablename__ = "ginkgo_logs_backtest"
    __table_args__ = (
        engines.MergeTree(
            order_by=("timestamp", "portfolio_id", "trace_id")
        ),
        {"extend_existing": True},
    )

    # ==================== 主键和基础字段 ====================
    uuid: Mapped[str] = mapped_column(String(), primary_key=True, default=lambda: str(uuid.uuid4().hex))
    timestamp: Mapped[dt.datetime] = mapped_column(DateTime, default=dt.datetime.now)
    source: Mapped[int] = mapped_column(types.Int8, default=-1)

    # ==================== 基础日志字段 ====================
    level: Mapped[str] = mapped_column(String(), default="INFO")
    message: Mapped[str] = mapped_column(String(), default="")
    logger_name: Mapped[str] = mapped_column(String(), default="")

    # ==================== 分布式追踪字段 ====================
    trace_id: Mapped[Optional[str]] = mapped_column(String(), default=None)
    span_id: Mapped[Optional[str]] = mapped_column(String(), default=None)

    # ==================== 事件分类字段 ====================
    event_type: Mapped[Optional[str]] = mapped_column(String(), default=None)  # 事件类型
    event_category: Mapped[Optional[str]] = mapped_column(String(), default=None)  # 事件分类

    # ==================== 任务关联字段 ====================
    portfolio_id: Mapped[Optional[str]] = mapped_column(String(), default=None)
    engine_id: Mapped[Optional[str]] = mapped_column(String(), default=None)
    run_id: Mapped[Optional[str]] = mapped_column(String(), default=None)

    # ==================== 信号事件字段 ====================
    symbol: Mapped[Optional[str]] = mapped_column(String(), default=None)
    direction: Mapped[Optional[str]] = mapped_column(String(), default=None)
    signal_volume: Mapped[Optional[int]] = mapped_column(Integer, default=None)
    signal_reason: Mapped[Optional[str]] = mapped_column(String(), default=None)
    signal_weight: Mapped[Optional[float]] = mapped_column(Float, default=None)
    signal_confidence: Mapped[Optional[float]] = mapped_column(Float, default=None)
    strategy_id: Mapped[Optional[str]] = mapped_column(String(), default=None)

    # ==================== 订单事件字段 ====================
    order_id: Mapped[Optional[str]] = mapped_column(String(), default=None)
    order_type: Mapped[Optional[str]] = mapped_column(String(), default=None)
    limit_price: Mapped[Optional[Decimal]] = mapped_column(DECIMAL(16, 2), default=None)
    frozen_money: Mapped[Optional[Decimal]] = mapped_column(DECIMAL(16, 2), default=None)

    # ==================== 订单确认字段（实盘交易） ====================
    broker_order_id: Mapped[Optional[str]] = mapped_column(String(), default=None)
    ack_message: Mapped[Optional[str]] = mapped_column(String(), default=None)
    order_status: Mapped[Optional[str]] = mapped_column(String(), default=None)

    # ==================== 成交字段 ====================
    transaction_price: Mapped[Optional[Decimal]] = mapped_column(DECIMAL(16, 2), default=None)
    transaction_volume: Mapped[Optional[int]] = mapped_column(Integer, default=None)
    remain_volume: Mapped[Optional[Decimal]] = mapped_column(DECIMAL(20, 4), default=None)
    commission: Mapped[Optional[Decimal]] = mapped_column(DECIMAL(16, 2), default=None)
    slippage: Mapped[Optional[float]] = mapped_column(Float, default=None)
    trade_id: Mapped[Optional[str]] = mapped_column(String(), default=None)

    # ==================== 订单拒绝/取消/过期字段 ====================
    reject_code: Mapped[Optional[str]] = mapped_column(String(), default=None)
    reject_reason: Mapped[Optional[str]] = mapped_column(String(), default=None)
    cancel_reason: Mapped[Optional[str]] = mapped_column(String(), default=None)
    expire_reason: Mapped[Optional[str]] = mapped_column(String(), default=None)
    cancelled_quantity: Mapped[Optional[int]] = mapped_column(Integer, default=None)
    expired_quantity: Mapped[Optional[int]] = mapped_column(Integer, default=None)

    # ==================== 执行确认字段（实盘交易） ====================
    tracking_id: Mapped[Optional[str]] = mapped_column(String(), default=None)
    expected_price: Mapped[Optional[Decimal]] = mapped_column(DECIMAL(16, 2), default=None)
    actual_price: Mapped[Optional[Decimal]] = mapped_column(DECIMAL(16, 2), default=None)
    expected_volume: Mapped[Optional[int]] = mapped_column(Integer, default=None)
    actual_volume: Mapped[Optional[int]] = mapped_column(Integer, default=None)
    price_deviation: Mapped[Optional[float]] = mapped_column(Float, default=None)
    volume_deviation: Mapped[Optional[float]] = mapped_column(Float, default=None)
    delay_seconds: Mapped[Optional[int]] = mapped_column(Integer, default=None)

    # ==================== 持仓字段 ====================
    position_code: Mapped[Optional[str]] = mapped_column(String(), default=None)
    position_volume: Mapped[Optional[int]] = mapped_column(Integer, default=None)
    position_cost: Mapped[Optional[Decimal]] = mapped_column(DECIMAL(20, 4), default=None)
    position_price: Mapped[Optional[Decimal]] = mapped_column(DECIMAL(16, 2), default=None)

    # ==================== 资金字段 ====================
    total_value: Mapped[Optional[Decimal]] = mapped_column(DECIMAL(20, 2), default=None)
    available_cash: Mapped[Optional[Decimal]] = mapped_column(DECIMAL(20, 2), default=None)
    frozen_cash: Mapped[Optional[Decimal]] = mapped_column(DECIMAL(20, 2), default=None)
    net_value: Mapped[Optional[Decimal]] = mapped_column(DECIMAL(20, 2), default=None)
    drawdown: Mapped[Optional[float]] = mapped_column(Float, default=None)
    pnl: Mapped[Optional[Decimal]] = mapped_column(DECIMAL(20, 2), default=None)

    # ==================== 风控字段 ====================
    risk_type: Mapped[Optional[str]] = mapped_column(String(), default=None)
    risk_reason: Mapped[Optional[str]] = mapped_column(String(), default=None)
    risk_limit_value: Mapped[Optional[Decimal]] = mapped_column(DECIMAL(16, 2), default=None)
    risk_actual_value: Mapped[Optional[Decimal]] = mapped_column(DECIMAL(16, 2), default=None)

    # ==================== 市场数据字段 ====================
    bar_datetime: Mapped[Optional[dt.datetime]] = mapped_column(DateTime, default=None)
    bar_open: Mapped[Optional[Decimal]] = mapped_column(DECIMAL(16, 2), default=None)
    bar_high: Mapped[Optional[Decimal]] = mapped_column(DECIMAL(16, 2), default=None)
    bar_low: Mapped[Optional[Decimal]] = mapped_column(DECIMAL(16, 2), default=None)
    bar_close: Mapped[Optional[Decimal]] = mapped_column(DECIMAL(16, 2), default=None)
    bar_volume: Mapped[Optional[int]] = mapped_column(Integer, default=None)
    bar_count: Mapped[Optional[int]] = mapped_column(Integer, default=None)

    # ==================== 引擎状态字段 ====================
    engine_status: Mapped[Optional[str]] = mapped_column(String(), default=None)
    progress: Mapped[Optional[float]] = mapped_column(Float, default=None)
    error_code: Mapped[Optional[str]] = mapped_column(String(), default=None)
    error_message: Mapped[Optional[str]] = mapped_column(String(), default=None)

    # ==================== 市场状态字段 ====================
    market_status: Mapped[Optional[str]] = mapped_column(String(), default=None)
    market_session: Mapped[Optional[str]] = mapped_column(String(), default=None)

    # ==================== 新闻事件字段 ====================
    news_id: Mapped[Optional[str]] = mapped_column(String(), default=None)
    news_source: Mapped[Optional[str]] = mapped_column(String(), default=None)
    news_content: Mapped[Optional[str]] = mapped_column(String(), default=None)

    # ==================== 元数据字段 ====================
    hostname: Mapped[Optional[str]] = mapped_column(String(), default=None)
    pid: Mapped[Optional[int]] = mapped_column(Integer, default=None)
    container_id: Mapped[Optional[str]] = mapped_column(String(), default=None)
    ingested_at: Mapped[Optional[dt.datetime]] = mapped_column(DateTime, default=None)

    # ==================== 业务时间戳 ====================
    business_timestamp: Mapped[Optional[dt.datetime]] = mapped_column(DateTime, default=None)


class MComponentLog(Base):
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

    __abstract__ = False
    __tablename__ = "ginkgo_logs_component"
    __table_args__ = (
        engines.MergeTree(
            order_by=("timestamp", "component_name", "trace_id")
        ),
        {"extend_existing": True},
    )

    # ==================== 主键和基础字段 ====================
    uuid: Mapped[str] = mapped_column(String(), primary_key=True, default=lambda: str(uuid.uuid4().hex))
    timestamp: Mapped[dt.datetime] = mapped_column(DateTime, default=dt.datetime.now)
    source: Mapped[int] = mapped_column(types.Int8, default=-1)
    meta: Mapped[Optional[str]] = mapped_column(String(), default="{}")
    desc: Mapped[Optional[str]] = mapped_column(String(), default="This man is lazy, there is no description.")

    # ==================== 基础日志字段 ====================
    level: Mapped[str] = mapped_column(String(), default="INFO")
    message: Mapped[str] = mapped_column(String(), default="")
    logger_name: Mapped[str] = mapped_column(String(), default="")

    # ==================== 分布式追踪字段 ====================
    trace_id: Mapped[Optional[str]] = mapped_column(String(), default=None)
    span_id: Mapped[Optional[str]] = mapped_column(String(), default=None)

    # ==================== 组件字段 ====================
    component_name: Mapped[Optional[str]] = mapped_column(String(), default=None)
    component_version: Mapped[Optional[str]] = mapped_column(String(), default=None)
    component_instance: Mapped[Optional[str]] = mapped_column(String(), default=None)
    module_name: Mapped[Optional[str]] = mapped_column(String(), default=None)

    # ==================== 元数据字段 ====================
    hostname: Mapped[Optional[str]] = mapped_column(String(), default=None)
    pid: Mapped[Optional[int]] = mapped_column(Integer, default=None)
    container_id: Mapped[Optional[str]] = mapped_column(String(), default=None)
    task_id: Mapped[Optional[str]] = mapped_column(String(), default=None)
    ingested_at: Mapped[Optional[dt.datetime]] = mapped_column(DateTime, default=None)


class MPerformanceLog(Base):
    """性能日志表 Model

    记录性能监控数据，包括：
    - 方法执行耗时
    - 内存使用情况
    - CPU 使用率
    - 吞吐量指标
    - 自定义性能指标
    """

    __abstract__ = False
    __tablename__ = "ginkgo_logs_performance"
    __table_args__ = (
        engines.MergeTree(
            order_by=("timestamp", "trace_id", "function_name")
        ),
        {"extend_existing": True},
    )

    # ==================== 主键和基础字段 ====================
    uuid: Mapped[str] = mapped_column(String(), primary_key=True, default=lambda: str(uuid.uuid4().hex))
    timestamp: Mapped[dt.datetime] = mapped_column(DateTime, default=dt.datetime.now)

    # ==================== 基础日志字段 ====================
    level: Mapped[str] = mapped_column(String(), default="INFO")
    message: Mapped[str] = mapped_column(String(), default="")
    logger_name: Mapped[str] = mapped_column(String(), default="")

    # ==================== 分布式追踪字段 ====================
    trace_id: Mapped[Optional[str]] = mapped_column(String(), default=None)
    span_id: Mapped[Optional[str]] = mapped_column(String(), default=None)

    # ==================== 性能字段 ====================
    duration_ms: Mapped[Optional[float]] = mapped_column(Float, default=None)
    memory_mb: Mapped[Optional[float]] = mapped_column(Float, default=None)
    cpu_percent: Mapped[Optional[float]] = mapped_column(Float, default=None)
    throughput: Mapped[Optional[float]] = mapped_column(Float, default=None)
    custom_metrics: Mapped[Optional[str]] = mapped_column(String(), default=None)

    # ==================== 上下文字段 ====================
    function_name: Mapped[Optional[str]] = mapped_column(String(), default=None)
    module_name: Mapped[Optional[str]] = mapped_column(String(), default=None)
    call_site: Mapped[Optional[str]] = mapped_column(String(), default=None)

    # ==================== 元数据字段 ====================
    hostname: Mapped[Optional[str]] = mapped_column(String(), default=None)
    pid: Mapped[Optional[int]] = mapped_column(Integer, default=None)
    container_id: Mapped[Optional[str]] = mapped_column(String(), default=None)
    task_id: Mapped[Optional[str]] = mapped_column(String(), default=None)
    ingested_at: Mapped[Optional[dt.datetime]] = mapped_column(DateTime, default=None)
