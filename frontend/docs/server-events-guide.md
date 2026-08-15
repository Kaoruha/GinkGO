# 服务端事件推送扩展指南（ADR-046）

> 如何在后端新增一个可推送到前端的事件，以及前端如何消费。架构决策全文见 `docs/adrs/ADR-046-global-notification-websocket-thin-events.md`（仓库根）。

## 架构总览

```
事件源(三路)                      API 进程                     前端
┌─────────────────┐   Kafka   ┌──────────────────┐   WS 帧  ┌──────────────────┐
│ Worker 进程      │ ────────→ │ Consumer 消费     │ ───────→ │ useWebSocket      │
│ (回测进度/通知)   │           │ (DB+Redis 写完后  │          │ (连接/重连/watchdog)│
├─────────────────┤           │  broadcast)      │          │        ↓           │
│ API 进程内       │ ────────→ │ broadcast_event  │          │ useServerEvents   │
│ (deploy 等)      │           │ (events.py)      │          │ (on/onReconnect/  │
├─────────────────┤           ├──────────────────┤          │  scheduleRefetch) │
│ 无推送源,靠 diff │ ────────→ │ Watcher 快照diff  │          │        ↓           │
│ (worker 存活)    │           │ (10s 轮询吸收前端)│          │ 页面: 行内patch /  │
└─────────────────┘           └──────────────────┘          │ 拉REST / toast    │
                                                            └──────────────────┘
```

**核心原则（薄事件）**：事件只做"什么变了"的信号，不带数据本体。前端收到后按 `id` 定位行/实体，拉 REST 刷新。一致性归 REST 单一来源。

## 事件信封

```json
{
  "type": "event",
  "event": "backtest.progress",       // 事件名,<域>.<动作>
  "entity": "backtest_task",          // 实体类型,前端按此过滤
  "id": "48df2479c1fa...",            // 实体 uuid,前端按此定位行
  "status": "running",                // 小写,与 REST/DB 枚举一致
  "data": { "progress": 83 },         // 薄字段,只放定位/提示所需
  "timestamp": "2026-08-15T17:51:22.751039"
}
```

**现有事件目录**：

| event | entity | 触发时机 | 模板源码 |
|---|---|---|---|
| `backtest.progress` | backtest_task | 回测运行中 ~2s/条 | `api/services/backtest_progress_consumer.py` |
| `backtest.stage` | backtest_task | 阶段切换（数据准备/引擎构建） | 同上 |
| `backtest.completed/failed/stopped` | backtest_task | 终态 | 同上 |
| `deployment.changed` | deployment | deploy 成功/失败 | `api/api/deployment.py` |
| `worker.changed` | worker | worker 上线/下线/状态变 | `api/services/worker_status_watcher.py` |
| `notification` | notification | Kafka `ginkgo.notifications` | `api/services/notification_consumer.py` |

## 前端如何消费（四件套）

框架层（`useWebSocket.ts` / `useServerEvents.ts` / `App.vue`）**不用碰**——只认信封不认事件名。消费页固定三种模式：

```typescript
import { useServerEvents } from '@/composables'

const { on, onReconnect, scheduleRefetch } = useServerEvents()

// ① 精确订阅：行内 patch（列表页/详情页模式——就地改行数据，不整表刷新）
on('*', (e) => {
  if (e.entity !== 'backtest_task') return        // 过滤实体
  const hit = rows.value.find(t => t.uuid === e.id) // 按 id 定位行
  if (!hit) return
  if (e.data?.progress != null) hit.progress = e.data.progress
  if (e.status) hit.status = e.status
})
// 也可以 on('backtest.progress', h) 按事件名订阅

// ② 列表类：trailing 合并——N 个事件塌缩成一次 REST 拉取（1s 静默期）
scheduleRefetch('my-page-list', () => loadList({ silent: true }))

// ③ 断线补齐：每次连上（含首连）幂等全量刷新，补回断线窗口丢的事件
onReconnect(() => loadList())

// ④ toast 类：见 useServerEvents.ts 里 useNotificationToasts 的写法，
//    在 App.vue 或常驻组件 setup 里调用一次
```

参考实现：`BacktestListPage.vue`（行内 patch + 断线 5s 轮询兜底）、`BacktestDetailPage.vue`（直接 patch 本地 currentTask + 轮询反转兜底）、`portfolio/tabs/BacktestTab.vue`（纯 scheduleRefetch）。

## 新增一个事件：按事件源选路径

### 路径 A：事件在 API 进程内产生（deploy、CRUD 状态变化）

1. 事件源处加一行广播（WS 故障不得影响业务，须 try/except 包裹）：

```python
from websocket.events import broadcast_event, canonical_status

try:
    await broadcast_event("xxx.changed", "xxx", obj.uuid,
                          status=canonical_status(obj.status))
except Exception:
    logger.warning("broadcast failed", exc_info=True)
```

2. 需要定向到指定用户（如通知）：用 `broadcast_event_to_users(user_uuids, ...)`，无匹配连接自动 fall back 全员。
3. 测试仿 `tests/unit/api/websocket/test_deployment_broadcast.py`。

### 路径 B：事件在 Worker 等其他进程产生（回测类）

1. Worker 端发 Kafka 消息。**新 topic 必须显式建**（broker 不自动创建；`ginkgo.notifications` 曾因 topic 缺失整条链路静默哑火）：
   ```bash
   docker exec ginkgo-kafka1 /opt/kafka/bin/kafka-topics.sh \
     --bootstrap-server localhost:9092 --create --topic <topic> \
     --partitions 1 --replication-factor 1
   ```
2. API 侧：已有 consumer（如 `backtest_progress_consumer.py`）就在对应 `_update_*` 里 DB+Redis 写完后加 `await broadcast_event(...)`；没有则仿 `notification_consumer.py` 新建（注意 **group_id 不得与其他消费者同组**，否则抢分区；toast 类用 offset=latest 不重放），并在 `api/main.py` lifespan 挂 start/stop（仿现有两个 try/except 块）。
3. 测试仿 `tests/unit/api/websocket/test_notification_consumer.py`。

### 路径 C：没有推送源，靠轮询 diff（worker 存活类）

服务端一个 watcher 吸收 N 个前端轮询：仿 `worker_status_watcher.py`——定时快照 → 纯函数 diff → 变化才广播；**首轮只播种不广播**（否则重启风暴）。测试仿 `test_worker_status_watcher.py`。

## 易漏点清单

| # | 陷阱 | 说明 |
|---|---|---|
| 1 | `STATUS_MAP` 新枚举 | `events.py` 里 Kafka/内部大写态 → REST 小写枚举的映射要显式加（如 `CANCELLED→stopped`）；不认识的只 lower 兜底，语义可能错 |
| 2 | Kafka topic 显式建 | broker 不自动建 topic；上线前 `kafka-topics.sh --list` 核实 |
| 3 | consumer group 隔离 | 新 consumer 的 group_id 不得与既有消费者同组（抢分区=互相吞消息） |
| 4 | 前端类型枚举 | `useServerEvents.ts` 的 `ServerEvent['entity']` 联合类型补新实体名 |
| 5 | WS 故障不影响业务 | 广播一律 try/except 包裹，失败只告警 |
| 6 | ADR 目录 | ADR-046 的"事件目录"表补一行，保持文档与代码同步 |

## 调试

- 后端起真服务后，命令行直连看帧（跳过前端）：
  ```bash
  # token 从 POST /api/v1/auth/login 拿
  npx wscat -c "ws://localhost:8000/ws/portfolio?token=<JWT>"
  ```
- 实测样例（2026-08-16，重跑回测抓帧）：`backtest.stage`×2（DATA_PREPARING→ENGINE_BUILDING）→ `backtest.progress`×54（0→100）→ `backtest.completed`。
- 前端单测模板：`composables/__tests__/useWebSocket.spec.ts`（FakeWebSocket + fake timers）、`useServerEvents.spec.ts`（mock useWebSocket 手动派发帧）。
