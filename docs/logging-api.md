# LogService API 文档

**Feature**: 012-distributed-logging
**Last Updated**: 2026-02-26

## 概述

LogService 是日志查询服务，封装了 Grafana Loki LogQL API，提供业务日志查询功能。支持按组合、策略、链路追踪 ID 等条件过滤。

## 服务访问

```python
from ginkgo import services

log_service = services.logging.log_service()

# 或者直接访问 Loki 客户端
loki_client = services.logging.loki_client()
```

## API 方法

### 1. query_logs - 通用日志查询

查询日志，支持多条件过滤。

```python
logs = log_service.query_logs(
    portfolio_id="portfolio-uuid",
    strategy_id="strategy-uuid",
    trace_id="trace-123",
    level="error",
    start_time=datetime.now() - timedelta(hours=1),
    end_time=datetime.now(),
    limit=100,
    offset=0
)
```

**参数：**

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| portfolio_id | str | 否 | 组合 ID 过滤 |
| strategy_id | str | 否 | 策略 ID 过滤 |
| trace_id | str | 否 | 链路追踪 ID 过滤 |
| level | str | 否 | 日志级别 (error, warning, info, debug) |
| start_time | datetime | 否 | 开始时间（预留，暂未实现） |
| end_time | datetime | 否 | 结束时间（预留，暂未实现） |
| limit | int | 否 | 最大返回结果数，默认 100 |
| offset | int | 否 | 偏移量（预留，暂未实现） |

**返回：**

```python
[
    {
        "timestamp": 1234567890000000000,  # 纳秒时间戳
        "message": '{"level":"info","message":"Processing signal",...}'
    },
    ...
]
```

### 2. query_by_portfolio - 按组合 ID 查询

查询某个组合的所有日志。

```python
logs = log_service.query_by_portfolio(
    portfolio_id="portfolio-uuid",
    level="error",    # 可选
    limit=200,        # 可选
    offset=0          # 可选
)
```

**使用场景：**
- 回测完成后查看所有日志
- 调试特定组合的运行问题
- 生成组合运行报告

### 3. query_by_trace_id - 按追踪 ID 查询

查询完整的请求链路日志。

```python
logs = log_service.query_by_trace_id(trace_id="trace-123")
```

**使用场景：**
- 追踪跨服务请求链路
- 分析分布式调用时序
- 排查跨组件问题

**返回结果已按时间排序，可直接展示：**

```python
for log in logs:
    print(f"[{log['timestamp']}] {log['message']}")
```

### 4. query_errors - 查询错误日志

查询错误日志，支持按组合过滤。

```python
# 查询所有错误
errors = log_service.query_errors(limit=50)

# 查询特定组合的错误
errors = log_service.query_errors(
    portfolio_id="portfolio-uuid",
    limit=100
)
```

**使用场景：**
- 快速定位系统错误
- 错误统计和分析
- 错误报告生成

### 5. get_log_count - 获取日志数量

获取日志数量统计。

```python
# 统计某个组合的日志总数
count = log_service.get_log_count(
    portfolio_id="portfolio-uuid"
)

# 统计某个组合的错误日志数
error_count = log_service.get_log_count(
    portfolio_id="portfolio-uuid",
    level="error"
)
```

## Web UI 集成示例

### FastAPI 端点实现

```python
from fastapi import APIRouter, Query
from typing import Optional
from ginkgo import services

router = APIRouter()
log_service = services.logging.log_service()

@router.get("/api/backtests/{portfolio_id}/logs")
async def get_backtest_logs(
    portfolio_id: str,
    level: Optional[str] = Query(None, description="日志级别过滤"),
    limit: int = Query(100, ge=1, le=1000, description="返回条数"),
    offset: int = Query(0, ge=0, description="偏移量")
):
    """获取回测日志 API"""
    try:
        logs = log_service.query_logs(
            portfolio_id=portfolio_id,
            level=level,
            limit=limit,
            offset=offset
        )
        return {
            "success": True,
            "data": logs,
            "total": len(logs)
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }

@router.get("/api/backtests/{portfolio_id}/errors")
async def get_backtest_errors(
    portfolio_id: str,
    limit: int = Query(50, ge=1, le=500)
):
    """获取回测错误日志"""
    errors = log_service.query_errors(
        portfolio_id=portfolio_id,
        limit=limit
    )
    return {
        "success": True,
        "data": errors,
        "total": len(errors)
    }

@router.get("/api/traces/{trace_id}/logs")
async def get_trace_logs(trace_id: str):
    """获取链路追踪日志"""
    logs = log_service.query_by_trace_id(trace_id=trace_id)
    return {
        "success": True,
        "data": logs
    }
```

### 前端调用示例

```typescript
// 获取回测日志
async function getBacktestLogs(portfolioId: string, level?: string) {
  const response = await fetch(
    `/api/backtests/${portfolioId}/logs?level=${level || ''}&limit=100`
  );
  const data = await response.json();
  return data.data;
}

// 获取错误日志
async function getBacktestErrors(portfolioId: string) {
  const response = await fetch(
    `/api/backtests/${portfolioId}/errors?limit=50`
  );
  const data = await response.json();
  return data.data;
}
```

## 错误处理

### Loki 不可用时的优雅降级

当 Loki 服务不可用时，LogService 会优雅降级，返回空列表而不是抛出异常：

```python
from ginkgo.libs.exceptions import ServiceUnavailable

try:
    logs = log_service.query_by_portfolio(portfolio_id="xxx")
    if not logs:
        print("无日志或 Loki 不可用")
except ServiceUnavailable:
    print("无法连接到日志服务")
```

### LokiClient 错误处理

```python
# LokiClient 内部处理所有 HTTP 异常
# 连接失败、超时等情况都会返回空列表
logs = loki_client.query("{level='error'}", limit=100)
# 如果 Loki 不可用，logs = []
```

## LogQL 查询字符串

LogService 会根据查询参数自动构建 LogQL 查询字符串：

```python
# 单条件
query_by_portfolio("portfolio-123")
  → LogQL: '{portfolio_id="portfolio-123"}'

# 多条件
query_logs(portfolio_id="portfolio-123", level="error")
  → LogQL: '{portfolio_id="portfolio-123", level="error"}'

# 链路追踪
query_by_trace_id("trace-456")
  → LogQL: '{trace_id="trace-456"}'

# 无条件（所有日志）
query_logs()
  → LogQL: '{}'
```

## 性能考虑

### 1. 限制返回结果数

```python
# 推荐: 使用 limit 参数
logs = log_service.query_by_portfolio(portfolio_id, limit=100)

# 避免: 不限制结果数
logs = log_service.query_by_portfolio(portfolio_id)  # 默认 limit=100
```

### 2. 使用时间范围过滤（未来支持）

```python
# 使用时间范围减少查询数据量
logs = log_service.query_logs(
    portfolio_id=portfolio_id,
    start_time=datetime.now() - timedelta(hours=1),
    end_time=datetime.now()
)
```

### 3. 缓存查询结果

```python
from functools import lru_cache

@lru_cache(maxsize=128)
def get_cached_logs(portfolio_id: str, level: str = None):
    return log_service.query_by_portfolio(portfolio_id, level=level)
```

## 高级用法

### 1. 自定义 Loki 客户端

```python
from ginkgo.services.logging.clients import LokiClient

# 自定义 Loki endpoint
custom_client = LokiClient(base_url="http://custom-loki:3100")

# 创建自定义 LogService
custom_log_service = LogService(loki_client=custom_client)
logs = custom_log_service.query_by_portfolio("portfolio-123")
```

### 2. 直接使用 LokiClient

```python
loki_client = services.logging.loki_client()

# 直接执行 LogQL 查询
logs = loki_client.query('{level="error"} |= "database"', limit=50)
```

### 3. 组合多个过滤条件

```python
# 查询特定策略的错误日志
logs = log_service.query_logs(
    portfolio_id="portfolio-123",
    strategy_id="strategy-456",
    level="error",
    limit=100
)
```

## 相关文档

- [快速开始](../specs/012-distributed-logging/quickstart.md)
- [架构设计](../specs/012-distributed-logging/plan.md)
- [数据模型](../specs/012-distributed-logging/data-model.md)
- [API 契约](../specs/012-distributed-logging/contracts/log-api-contract.md)
