# SSE 回测进度推送功能

## 功能概述

SSE (Server-Sent Events) 回测进度推送功能允许前端实时接收回测任务的进度更新，无需轮询 API。

## 架构设计

```
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│   回测 Worker   │────▶│    Kafka        │────▶│  Progress       │
│  (执行回测)      │     │ (进度消息队列)   │     │  Consumer       │
└─────────────────┘     └─────────────────┘     └─────────────────┘
                                                          │
                                                          ▼
                                                   ┌─────────────┐
                                                   │   MySQL     │
                                                   │ (持久化存储) │
                                                   └─────────────┘
                                                          │
                                                          ▼
                                                   ┌─────────────┐
                                                   │   Redis     │
                                                   │ (实时缓存)   │
                                                   │ TTL: 60秒   │
                                                   └─────────────┘
                                                          │
                                                          ▼
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│   前端页面       │────▶│  SSE 端点       │────▶│  Redis Client  │
│ (EventSource)   │     │ /backtest/{id}  │     │  (读取进度)     │
│                 │     │     /events     │     │                 │
└─────────────────┘     └─────────────────┘     └─────────────────┘
```

## 后端实现

### 1. Redis 客户端 (`/home/kaoru/Ginkgo/apiserver/core/redis_client.py`)

提供异步 Redis 连接管理和进度数据存储：

```python
# 设置进度
await set_backtest_progress(task_uuid, progress_data, ttl=60)

# 获取进度
progress = await get_backtest_progress(task_uuid)
```

### 2. SSE 端点 (`/home/kaoru/Ginkgo/apiserver/api/backtest.py`)

提供 SSE 流式响应：

```python
@router.get("/{uuid}/events")
async def backtest_events(uuid: str):
    """SSE 端点 - 推送回测进度"""
    async def event_generator():
        while True:
            progress = await get_backtest_progress(uuid)
            if progress:
                yield f"data: {json.dumps(progress)}\n\n"
                if progress.get('state') in ['COMPLETED', 'FAILED', 'CANCELLED']:
                    break
            await asyncio.sleep(1)

    return StreamingResponse(event_generator(), media_type="text/event-stream")
```

### 3. 进度消费者 (`/home/kaoru/Ginkgo/apiserver/services/backtest_progress_consumer.py`)

消费 Kafka 消息并更新数据库和 Redis：

```python
async def _update_progress(self, task_uuid: str, progress: float, ...):
    # 更新 MySQL
    await db.execute(query, [progress, state, task_uuid])

    # 写入 Redis (TTL 60秒)
    progress_data = {
        "progress": progress,
        "state": state,
        "current_date": current_date,
        "updated_at": datetime.utcnow().isoformat()
    }
    await set_backtest_progress(task_uuid, progress_data, ttl=60)
```

## 前端实现

### 1. API 模块 (`/home/kaoru/Ginkgo/web-ui/src/api/modules/backtest.ts`)

提供订阅 SSE 的方法：

```typescript
// 创建 SSE 连接
const eventSource = backtestApi.subscribeProgress(
  taskUuid,
  // onProgress
  (data) => {
    progress.value = data.progress
    currentDate.value = data.current_date
  },
  // onComplete
  (data) => {
    console.log('回测完成', data)
  },
  // onError
  (error) => {
    console.error('SSE 错误', error)
  }
)

// 关闭连接
eventSource.close()
```

### 2. 详情页面 (`/home/kaoru/Ginkgo/web-ui/src/views/Backtest/BacktestDetail.vue`)

实时显示回测进度：

```vue
<template>
  <a-progress :percent="progress" />
  <div v-if="currentDate">当前日期: {{ currentDate }}</div>
</template>

<script setup>
const progress = ref(0)
const currentDate = ref('')

const startSSE = () => {
  eventSource = backtestApi.subscribeProgress(
    taskUuid,
    (data) => {
      progress.value = data.progress
      currentDate.value = data.current_date
    },
    async (data) => {
      await loadDetail() // 重新加载详情
      eventSource.close()
    }
  )
}
</script>
```

## 使用流程

1. **创建回测任务**
   ```bash
   POST /api/backtest
   {
     "name": "测试回测",
     "portfolio_uuids": ["xxx"],
     "engine_config": {...}
   }
   ```

2. **跳转到详情页**
   ```
   浏览器访问: /backtest/{task_uuid}
   ```

3. **自动建立 SSE 连接**
   - 前端自动调用 `subscribeProgress()`
   - 建立 SSE 连接: `/api/backtest/{uuid}/events`
   - 开始接收实时进度更新

4. **进度实时更新**
   - Worker 发送进度消息到 Kafka
   - Progress Consumer 更新 MySQL 和 Redis
   - SSE 端点从 Redis 读取进度并推送给前端
   - 前端实时更新进度条和日期

5. **连接自动关闭**
   - 任务完成 (COMPLETED)
   - 任务失败 (FAILED)
   - 任务取消 (CANCELLED)
   - 发生错误 (ERROR)

## 数据格式

### SSE 事件格式

```
data: {"progress": 50.0, "state": "RUNNING", "current_date": "2024-01-01", "updated_at": "2024-01-01T12:00:00"}

data: {"progress": 100.0, "state": "COMPLETED", "result": {...}, "updated_at": "2024-01-01T12:01:00"}
event: complete

data: {"error": "Worker timeout", "state": "ERROR", "progress": 0.0}
event: error
```

### 进度数据结构

```typescript
interface BacktestProgress {
  progress: number        // 进度百分比 (0-100)
  state?: string          // 状态 (RUNNING, COMPLETED, FAILED, CANCELLED)
  current_date?: string   // 当前回测日期
  result?: object         // 回测结果 (完成时)
  error?: string          // 错误信息 (失败时)
  updated_at: string      // 更新时间戳
}
```

## 配置要求

### 后端依赖

```
redis>=7.0.0  # 支持 asyncio
```

### Redis 配置

在 `/home/kaoru/Ginkgo/apiserver/core/config.py` 中配置：

```python
GINKGO_REDISHOST: str = "localhost"
GINKGO_REDISPORT: int = 6379
```

## 优势

1. **实时性好**: 服务器主动推送，无需客户端轮询
2. **性能高**: 单向通信，比 WebSocket 更简单
3. **可靠性强**: 自动重连，浏览器原生支持
4. **缓存优化**: Redis 缓存 60 秒，减少数据库查询
5. **用户体验好**: 进度条实时更新，无需手动刷新

## 测试

运行测试脚本：

```bash
cd /home/kaoru/Ginkgo/apiserver
/home/kaoru/Ginkgo/.venv/bin/python scripts/test_sse.py
```

## 注意事项

1. **Redis 可用性**: 确保 Redis 服务正常运行
2. **网络连接**: SSE 需要稳定的网络连接
3. **资源清理**: 组件卸载时记得关闭 EventSource
4. **错误处理**: 处理 SSE 连接错误和超时
5. **并发控制**: 避免同一页面创建多个 SSE 连接

## 文件清单

- `/home/kaoru/Ginkgo/apiserver/core/redis_client.py` - Redis 客户端工具
- `/home/kaoru/Ginkgo/apiserver/api/backtest.py` - SSE 端点实现
- `/home/kaoru/Ginkgo/apiserver/services/backtest_progress_consumer.py` - 进度消费者
- `/home/kaoru/Ginkgo/web-ui/src/api/modules/backtest.ts` - 前端 API 封装
- `/home/kaoru/Ginkgo/web-ui/src/views/Backtest/BacktestDetail.vue` - 详情页面
- `/home/kaoru/Ginkgo/apiserver/scripts/test_sse.py` - 测试脚本
