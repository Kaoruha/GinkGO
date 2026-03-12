# Data Model: 分布式日志系统优化重构

**Feature**: 011-distributed-logging
**Date**: 2026-03-10
**Status**: Complete

## Overview

本文档定义分布式日志系统的数据模型，包括 ClickHouse 表结构、SQLAlchemy Model 类和枚举类型定义。

---

## 1. 枚举类型定义

### 1.1 LEVEL_TYPES（日志级别枚举）

**文件位置**: `src/ginkgo/enums.py`

```python
class LEVEL_TYPES(EnumBase):
    """日志级别枚举"""
    VOID = -1
    DEBUG = 0
    INFO = 1
    WARNING = 2
    ERROR = 3
    CRITICAL = 4
```

**用途**: 标识日志严重程度，用于日志过滤和告警触发

**存储格式**: Int8（数据库存储整数，查询时转换为可读名称）

---

### 1.2 LOG_CATEGORY_TYPES（日志类别枚举）

**文件位置**: `src/ginkgo/enums.py`

```python
class LOG_CATEGORY_TYPES(EnumBase):
    """日志类别枚举"""
    VOID = -1
    BACKTEST = 0      # 回测业务日志
    COMPONENT = 1     # 组件运行日志
    PERFORMANCE = 2   # 性能监控日志
```

**用途**: 区分日志类型，用于 Vector 路由到不同 ClickHouse 表

**存储格式**: Int8

---

## 2. ClickHouse 表结构

### 2.1 ginkgo_logs_backtest（回测日志表）

**用途**: 记录回测任务的业务日志（策略信号、风控触发、订单执行等）

**SQLAlchemy Model**: `MBacktestLog`

**建表 SQL**:
```sql
CREATE TABLE IF NOT EXISTS ginkgo.ginkgo_logs_backtest ON CLUSTER '{cluster}' (
    uuid String DEFAULT generateUUIDv4(),
    timestamp DateTime,
    level String DEFAULT 'INFO',
    message String DEFAULT '',
    logger_name String DEFAULT '',

    -- 追踪字段
    trace_id String DEFAULT '',
    span_id String DEFAULT '',

    -- 业务字段
    portfolio_id String DEFAULT '',
    strategy_id String DEFAULT '',
    event_type String DEFAULT '',
    symbol String DEFAULT '',
    direction String DEFAULT '',
    volume Decimal(16, 2) DEFAULT 0,
    price Decimal(16, 2) DEFAULT 0,

    -- 元数据字段
    hostname String DEFAULT '',
    pid UInt32 DEFAULT 0,
    container_id String DEFAULT '',
    task_id String DEFAULT '',
    ingested_at DateTime DEFAULT now(),

    -- 基础字段（MClickBase）
    meta String DEFAULT '{}',
    desc String DEFAULT 'This man is lazy, there is no description.',
    source Int8 DEFAULT -1
)
ENGINE = MergeTree()
PARTITION BY (toDate(timestamp), portfolio_id)
ORDER BY (timestamp, portfolio_id, trace_id)
TTL timestamp + INTERVAL 180 DAY
SETTINGS index_granularity = 8192;
```

**分区策略**: `(toDate(timestamp), portfolio_id)` - 按日期和组合 ID 复合分区

**排序键**: `(timestamp, portfolio_id, trace_id)` - 优化时序查询和关联查询

**TTL**: 180 天（可通过 GCONF.LOGGING_TTL_BACKTEST 动态调整）

**索引字段**: timestamp, trace_id, portfolio_id, strategy_id, level

---

### 2.2 ginkgo_logs_component（组件日志表）

**用途**: 记录各核心组件的运行日志（Strategy、Analyzer、RiskManagement、Sizer、Portfolio、Engine、DataWorker、ExecutionNode）

**SQLAlchemy Model**: `MComponentLog`

**建表 SQL**:
```sql
CREATE TABLE IF NOT EXISTS ginkgo.ginkgo_logs_component ON CLUSTER '{cluster}' (
    uuid String DEFAULT generateUUIDv4(),
    timestamp DateTime,
    level String DEFAULT 'INFO',
    message String DEFAULT '',
    logger_name String DEFAULT '',

    -- 追踪字段
    trace_id String DEFAULT '',
    span_id String DEFAULT '',

    -- 组件字段
    component_name String DEFAULT '',
    component_version String DEFAULT '',
    component_instance String DEFAULT '',
    module_name String DEFAULT '',

    -- 元数据字段
    hostname String DEFAULT '',
    pid UInt32 DEFAULT 0,
    container_id String DEFAULT '',
    task_id String DEFAULT '',
    ingested_at DateTime DEFAULT now(),

    -- 基础字段（MClickBase）
    meta String DEFAULT '{}',
    desc String DEFAULT 'This man is lazy, there is no description.',
    source Int8 DEFAULT -1
)
ENGINE = MergeTree()
PARTITION BY (toDate(timestamp), component_name)
ORDER BY (timestamp, component_name, trace_id)
TTL timestamp + INTERVAL 90 DAY
SETTINGS index_granularity = 8192;
```

**分区策略**: `(toDate(timestamp), component_name)` - 按日期和组件名复合分区

**排序键**: `(timestamp, component_name, trace_id)` - 优化组件日志查询

**TTL**: 90 天（可通过 GCONF.LOGGING_TTL_COMPONENT 动态调整）

**索引字段**: timestamp, trace_id, component_name, level, hostname

---

### 2.3 ginkgo_logs_performance（性能日志表）

**用途**: 记录性能监控数据（方法执行耗时、资源使用、吞吐量等）

**SQLAlchemy Model**: `MPerformanceLog`

**建表 SQL**:
```sql
CREATE TABLE IF NOT EXISTS ginkgo.ginkgo_logs_performance ON CLUSTER '{cluster}' (
    uuid String DEFAULT generateUUIDv4(),
    timestamp DateTime,
    level String DEFAULT 'INFO',
    message String DEFAULT '',
    logger_name String DEFAULT '',

    -- 追踪字段
    trace_id String DEFAULT '',
    span_id String DEFAULT '',

    -- 性能字段
    duration_ms Float64 DEFAULT 0,
    memory_mb Float64 DEFAULT 0,
    cpu_percent Float64 DEFAULT 0,
    throughput Float64 DEFAULT 0,
    custom_metrics String DEFAULT '{}',

    -- 上下文字段
    function_name String DEFAULT '',
    module_name String DEFAULT '',
    call_site String DEFAULT '',

    -- 元数据字段
    hostname String DEFAULT '',
    pid UInt32 DEFAULT 0,
    container_id String DEFAULT '',
    task_id String DEFAULT '',
    ingested_at DateTime DEFAULT now(),

    -- 基础字段（MClickBase）
    meta String DEFAULT '{}',
    desc String DEFAULT 'This man is lazy, there is no description.',
    source Int8 DEFAULT -1
)
ENGINE = MergeTree()
PARTITION BY (toDate(timestamp), level)
ORDER BY (timestamp, trace_id, function_name)
TTL timestamp + INTERVAL 30 DAY
SETTINGS index_granularity = 8192;
```

**分区策略**: `(toDate(timestamp), level)` - 按日期和日志级别复合分区

**排序键**: `(timestamp, trace_id, function_name)` - 优化性能日志查询

**TTL**: 30 天（可通过 GCONF.LOGGING_TTL_PERFORMANCE 动态调整）

**索引字段**: timestamp, trace_id, function_name, duration_ms, level

---

## 3. SQLAlchemy Model 类

### 3.1 MBacktestLog（回测日志 Model）

**文件位置**: `src/ginkgo/data/models/model_logs.py`

```python
# Upstream: LogService (日志查询服务)、GLOG (日志输出)
# Downstream: MClickBase (继承提供ClickHouse模型基础能力)、LEVEL_TYPES (枚举类型)
# Role: 回测日志表Model类，定义回测业务日志的字段结构和ClickHouse映射

import datetime
from decimal import Decimal
from typing import Optional
from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column
from clickhouse_sqlalchemy import engines

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
            partition_by="(toDate(timestamp), portfolio_id)",
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
    volume: Mapped[Optional[Decimal]] = mapped_column(Decimal(16, 2), default=None)
    price: Mapped[Optional[Decimal]] = mapped_column(Decimal(16, 2), default=None)

    # 元数据字段
    hostname: Mapped[Optional[str]] = mapped_column(String(), default=None)
    pid: Mapped[Optional[int]] = mapped_column(type_=Integer, default=None)
    container_id: Mapped[Optional[str]] = mapped_column(String(), default=None)
    task_id: Mapped[Optional[str]] = mapped_column(String(), default=None)
    ingested_at: Mapped[Optional[datetime.datetime]] = mapped_column(
        type_=DateTime, default=None
    )
```

**字段说明**:

| 字段名 | 类型 | 说明 | 示例值 |
|--------|------|------|--------|
| uuid | String | 主键，自动生成 | "a1b2c3d4..." |
| timestamp | DateTime | 日志时间戳 | 2026-03-10 12:00:00 |
| level | String | 日志级别 | "INFO", "ERROR" |
| message | String | 日志消息 | "信号生成成功" |
| logger_name | String | 日志记录器名称 | "ginkgo.strategy" |
| trace_id | String | 追踪 ID | "trace-abc-123" |
| span_id | String | 跨度 ID | "span-xyz-789" |
| portfolio_id | String | 组合 ID | "portfolio-001" |
| strategy_id | String | 策略 ID | "strategy-ma" |
| event_type | String | 事件类型 | "SIGNALGENERATION" |
| symbol | String | 股票代码 | "000001.SZ" |
| direction | String | 方向 | "LONG", "SHORT" |
| volume | Decimal | 数量 | 100.00 |
| price | Decimal | 价格 | 10.50 |
| hostname | String | 主机名 | "ginkgo-worker-1" |
| pid | Int32 | 进程 ID | 12345 |
| container_id | String | 容器 ID | "container-xyz" |
| task_id | String | 任务 ID | "backtest-001" |
| ingested_at | DateTime | 采集时间戳 | 2026-03-10 12:00:02 |

---

### 3.2 MComponentLog（组件日志 Model）

**文件位置**: `src/ginkgo/data/models/model_logs.py`

```python
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
            partition_by="(toDate(timestamp), component_name)",
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
    pid: Mapped[Optional[int]] = mapped_column(type_=Integer, default=None)
    container_id: Mapped[Optional[str]] = mapped_column(String(), default=None)
    task_id: Mapped[Optional[str]] = mapped_column(String(), default=None)
    ingested_at: Mapped[Optional[datetime.datetime]] = mapped_column(
        type_=DateTime, default=None
    )
```

**字段说明**:

| 字段名 | 类型 | 说明 | 示例值 |
|--------|------|------|--------|
| component_name | String | 组件名称 | "Strategy", "Analyzer" |
| component_version | String | 组件版本 | "1.0.0" |
| component_instance | String | 组件实例 ID | "strategy-abc" |
| module_name | String | 模块名称 | "ginkgo.core.strategies" |

---

### 3.3 MPerformanceLog（性能日志 Model）

**文件位置**: `src/ginkgo/data/models/model_logs.py`

```python
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
            partition_by="(toDate(timestamp), level)",
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
    duration_ms: Mapped[Optional[float]] = mapped_column(type_=Float, default=None)
    memory_mb: Mapped[Optional[float]] = mapped_column(type_=Float, default=None)
    cpu_percent: Mapped[Optional[float]] = mapped_column(type_=Float, default=None)
    throughput: Mapped[Optional[float]] = mapped_column(type_=Float, default=None)
    custom_metrics: Mapped[Optional[str]] = mapped_column(String(), default=None)

    # 上下文字段
    function_name: Mapped[Optional[str]] = mapped_column(String(), default=None)
    module_name: Mapped[Optional[str]] = mapped_column(String(), default=None)
    call_site: Mapped[Optional[str]] = mapped_column(String(), default=None)

    # 元数据字段
    hostname: Mapped[Optional[str]] = mapped_column(String(), default=None)
    pid: Mapped[Optional[int]] = mapped_column(type_=Integer, default=None)
    container_id: Mapped[Optional[str]] = mapped_column(String(), default=None)
    task_id: Mapped[Optional[str]] = mapped_column(String(), default=None)
    ingested_at: Mapped[Optional[datetime.datetime]] = mapped_column(
        type_=DateTime, default=None
    )
```

**字段说明**:

| 字段名 | 类型 | 说明 | 示例值 |
|--------|------|------|--------|
| duration_ms | Float64 | 执行耗时（毫秒） | 123.45 |
| memory_mb | Float64 | 内存使用（MB） | 256.78 |
| cpu_percent | Float64 | CPU 使用率（%） | 45.6 |
| throughput | Float64 | 吞吐量（条/秒） | 1000.0 |
| custom_metrics | String | 自定义指标（JSON） | "{\"cache_hit\": 0.95}" |
| function_name | String | 函数名称 | "calculate_signals" |
| module_name | String | 模块名称 | "ginkgo.core.strategies" |
| call_site | String | 调用位置 | "model_ma.py:45" |

---

## 4. 数据模型关系图

```
┌─────────────────────────────────────────────────────────────┐
│                    日志输出层 (GLOG)                          │
│  输出 JSON 日志，包含 log_category 字段用于路由              │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                    Vector 采集层                             │
│  根据 log_category 路由到不同的 sink                         │
└─────────────────────────────────────────────────────────────┘
                              │
          ┌───────────────────┼───────────────────┐
          ▼                   ▼                   ▼
┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐
│ ginkgo_logs_    │  │ ginkgo_logs_    │  │ ginkgo_logs_    │
│ backtest        │  │ component       │  │ performance     │
│                 │  │                 │  │                 │
│ • portfolio_id  │  │ • component_    │  │ • duration_ms   │
│ • strategy_id   │  │   name          │  │ • memory_mb     │
│ • event_type    │  │ • module_name   │  │ • cpu_percent   │
│ • symbol        │  │                 │  │ • throughput    │
│ • direction     │  │                 │  │                 │
│ TTL: 180天      │  │ TTL: 90天       │  │ TTL: 30天       │
└─────────────────┘  └─────────────────┘  └─────────────────┘
          │                   │                   │
          └───────────────────┼───────────────────┘
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                    LogService                                │
│  • query_by_trace_id() - 跨表查询                            │
│  • query_backtest_logs() - 回测日志                          │
│  • query_component_logs() - 组件日志                         │
│  • query_performance_logs() - 性能日志                       │
│  • 关联查询: 与回测结果表 JOIN                                │
└─────────────────────────────────────────────────────────────┘
```

---

## 5. 配置参数

### 5.1 GCONF 配置项

| 配置项 | 类型 | 默认值 | 说明 |
|--------|------|--------|------|
| LOGGING_MODE | str | "auto" | 日志模式：container/local/auto |
| LOGGING_JSON_OUTPUT | bool | True | 是否输出 JSON 格式 |
| LOGGING_TTL_BACKTEST | int | 180 | 回测日志 TTL（天） |
| LOGGING_TTL_COMPONENT | int | 90 | 组件日志 TTL（天） |
| LOGGING_TTL_PERFORMANCE | int | 30 | 性能日志 TTL（天） |
| LOGGING_SAMPLING_RATE | float | 0.1 | DEBUG 日志采样率 |
| LOGGING_FILE_PATH | str | "/var/log/ginkgo" | 日志文件路径 |
| LOGGING_LEVEL_MODULES | dict | {} | 模块级别配置 |

---

## 6. 数据迁移

### 6.1 初始化脚本

创建日志表的迁移脚本：

```python
# scripts/init_logging_tables.py
from ginkgo.data.models.model_logs import (
    MBacktestLog,
    MComponentLog,
    MPerformanceLog
)
from ginkgo.data.interfaces import clickhouse_interface

def init_logging_tables():
    """初始化日志表"""
    engine = clickhouse_interface.get_engine()

    # 创建表
    MBacktestLog.metadata.create_all(engine)
    MComponentLog.metadata.create_all(engine)
    MPerformanceLog.metadata.create_all(engine)

    print("日志表初始化完成")
```

---

## 总结

本文档定义了分布式日志系统的完整数据模型：

1. **枚举类型**: LEVEL_TYPES、LOG_CATEGORY_TYPES
2. **ClickHouse 表**: ginkgo_logs_backtest、ginkgo_logs_component、ginkgo_logs_performance
3. **SQLAlchemy Model**: MBacktestLog、MComponentLog、MPerformanceLog
4. **配置参数**: GCONF 日志相关配置项

所有 Model 类继承自 MClickBase，保持与项目现有代码的一致性。
