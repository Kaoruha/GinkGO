# Data Model: 容器化分布式日志系统 (Loki Only)

**Feature**: 012-distributed-logging
**Date**: 2026-02-26

## 概述

Loki Only 架构下，不需要定义数据库表结构。日志以 JSON 格式输出到 stdout/stderr，由 Promtail 采集并添加 Loki 标签。

## structlog Event Dict 结构

### 完整结构

```python
{
    # ========== ECS 标准字段 ==========
    "@timestamp": "2026-02-26T10:30:00.123456Z",
    "log": {
        "level": "info",
        "logger": "ginkgo.engine"
    },
    "message": "Engine started",

    # ========== 进程/主机信息 ==========
    "process": {
        "pid": 12345,
        "name": "ginkgo"
    },
    "host": {
        "hostname": "ginkgo-pod-abc123"
    },

    # ========== 容器元数据 ==========
    "container": {
        "id": "docker://abc123def456..."
    },
    "kubernetes": {
        "pod": {
            "name": "ginkgo-worker-0"
        },
        "namespace": "production"
    },

    # ========== 追踪上下文 ==========
    "trace": {
        "id": "trace-123"
    },
    "span": {
        "id": "span-456"
    },

    # ========== Ginkgo 业务字段 ==========
    "ginkgo": {
        "log_category": "system",      # system / backtest
        "strategy_id": "550e8400-...",
        "portfolio_id": "550e8400-...",
        "event_type": "ENGINE_STARTED",
        "symbol": "000001.SZ",
        "direction": "LONG"
    },

    # ========== 异常信息（如果有）==========
    "error": {
        "type": "ValueError",
        "message": "Invalid parameter",
        "stack_trace": "..."
    }
}
```

## Loki 标签设计

Promtail 会将 JSON 字段转换为 Loki 标签，用于快速过滤查询。

### 自动标签（Promtail 提取）

| 标签 | 来源 | 示例值 |
|------|------|--------|
| `container_id` | container.id | docker://abc123... |
| `pod_name` | kubernetes.pod.name | ginkgo-worker-0 |
| `namespace` | kubernetes.namespace | production |
| `hostname` | host.hostname | ginkgo-pod-abc123 |
| `logger_name` | log.logger | ginkgo.engine |
| `log_category` | ginkgo.log_category | system / backtest |
| `level` | log.level | info / error |
| `trace_id` | trace.id | trace-123 |

### 标签查询示例 (LogQL)

```logql
# 按日志类别过滤
{log_category="backtest"}

# 按日志级别过滤
{level="error"}

# 按容器过滤
{container_id="docker://abc123"}

# 按 trace_id 过滤
{trace_id="trace-123"}

# 组合查询
{log_category="backtest", level="error"} |= "database"

# 时间范围
{level="error"} |= "" [1h]
```

## 字段说明

### 必填字段

| 字段路径 | 类型 | 说明 |
|----------|------|------|
| @timestamp | ISO8601 string | 日志时间戳 |
| log.level | string | 小写级别 (debug/info/warning/error/critical) |
| log.logger | string | Logger 名称 |
| message | string | 日志消息 |
| process.pid | uint32 | 进程 ID |
| host.hostname | string | 主机名 |
| ginkgo.log_category | enum | system / backtest |

### 可选字段

| 字段路径 | 类型 | 说明 |
|----------|------|------|
| container.id | string | 容器 ID（容器环境） |
| kubernetes.pod.name | string | Pod 名称（K8s 环境） |
| kubernetes.namespace | string | Namespace（K8s 环境） |
| trace.id | string | 追踪 ID（启用追踪时） |
| span.id | string | Span ID（启用追踪时） |
| ginkgo.strategy_id | UUID | 策略 ID |
| ginkgo.portfolio_id | UUID | 组合 ID |
| ginkgo.event_type | string | T5 事件类型 |
| ginkgo.symbol | string | 股票代码 |
| ginkgo.direction | string | 交易方向 |

## 枚举类型

### LogCategory

```python
class LogCategory(str, Enum):
    """日志类别枚举"""
    SYSTEM = "system"      # 系统级日志
    BACKTEST = "backtest"  # 业务级日志（回测）
```

### LogLevel

```python
class LogLevel(str, Enum):
    """日志级别枚举（ECS 标准）"""
    DEBUG = "debug"
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"
```

## 数据流

```
应用代码
   │
   ▼
GLOG.INFO("message")
   │
   ▼
structlog Event Dict
   │
   ├─► stdout/stderr (JSON) ──► Promtail ──► Loki (标签索引 + 存储)
   │
   └─► (未来扩展: ClickHouse)
```

## 输出示例

### 容器环境（JSON）

```json
{"@timestamp":"2026-02-26T10:30:00.123456Z","log":{"level":"info","logger":"ginkgo.engine"},"message":"Engine started","process":{"pid":12345},"host":{"hostname":"ginkgo-pod-abc123"},"container":{"id":"docker://abc123"},"kubernetes":{"pod":{"name":"ginkgo-worker-0"},"namespace":"production"},"ginkgo":{"log_category":"system","event_type":"ENGINE_STARTED"}}
```

### 本地环境（Rich 控制台 + 文件）

```
[10:30:00] [INFO] ginkgo.engine: Engine started
```
