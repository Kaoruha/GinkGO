# API Contract: LogService

**Service**: LogService - 日志查询服务
**Version**: 1.0.0
**Date**: 2026-03-10

## Overview

LogService 是日志查询服务，封装 ClickHouse SQL 查询 API，支持回测日志、组件日志、性能日志的分表查询和跨表关联查询。

---

## API Methods

### 1. query_backtest_logs

查询回测业务日志，支持按组合 ID、策略 ID、日志级别等条件过滤。

**Signature**:
```python
def query_backtest_logs(
    portfolio_id: Optional[str] = None,
    strategy_id: Optional[str] = None,
    level: Optional[str] = None,
    start_time: Optional[datetime] = None,
    end_time: Optional[datetime] = None,
    limit: int = 100,
    offset: int = 0
) -> List[Dict[str, Any]]:
```

**Parameters**:

| 参数 | 类型 | 必需 | 说明 |
|------|------|------|------|
| portfolio_id | str | 否 | 组合 ID 过滤 |
| strategy_id | str | 否 | 策略 ID 过滤 |
| level | str | 否 | 日志级别过滤（DEBUG/INFO/WARNING/ERROR/CRITICAL） |
| start_time | datetime | 否 | 开始时间 |
| end_time | datetime | 否 | 结束时间 |
| limit | int | 否 | 最大返回结果数（默认 100，最大 1000） |
| offset | int | 否 | 偏移量（默认 0） |

**Returns**:
```python
List[Dict[str, Any]]  # 日志条目列表
```

**Example**:
```python
# 查询指定组合的日志
logs = log_service.query_backtest_logs(
    portfolio_id="portfolio-001",
    level="ERROR",
    limit=50
)
```

---

### 2. query_component_logs

查询组件运行日志，支持按组件名称、模块名等条件过滤。

**Signature**:
```python
def query_component_logs(
    component_name: Optional[str] = None,
    module_name: Optional[str] = None,
    level: Optional[str] = None,
    start_time: Optional[datetime] = None,
    end_time: Optional[datetime] = None,
    limit: int = 100,
    offset: int = 0
) -> List[Dict[str, Any]]:
```

**Parameters**:

| 参数 | 类型 | 必需 | 说明 |
|------|------|------|------|
| component_name | str | 否 | 组件名称过滤（Strategy/Analyzer/RiskManagement 等） |
| module_name | str | 否 | 模块名称过滤 |
| level | str | 否 | 日志级别过滤 |
| start_time | datetime | 否 | 开始时间 |
| end_time | datetime | 否 | 结束时间 |
| limit | int | 否 | 最大返回结果数 |
| offset | int | 否 | 偏移量 |

**Example**:
```python
# 查询 Strategy 组件的日志
logs = log_service.query_component_logs(
    component_name="Strategy",
    level="DEBUG"
)
```

---

### 3. query_performance_logs

查询性能监控日志，支持按函数名、最小耗时等条件过滤。

**Signature**:
```python
def query_performance_logs(
    function_name: Optional[str] = None,
    min_duration: Optional[float] = None,
    max_duration: Optional[float] = None,
    start_time: Optional[datetime] = None,
    end_time: Optional[datetime] = None,
    limit: int = 100
) -> List[Dict[str, Any]]:
```

**Parameters**:

| 参数 | 类型 | 必需 | 说明 |
|------|------|------|------|
| function_name | str | 否 | 函数名称过滤 |
| min_duration | float | 否 | 最小耗时（毫秒） |
| max_duration | float | 否 | 最大耗时（毫秒） |
| start_time | datetime | 否 | 开始时间 |
| end_time | datetime | 否 | 结束时间 |
| limit | int | 否 | 最大返回结果数 |

**Example**:
```python
# 查询耗时超过 100ms 的日志
logs = log_service.query_performance_logs(
    min_duration=100.0,
    limit=50
)
```

---

### 4. query_by_trace_id

跨表查询指定 trace_id 的所有日志，返回完整链路日志。

**Signature**:
```python
def query_by_trace_id(
    trace_id: str,
    start_time: Optional[datetime] = None,
    end_time: Optional[datetime] = None
) -> Dict[str, List[Dict[str, Any]]]:
```

**Parameters**:

| 参数 | 类型 | 必需 | 说明 |
|------|------|------|------|
| trace_id | str | 是 | 追踪 ID |
| start_time | datetime | 否 | 开始时间 |
| end_time | datetime | 否 | 结束时间 |

**Returns**:
```python
{
    "backtest": [...],    # 回测日志列表
    "component": [...],   # 组件日志列表
    "performance": [...]  # 性能日志列表
}
```

**Example**:
```python
# 查询完整链路日志
logs = log_service.query_by_trace_id("trace-abc-123")
all_logs = (
    logs["backtest"] +
    logs["component"] +
    logs["performance"]
)
all_logs.sort(key=lambda x: x["timestamp"])
```

---

### 5. search_logs

跨表关键词全文搜索。

**Signature**:
```python
def search_logs(
    keyword: str,
    tables: Optional[List[str]] = None,
    level: Optional[str] = None,
    start_time: Optional[datetime] = None,
    end_time: Optional[datetime] = None,
    limit: int = 100
) -> Dict[str, List[Dict[str, Any]]]:
```

**Parameters**:

| 参数 | 类型 | 必需 | 说明 |
|------|------|------|------|
| keyword | str | 是 | 搜索关键词 |
| tables | List[str] | 否 | 指定搜索的表（默认搜索所有表） |
| level | str | 否 | 日志级别过滤 |
| start_time | datetime | 否 | 开始时间 |
| end_time | datetime | 否 | 结束时间 |
| limit | int | 否 | 每张表最大返回结果数 |

**Example**:
```python
# 搜索包含"数据库连接失败"的日志
logs = log_service.search_logs(
    keyword="数据库连接失败",
    level="ERROR"
)
```

---

### 6. join_with_backtest_results

与回测结果表关联查询，实现日志与结果的联合分析。

**Signature**:
```python
def join_with_backtest_results(
    portfolio_id: str,
    limit: int = 100
) -> List[Dict[str, Any]]:
```

**Parameters**:

| 参数 | 类型 | 必需 | 说明 |
|------|------|------|------|
| portfolio_id | str | 是 | 组合 ID |
| limit | int | 否 | 最大返回结果数 |

**Returns**:
```python
List[Dict[str, Any]]  # 包含日志和回测结果的联合记录
```

**Example**:
```python
# 查询回测结果及其相关日志
results = log_service.join_with_backtest_results(
    portfolio_id="portfolio-001"
)
```

---

### 7. get_log_count

获取日志数量统计。

**Signature**:
```python
def get_log_count(
    table: str,
    portfolio_id: Optional[str] = None,
    level: Optional[str] = None,
    start_time: Optional[datetime] = None,
    end_time: Optional[datetime] = None
) -> int:
```

**Parameters**:

| 参数 | 类型 | 必需 | 说明 |
|------|------|------|------|
| table | str | 是 | 表名（backtest/component/performance） |
| portfolio_id | str | 否 | 组合 ID 过滤（仅 backtest 表） |
| level | str | 否 | 日志级别过滤 |
| start_time | datetime | 否 | 开始时间 |
| end_time | datetime | 否 | 结束时间 |

**Returns**:
```python
int  # 日志数量
```

---

## 错误处理

所有方法在 ClickHouse 不可用时应返回友好错误，而非抛出异常。

**错误处理示例**:
```python
def query_backtest_logs(self, **kwargs) -> List[Dict]:
    try:
        # 执行查询
        return self._execute_query(**kwargs)
    except ClickHouseError as e:
        GLOG.error(f"ClickHouse 查询失败: {e}")
        return []  # 返回空列表，不中断业务
    except Exception as e:
        GLOG.error(f"未知错误: {e}")
        return []
```

---

## 数据结构

### 日志条目结构

```python
{
    "uuid": "a1b2c3d4...",
    "timestamp": "2026-03-10T12:00:00",
    "level": "INFO",
    "message": "信号生成成功",
    "logger_name": "ginkgo.strategy",
    "trace_id": "trace-abc-123",
    "span_id": "span-xyz-789",
    # ... 业务字段
}
```

---

## 性能要求

- 按组合 ID 查询日志返回时间 < 3 秒
- 关键词全文搜索响应时间 < 5 秒
- 与回测结果表 JOIN 查询响应时间 < 5 秒
- 分页查询支持百万级日志数据集
