# Composables 使用指南

> 目录：`src/renderer/composables/`。本 README 覆盖服务端事件实时推送机制；其余家族成员见文末速查表。

## 目录

- [服务端事件实时推送（useWebSocket + useServerEvents）](#服务端事件实时推送usewebsocket--useserverevents)
- [Composables 速查表](#composables-速查表)

---

## 服务端事件实时推送（useWebSocket + useServerEvents）

### 概述

ADR-046 全局通知通道：一条 `/ws/portfolio` 长连接（登录即连、登出即断，**生命周期由 useWebSocket 模块自管理**，消费者不碰 connect/disconnect），后端推"薄事件"（只含变了什么，不含数据本体），前端收事件后拉 REST 刷新 UI 或弹 toast。

两层分工：

| 层 | 文件 | 职责 | 消费者要碰的 API |
|---|---|---|---|
| 连接层 | `useWebSocket.ts` | 建连/重连退避/心跳 watchdog/登录态绑定 | `isConnected`、`subscribe`（一般不直接用） |
| 事件层 | `useServerEvents.ts` | 信封解析、按事件名分发、断线补齐、刷新合并 | `on` / `onReconnect` / `scheduleRefetch` / `useNotificationToasts` |

### 事件信封

```json
{"type":"event","event":"backtest.progress","entity":"backtest_task",
 "id":"<uuid>","status":"running","data":{"progress":83},"timestamp":"iso"}
```

`status` 与 REST/DB 枚举一致（小写）；`entity`+`id` 用于定位行；`data` 只放薄字段。

**回测域事件**（worker → Kafka → API 消费广播，运行中 ~2s/条）：

| event | 触发 | data 薄字段 |
|---|---|---|
| `backtest.stage` | 阶段切换（数据准备/引擎构建） | `stage`, `message` |
| `backtest.progress` | 运行中进度 | `progress`, `current_date`, `state` |
| `backtest.completed` / `failed` / `stopped` | 终态 | `progress`/`error` 等 |

其余域（`deployment.changed`、`worker.changed`、`notification`）见 `frontend/docs/server-events-guide.md` 事件目录。

### 基本用法

```typescript
import { useServerEvents } from '@/composables'

const { on, onReconnect, scheduleRefetch } = useServerEvents()

onMounted(() => {
  // ① 行内 patch：就地改行数据（不整表刷新），按 entity+id 定位
  const offs = [
    on('*', (e) => {
      if (e.entity !== 'backtest_task') return
      const hit = rows.value.find(t => t.uuid === e.id)
      if (!hit) return
      if (e.data?.progress != null) hit.progress = e.data.progress
      if (e.status) hit.status = e.status
    }),
    // ② 列表类刷新：trailing 合并——1s 静默期内 N 个事件只拉一次 REST
    //   （页面级 key，如 on('backtest.completed', () => refetchList())）
    // ③ 断线补齐：每次连上（含首连）幂等全量刷新，补回断线窗口丢的事件
    onReconnect(refetchList),
  ]
  unsubscribe = () => offs.forEach(off => off())
})
onUnmounted(() => unsubscribe?.())  // on() 返回取消函数，卸载时务必调
```

toast 类（全局一次性接线，已在 `App.vue` 完成，一般无需重复）：

```typescript
useServerEvents().useNotificationToasts()  // notification 事件 → message[level]
```

### 轮询兜底模式

WS 是主路径，轮询只在断线窗口兜底。两种接法（参考 `BacktestListPage.vue` / `BacktestDetailPage.vue`）：

```typescript
const { isConnected } = useWebSocket()

// 列表页：断线起 5s 轮询，重连自动停
watch(isConnected, (connected) => {
  if (pollTimer) { clearInterval(pollTimer); pollTimer = null }
  if (!connected) pollTimer = window.setInterval(() => fetchTasks(false), 5000)
}, { immediate: true })
```

### 注意事项

1. **不要**在组件里调 `connect()/disconnect()`——它们已模块私有化；多组件并发 connect 曾产生孤儿连接（后端 3~6s 断连抖动）。
2. socket 实例存 `shallowRef`：深响应 `ref` 会把实例包成 reactive 代理，身份守卫（孤儿拦截）恒失效——新增持有 socket/类实例的状态时同理。
3. 事件不带数据本体：需要详情就拉 REST，别往 `data` 里塞大对象（后端侧约束，见扩展指南）。
4. `scheduleRefetch` 的 key 是页面级的（如 `'backtest-tab-list'`），同 key 反复 schedule 只执行最后一次的 fn。

### 扩展新事件

后端加事件源、前端订阅的完整链路（三条路径 + 易漏点清单）见 `frontend/docs/server-events-guide.md`；架构决策见仓库根 `docs/adrs/ADR-046-global-notification-websocket-thin-events.md`。

---

## Composables 速查表

| Composable | 文件 | 一句话用途 |
|---|---|---|
| `useServerEvents` | `useServerEvents.ts` | 服务端薄事件订阅/断线补齐/刷新合并/notification toast（ADR-046） |
| `useWebSocket` | `useWebSocket.ts` | 全局通知 WS 连接（单例，登录态自管理）；一般只取 `isConnected` 做轮询兜底 |
| `usePolling` | `usePolling.ts` | 可组合轮询（start/stop），断线兜底轮询用 |
| `useStatusFormat` | `useStatusFormat.ts` | 回测状态/组合模式等枚举格式化 |
| `useContextMenu` | `useContextMenu.ts` | 右键菜单（全局单例组件配套） |
| `useAsyncAction` | `useAsyncAction.ts` | 提交态收敛（running+toast+成功回调），弹窗/表单提交复用 |
| `useBacktestFormatters` | `useBacktestFormatters.ts` | 回测数值格式化（百分比/小数等） |
| `useChartTheme` | `useChartTheme.ts` | 图表主题（跟随站点深浅色） |
| `useECharts` | `useECharts.ts` | ECharts 实例生命周期（init/ResizeObserver/主题重绘/卸载清理）；动态多图用底层 `createChartController` |
| `createReconnectingSocket` | `reconnectingSocket.ts` | 低层重连 WS 工厂（url 重解析/enabled 闸门），独立于 useWebSocket 单例 |
| `useTheme` | `useTheme.ts` | 站点主题切换 |
