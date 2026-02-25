# Redis 键统一管理设计

## 概述

`redis_schema.py` 提供统一的 Redis 键命名和数据结构管理，避免在各处硬编码键名和格式。

**源码位置**: `src/ginkgo/data/redis_schema.py`

## 核心组件

### 1. RedisKeyPrefix - 键前缀常量

定义所有 Redis 键的命名空间前缀：

```python
class RedisKeyPrefix:
    # Worker 心跳
    DATA_WORKER_HEARTBEAT = "heartbeat:data_worker"
    BACKTEST_WORKER_HEARTBEAT = "backtest:worker"
    EXECUTION_NODE_HEARTBEAT = "heartbeat:node"
    SCHEDULER_HEARTBEAT = "heartbeat:scheduler"
    TASK_TIMER_HEARTBEAT = "heartbeat:task_timer"

    # 进程管理
    MAIN_CONTROL = "ginkgo:maincontrol"
    WATCHDOG = "ginkgo:watchdog"
    THREAD_POOL = "ginkgo:thread_pool"
    WORKER_STATUS = "ginkgo:worker_status"

    # 任务与缓存
    TASK_STATUS = "ginkgo:task_status"
    FUNC_CACHE = "ginkgo_func_cache"
```

### 2. RedisKeyPattern - 键匹配模式

用于 `KEYS`/`SCAN` 命令的匹配模式：

```python
class RedisKeyPattern:
    ALL_HEARTBEATS = "heartbeat:*"
    EXECUTION_NODE_HEARTBEAT_ALL = "heartbeat:node:*"
    BACKTEST_WORKER_HEARTBEAT_ALL = "backtest:worker:*"
    FUNC_CACHE_ALL = "ginkgo_func_cache_*"
    SYNC_PROGRESS_ALL = "*_update_*"
    ALL_GINKGO_KEYS = "ginkgo:*"
```

### 3. RedisKeyBuilder - 键生成器

**推荐使用**：统一的键生成方法，避免拼写错误。

```python
from ginkgo.data.redis_schema import RedisKeyBuilder

# 心跳键
key = RedisKeyBuilder.backtest_worker_heartbeat("worker_1")
# -> "backtest:worker:worker_1"

key = RedisKeyBuilder.execution_node_heartbeat("node_1")
# -> "heartbeat:node:node_1"

# 缓存键
key = RedisKeyBuilder.func_cache("my_function", "cache_key")
# -> "ginkgo_func_cache_my_function_cache_key"

key = RedisKeyBuilder.sync_progress("tick", "000001.SZ")
# -> "tick_update_000001.SZ"
```

### 4. RedisTTL - TTL 配置

统一的过期时间配置：

```python
class RedisTTL:
    # 心跳 TTL（应大于心跳间隔的2-3倍）
    BACKTEST_WORKER_HEARTBEAT = 30  # 30秒
    DATA_WORKER_HEARTBEAT = 30

    # 数据缓存 TTL
    SYNC_PROGRESS = 60 * 60 * 24 * 30  # 30天
    FUNC_CACHE_DEFAULT = 3600  # 1小时
    TASK_STATUS = 3600 * 24  # 1天
```

### 5. 心跳数据结构

使用 dataclass 定义标准化的心跳数据：

```python
from ginkgo.data.redis_schema import BacktestWorkerHeartbeat, WorkerStatus

# 创建心跳
heartbeat = BacktestWorkerHeartbeat.create(
    worker_id="worker_1",
    status=WorkerStatus.RUNNING,
    running_tasks=3,
    max_tasks=5
)

# 序列化为 JSON
json_data = heartbeat.to_json()

# 从 JSON 反序列化
heartbeat = BacktestWorkerHeartbeat.from_json(json_data)
```

## 键格式速查表

| 功能 | 键格式 | 生成方法 |
|------|--------|----------|
| DataWorker 心跳 | `heartbeat:data_worker:{node_id}` | `RedisKeyBuilder.data_worker_heartbeat(node_id)` |
| BacktestWorker 心跳 | `backtest:worker:{worker_id}` | `RedisKeyBuilder.backtest_worker_heartbeat(worker_id)` |
| ExecutionNode 心跳 | `heartbeat:node:{node_id}` | `RedisKeyBuilder.execution_node_heartbeat(node_id)` |
| Scheduler 心跳 | `heartbeat:scheduler:{node_id}` | `RedisKeyBuilder.scheduler_heartbeat(node_id)` |
| TaskTimer 心跳 | `heartbeat:task_timer:{node_id}` | `RedisKeyBuilder.task_timer_heartbeat(node_id)` |
| 函数缓存 | `ginkgo_func_cache_{func}_{key}` | `RedisKeyBuilder.func_cache(func, key)` |
| 同步进度 | `{type}_update_{code}` | `RedisKeyBuilder.sync_progress(type, code)` |
| 任务状态 | `ginkgo:task_status:{task_id}` | `RedisKeyBuilder.task_status(task_id)` |

## 使用示例

### 发送心跳

```python
from ginkgo.data.redis_schema import (
    RedisKeyBuilder, BacktestWorkerHeartbeat, WorkerStatus, RedisTTL
)

def send_heartbeat(redis_client, worker_id: str, running_tasks: int):
    key = RedisKeyBuilder.backtest_worker_heartbeat(worker_id)
    heartbeat = BacktestWorkerHeartbeat.create(
        worker_id=worker_id,
        status=WorkerStatus.RUNNING,
        running_tasks=running_tasks,
        max_tasks=5
    )
    redis_client.setex(key, RedisTTL.BACKTEST_WORKER_HEARTBEAT, heartbeat.to_json())
```

### 查询所有 Worker 状态

```python
from ginkgo.data.redis_schema import (
    RedisKeyPattern, BacktestWorkerHeartbeat, parse_heartbeat_data
)

def get_all_workers(redis_client):
    keys = redis_client.keys(RedisKeyPattern.BACKTEST_WORKER_HEARTBEAT_ALL)
    workers = []
    for key in keys:
        data = parse_heartbeat_data(redis_client.get(key))
        workers.append(data)
    return workers
```

### 函数缓存

```python
from ginkgo.data.redis_schema import RedisKeyBuilder, RedisTTL

def cache_result(redis_client, func_name: str, params: dict, result: any):
    import json
    cache_key = RedisKeyBuilder.func_cache(func_name, str(hash(str(params))))
    redis_client.setex(cache_key, RedisTTL.FUNC_CACHE_DEFAULT, json.dumps(result))
```

## 工具函数

```python
from ginkgo.data.redis_schema import parse_heartbeat_data, extract_id_from_key

# 解析心跳数据（自动处理 str/dict/bytes）
data = parse_heartbeat_data(redis_client.get(key))

# 从键名提取 ID
node_id = extract_id_from_key("heartbeat:node:node_123", "heartbeat:node:")
# -> "node_123"
```

## 设计原则

1. **单一职责**: 所有 Redis 键定义集中在一个模块
2. **类型安全**: 使用 dataclass 和枚举避免字符串错误
3. **可追溯**: 键生成方法有明确的文档和类型提示
4. **向后兼容**: 保留原有键格式，仅通过统一方法生成

## 相关文件

- `src/ginkgo/data/redis_schema.py` - Schema 定义
- `src/ginkgo/data/services/redis_service.py` - Redis 服务实现
- `src/ginkgo/data/worker/worker.py` - DataWorker 心跳实现
- `src/ginkgo/workers/backtest_worker/node.py` - BacktestWorker 心跳实现
- `src/ginkgo/workers/execution_node/node.py` - ExecutionNode 心跳实现
- `src/ginkgo/livecore/scheduler.py` - Scheduler 心跳实现
- `src/ginkgo/livecore/task_timer.py` - TaskTimer 心跳实现
