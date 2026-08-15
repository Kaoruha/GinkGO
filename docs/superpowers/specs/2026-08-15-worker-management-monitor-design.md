# Worker 管理页纯监控化改造设计

- 日期：2026-08-15
- 分支：epic-6910-frontend-electron-dual-form
- 状态：已批准（用户选定方案：删假按钮 → 纯监控页）

## 背景与问题

`frontend/src/renderer/views/admin/WorkerManagement.vue`（413 行）存在三类问题：

1. **假按钮（硬伤）**：启动/停止按钮调用 `POST /api/v1/system/workers/{id}/start|stop`
   （`frontend/src/renderer/api/modules/system.ts:111-119`），后端 `api/api/system.py`
   无此端点，点击必然 404。架构上 worker 为独立进程/容器，API 进程没有对它们的
   生命周期控制通道（Kafka control 总线未接到该端点）。
2. **信息量不足**（用户主诉"页面偏简单"）：心跳显示原始 ISO 字符串；回测 worker
   的 `task_count` 只是数字，看不到具体任务；统计卡片与类型筛选不联动。
3. **状态语义漂移风险**：前端硬编码 status 文案映射，与后端 `_normalize_status` 双份维护。

## 目标

- 页面定位收口为「监控」：删除不可用的控制能力，不新增后端控制端点。
- 提升监控信息密度：心跳相对化 + stale 预警、回测 worker 活跃任务下钻、统计卡联动。

## 非目标

- 不实现 worker start/stop（需 control 总线协议 + worker 侧响应，另立 issue）。
- 不做执行节点 / 调度器的下钻（心跳数据不足以支撑，执行节点心跳仅
  host/port/active_strategies；后续心跳富化后可扩展）。
- 不引入 WebSocket 推送，维持轮询。

## 方案

### ① 删除假按钮

- 模板：删 start/stop 按钮、`action-buttons` 样式、`ConfirmDialog`、"操作"列。
- Store（`stores/system.ts`）：删 `startWorker` / `stopWorker`。
- API 模块（`api/modules/system.ts`）：删 `startWorker` / `stopWorker`。
- 相关 store 单测同步清理。

### ② 心跳相对化 + stale 预警

- 复用现成 `formatRelativeTime`（`utils/format.ts:105`，已有单测）。
- stale 判定阈值对齐心跳真实节奏（backtest worker `heartbeat_interval=10s`、
  `ttl=30s`，`workers/backtest_worker/node.py:69-70`）：
  - > 30s（超 TTL）：橙色
  - > 60s（两倍 TTL 仍无心跳）：红色
- 相对时间随自动刷新（5s）重新渲染——计算依赖 `lastUpdate`（store 已有）作为
  响应式 tick 源，避免额外定时器。
- 状态列同时应用高亮（stale 状态优先级高于 status tag 颜色）。

### ③ 回测 worker 活跃任务下钻（后端 + 前端）

数据链路（全部已有，无需新表/新协议）：

```
心跳 BacktestWorkerHeartbeat.task_uuids (#6846)
  → SystemService._format_workers 透传 task_uuids（当前被丢弃）
  → 新端点 GET /api/v1/system/workers/{worker_id}/tasks
      → MySQL backtest_task（task_id = task_uuid；name/status/progress 均有）
```

后端：

- `system_service.py`：
  - `_format_workers` 的 backtest_worker 分支增加 `"task_uuids"` 字段。
  - 新增 `get_worker_tasks(worker_id) -> Dict`：从心跳取 task_uuids，经
    BacktestTaskService 按 task_id 批量查询 name / status / progress /
    portfolio_id；worker 不存在或非回测类型返回空列表（含语义标记）。
- `api/api/system.py`：新增
  `GET /workers/{worker_id}/tasks`（两段路径，与单段的
  `/workers/{worker_type}` 类型路由无冲突）。分层遵守 API → Service → CRUD。

前端：

- `api/modules/system.ts`：`WorkerInfo` 增加 `task_uuids?: string[]`；
  新增 `getWorkerTasks(workerId)`。
- `WorkerManagement.vue`：回测 worker 行加展开箭头，展开行内嵌活跃任务
  小表格（任务名 / 状态 / 进度条 / portfolio）。展开时懒加载（首次点击
  才调下钻端点），自动刷新不自动刷新展开内容（避免表格行跳动）。
- 空任务 / worker 离线：展开行显示"无活跃任务"。

### ④ 统计卡与筛选联动

- 四个统计卡的计算基数从 `workers` 改为 `filteredWorkers`。
- 筛器选择"全部类型"时行为与现状一致。

## 错误处理

- 下钻端点失败：展开行内联提示"加载失败"，toast 一次，不阻塞列表。
- `task_uuids` 为空数组：显示"无活跃任务"（正常态，非错误）。
- 后端沿用 `ok()` 信封 + try/except 兜底返回空列表的既有模式。

## 测试

- 后端 pytest：
  - `system_service._format_workers` 透传 task_uuids。
  - 新端点：正常（有任务）/ 空 worker / 未知 worker_id 三态。
- 前端 vitest：
  - store：删 start/stop 后导出面回归。
  - 页面级（如现有测试模式支持）：统计卡联动逻辑、stale 阈值分级函数。
- 手工冒烟：`ginkgo serve api` + 前端页面对照 Redis 心跳数据。

## 改动面清单

| 层 | 文件 | 改动 |
|---|---|---|
| 后端 | `api/api/system.py` | +1 端点（workers/{worker_id}/tasks） |
| 后端 | `src/ginkgo/core/services/system_service.py` | _format_workers 透传 task_uuids；+get_worker_tasks |
| 前端 | `views/admin/WorkerManagement.vue` | 删控制列；心跳相对化+stale；下钻展开行；统计卡联动 |
| 前端 | `stores/system.ts` | 删 startWorker/stopWorker |
| 前端 | `api/modules/system.ts` | 删两方法；+getWorkerTasks；WorkerInfo 扩展 |
| 测试 | 两侧测试目录 | 见上 |
