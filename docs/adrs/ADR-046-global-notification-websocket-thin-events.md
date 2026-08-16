# ADR-046: 全局通知 WebSocket 薄事件推送链路

**Status:** Accepted（前后端已落地，端到端手工验证见下；2026-08-16 修订：连接生命周期内化至模块，见 §5）
**Date:** 2026-08-16
**Related:** ADR-042（双形态前端，ws 鉴权走 query param）、ADR-044（safeStorage token 经 useAuth 收口）

## Context

`/ws/portfolio` 连接管理器长期存在但 `broadcast` 全仓零调用方——前端三个消费者（回测列表/详情/组合 Tab）订阅的全是死通道，进度只能靠页面各自轮询（详情页 5s 拉任务本体，Tab 靠 store 轮询）。同时存在多套并行机制：backtest store 自带 polling/ws 状态、system store 有 wsConnected、`useRealtime.ts` 无引用。

期望终态：**一条全局通知 WS**（登录即连/登出即断）承载薄事件推送——回测进度、实例状态、通知；前端收事件后节流拉 REST 刷新 UI + toast。行情流走独立连接（本轮不动）。

## Decision

### 1. 薄事件信封（无兼容负担——旧 broadcast 零调用方，旧前端 handler 全是死代码）

```json
{"type":"event","event":"…","entity":"backtest_task|deployment|worker|notification","id":"<uuid>","status":"<小写,与REST/DB一致>","data":{…薄字段},"timestamp":"iso"}
```

事件目录：`backtest.progress|stage|completed|failed|stopped`、`deployment.changed`、`worker.changed`、`notification`。事件只做信号不含数据本体，前端按 id 定位行/实体后拉 REST。

### 2. 事件源（API 进程内三路汇入 connection_manager）

- **回测**：`BacktestProgressConsumer` 五个 `_update_*` 在 DB+Redis 写完后广播（Kafka 消费本就在 API 事件循环上，`await broadcast_event` 安全）。
- **部署**：deploy handler 成功/失败路径各广播一次，try/except 包裹（WS 故障不得影响 deploy）。
- **通知**：新增 `NotificationConsumer`（group_id=`api-notification-broadcaster`，与 NotificationWorker 不同组避免抢分区；offset=latest——toast 不重放）。
- **Worker 存活**：新增 `WorkerStatusWatcher`（10s 快照 diff，服务端一次轮询吸收 N 个前端轮询；首轮只播种不广播）。

### 3. 定向与全播

`MBacktestTask`/`MDeployment` 无 user 列 → 全员广播（单用户项目可接受）；通知走 `broadcast_to_user`（connection metadata 已有 user_uuid），无匹配 fall back 全员。

### 4. 不做全局 seq，做重连补齐

WS 每次连上（含首连）触发 catchup 回调（`onReconnect`），页面幂等全量刷新。理由：事件本身不携带数据（前端反正要拉 REST），补齐 = 重拉一次列表，无需 seq 排序合并。

### 5. 前端分层

- `useWebSocket.ts`：只管连接（`shallowRef` 存 socket——深响应 ref 会把实例包成 reactive 代理，身份守卫恒失效；指数退避 1s→30s+抖动；1008 鉴权拒绝不重试，恢复靠登录态翻转；65s watchdog 半开检测）。**连接生命周期模块自管理**（2026-08-16 修订，原归 `App.vue`）：首个消费者调用 `useWebSocket()` 时绑定登录态 watch（登录即连/登出即断，幂等），`connect`/`disconnect` 不再导出——曾因多组件并发调用 `connect` 产生孤儿连接竞态（`await` 窗口穿透 readyState 检查、覆盖 `ws` 引用，孤儿被回收时误降 `isConnected` 并叠加重连，后端日志呈 3~6s 断连抖动），唯一调用方由"接口不存在"结构性保证，`App.vue` 不再持有连接权柄。
- `useServerEvents.ts`：事件层（`on`/`onReconnect`/`scheduleRefetch` per-key trailing 合并/`useNotificationToasts`）。N 个事件塌缩成一次列表刷新。
- 消费者：ListPage 行内 patch + 5s 断线轮询兜底；DetailPage 直接 patch 本地 `currentTask`（丢 store 往返）+ 轮询反转为断线兜底（连线停、断线且活跃才启）；BacktestTab 全走 `scheduleRefetch`。
- 死代码删除：`useRealtime.ts`、backtest store 的 polling/ws 机制与 `updateProgress`、system store 的 `wsConnected/setWsConnected`。

## Rationale

- **为何薄事件不做厚推送**：事件只做"变了"的信号，数据一致性归 REST 单一来源；避免 WS 推送与 GET 返回两套形状漂移。
- **为何重连补齐不做 seq**：见决策 4——消费者反正幂等拉 REST，seq 的排序合并收益为零，维护单调计数器的成本（Redis/多实例）纯浪费。
- **为何服务端 Watcher 吸收前端轮询**：N 个打开的 Dashboard 各自轮询 workers → 服务端 1 次 10s 快照 diff，广播增量。
- **为何 WS 不换 SSE**：用户质询后评估——连接管理器/订阅协议/Electron ws 鉴权（query param）均已就绪，SSE 要重建一半且丢双向（subscribe topic）；单用户自用项目单连接开销无感。保留 WS。

## Consequences

- 回测列表/详情/Tab 进度从轮询主路径翻转为 WS 主路径，轮询仅在断线窗口兜底。
- 详情页修复"重跑后进度不更新"（旧路径 store 往返依赖 tasks 列表碰巧含同 id 任务）；列表页修复 status 大小写（旧 `data.type` 直写大写态名）。
- 后端 API 进程新增三个后台任务（progress consumer 原有 + notification consumer + worker watcher），lifespan 统一启停。

## 后续项（范围外）

- SSE 旧通道退役。
- `system.events`（/ws/system）消费端补齐。
- Dashboard 订阅 `worker.changed` 实时刷新（当前仍走 Watcher 同源的 REST 轮询）。
- 行情 MarketData.vue 独立连接的收口（鉴权/重连策略对齐本 ADR）。

## 判定标准自检

- [x] 单测：信封构造/定向广播/三消费者/watcher（后端 37 例）+ 前端连接健壮性与事件层（13 例）
- [x] `pytest -n auto` 触碰文件回归通过（全量其余失败均为既有，与本链路无关）
- [x] `pnpm test` 119/119、`vue-tsc --noEmit` 干净
- [x] 端到端验证（DEVELOPMENT 集群，2026-08-16）：WS token 鉴权连接；`docker restart` worker → 10s 内收到 `worker.changed` offline/running 两帧；Kafka `ginkgo.notifications` 发消息 → 收到定向 `notification` 帧（信封/level 小写正确）；heartbeat 30s 帧正常。验证中发现集群缺 `ginkgo.notifications` topic（已手动补建，`backtest.progress` 等既有 topic 正常）
