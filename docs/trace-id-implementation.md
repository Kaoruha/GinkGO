# 跨容器请求追踪 (trace_id) 实现总结

## 概述

成功实现了基于 Python `contextvars` 的跨容器请求追踪功能，支持在分布式系统中追踪请求链路。

## 实现内容

### T025-T028: 测试编写 (Red 阶段)

在 `tests/unit/libs/test_core_logger.py` 中添加了 4 个测试类，共 6 个测试方法：

1. **TestTraceIdManagement** (3 个测试)
   - `test_set_trace_id_returns_token` - 验证 set_trace_id 返回 Token
   - `test_get_trace_id_returns_current_value` - 验证获取当前 trace_id
   - `test_clear_trace_id_restores_context` - 验证清除后恢复上下文

2. **TestTraceIdContextManager** (1 个测试)
   - `test_exits_clears_trace_id` - 验证上下文管理器自动清除

3. **TestTraceIdThreadIsolation** (1 个测试)
   - `test_threads_have_independent_context` - 验证线程隔离特性

4. **TestTraceIdAsyncPropagation** (1 个测试)
   - `test_async_propagates_trace_id` - 验证异步上下文传播

### T029-T034: 功能实现 (Green 阶段)

在 `src/ginkgo/libs/core/logger.py` 中实现：

#### T029: 创建 contextvars.ContextVar
```python
_trace_id_ctx: contextvars.ContextVar[Optional[str]] = contextvars.ContextVar(
    "trace_id", default=None
)
```

#### T030: set_trace_id 方法
```python
def set_trace_id(self, trace_id: str) -> contextvars.Token:
    """设置当前 trace_id（使用 contextvars）"""
    return _trace_id_ctx.set(trace_id)
```

#### T031: get_trace_id 方法
```python
def get_trace_id(self) -> Optional[str]:
    """获取当前 trace_id"""
    return _trace_id_ctx.get()
```

#### T032: clear_trace_id 方法
```python
def clear_trace_id(self, token: contextvars.Token) -> None:
    """清除 trace_id，恢复之前的值"""
    _trace_id_ctx.reset(token)
```

#### T033: with_trace_id 上下文管理器
```python
@contextlib.contextmanager
def with_trace_id(self, trace_id: str):
    """临时设置 trace_id 的上下文管理器"""
    token = _trace_id_ctx.set(trace_id)
    try:
        yield
    finally:
        _trace_id_ctx.reset(token)
```

#### T034: ecs_processor 集成
```python
# 在 ecs_processor 中添加 trace_id 注入
trace_id = _trace_id_ctx.get()
if trace_id:
    event_dict["trace"] = {"id": trace_id}
```

## 测试结果

所有测试通过 (20/20)：
- 14 个现有测试继续通过
- 6 个新增 trace_id 测试全部通过

## 技术特性

### 1. 线程隔离
`contextvars` 自动提供线程隔离，每个线程有独立的 trace_id 上下文。

### 2. 异步传播
在 async/await 场景下，trace_id 自动传播到整个调用链。

### 3. 上下文管理器
支持临时设置 trace_id，退出后自动恢复原值。

### 4. ECS 兼容
trace_id 按照 ECS 标准格式输出：`{"trace": {"id": "trace-123"}}`

## 使用示例

### 基本使用
```python
from ginkgo.libs.core.logger import GinkgoLogger

logger = GinkgoLogger("my_app")

# 设置 trace_id
token = logger.set_trace_id("trace-123")
logger.INFO("This log has trace_id")

# 清除 trace_id
logger.clear_trace_id(token)
```

### 上下文管理器
```python
# 临时设置 trace_id
with logger.with_trace_id("trace-temp"):
    logger.INFO("Temporary trace_id")
# 自动恢复原值

logger.INFO("Back to original trace_id")
```

### 嵌套上下文
```python
logger.set_trace_id("trace-outer")

with logger.with_trace_id("trace-inner"):
    # trace_id = "trace-inner"
    with logger.with_trace_id("trace-deep"):
        # trace_id = "trace-deep"
        pass
    # trace_id = "trace-inner"

# trace_id = "trace-outer"
```

### ECS 日志输出
```json
{
  "@timestamp": "2024-01-01T12:00:00Z",
  "log": {
    "level": "info",
    "logger": "my_app"
  },
  "message": "Processing request",
  "trace": {
    "id": "trace-123-abc"
  }
}
```

## 分布式追踪集成

trace_id 可与以下系统集成：
- **OpenTelemetry**: 使用相同的 trace_id 概念
- **Jaeger**: 通过 trace.id 字段关联
- **ELK Stack**: Kibana 支持按 trace.id 聚合
- **日志聚合**: 在微服务架构中追踪请求链路

## 相关文件

- 实现: `/home/kaoru/Ginkgo/src/ginkgo/libs/core/logger.py`
- 测试: `/home/kaoru/Ginkgo/tests/unit/libs/test_core_logger.py`
- 演示: `/home/kaoru/Ginkgo/tests/integration/trace_id_demo.py`
