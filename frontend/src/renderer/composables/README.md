# Composables 使用指南

> 目录：`src/renderer/composables/`。本 README 覆盖两块常用机制——可取消请求、服务端事件实时推送；其余家族成员见文末速查表。

## 目录

- [可取消请求（useRequestCancelable）](#可取消请求-composable-使用指南)
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

## 可取消请求 Composable 使用指南

## 概述

`useRequestCancelable` 是基于 `AbortController` 实现的请求取消机制，用于解决组件销毁时请求仍在执行的问题。

## 基本用法

### 1. 单个可取消请求

```typescript
import { useRequestCancelable } from '@/composables/useRequestCancelable'
import * as portfolioApi from '@/api/modules/portfolio'
import { message } from '@/utils/toast'

const { loading, error, execute, cancel } = useRequestCancelable()

async function loadData() {
  await execute(
    (signal) => portfolioApi.list(undefined, { signal }),
    {
      onSuccess: (data) => {
        console.log('数据加载成功:', data)
      },
      onError: (err) => {
        if (err.name !== 'AbortError') {
          message.error(`加载失败: ${err.message}`)
        }
      },
      onFinally: () => {
        console.log('请求完成')
      }
    }
  )
}

// 组件卸载时自动取消请求
// 也可以手动取消
// cancel()
```

### 2. 在组件中使用

```vue
<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useRequestCancelable } from '@/composables/useRequestCancelable'
import * as portfolioApi from '@/api/modules/portfolio'
import { message } from '@/utils/toast'

const portfolios = ref([])

// 使用可取消请求
const { loading, execute: loadPortfolios } = useRequestCancelable()

async function loadData() {
  const result = await loadPortfolios(
    (signal) => portfolioApi.list(undefined, { signal }),
    {
      onSuccess: (data) => {
        portfolios.value = data.data || []
      },
      onError: (error) => {
        if (error.name !== 'AbortError') {
          message.error(`加载失败: ${error.message}`)
        }
      }
    }
  )
}

onMounted(() => {
  loadData()
})

// 组件卸载时，useRequestCancelable 会自动取消进行中的请求
</script>

<template>
  <div>
    <a-spin :spinning="loading">
      <div v-for="portfolio in portfolios" :key="portfolio.uuid">
        {{ portfolio.name }}
      </div>
    </a-spin>
  </div>
</template>
```

### 3. 多个并发可取消请求

```typescript
import { useMultiRequestCancelable } from '@/composables/useRequestCancelable'
import * as portfolioApi from '@/api/modules/portfolio'
import * as backtestApi from '@/api/modules/backtest'

const { execute, cancel, isLoading, getError } = useMultiRequestCancelable()

// 加载组合列表
async function loadPortfolios() {
  await execute(
    'portfolios',
    (signal) => portfolioApi.list(undefined, { signal }),
    {
      onSuccess: (data) => console.log('组合列表:', data)
    }
  )
}

// 加载回测列表
async function loadBacktests() {
  await execute(
    'backtests',
    (signal) => backtestApi.list(undefined, { signal }),
    {
      onSuccess: (data) => console.log('回测列表:', data)
    }
  )
}

// 取消所有请求
function cancelAll() {
  cancel()
}

// 取消特定请求
function cancelPortfolios() {
  cancel('portfolios')
}

// 检查加载状态
const isPortfoliosLoading = isLoading('portfolios')
const backtestError = getError('backtests')
```

## API 接口

### useRequestCancelable

返回值：

- `loading: Ref<boolean>` - 请求加载状态
- `error: Ref<any>` - 错误信息
- `execute<T>(requestFn, options?): Promise<T | null>` - 执行可取消请求
- `cancel(): void` - 取消当前请求

#### execute 参数

- `requestFn: (signal: AbortSignal) => Promise<T>` - 接收 AbortSignal 的请求函数
- `options?: RequestOptions<T>` - 可选的回调配置
  - `onSuccess?: (data: T) => void` - 成功回调
  - `onError?: (error: any) => void` - 错误回调
  - `onFinally?: () => void` - 最终回调

### useMultiRequestCancelable

返回值：

- `loadingStates: Ref<Record<string, boolean>>` - 各请求的加载状态
- `errors: Ref<Record<string, any>>` - 各请求的错误信息
- `execute<T>(key, requestFn, options?): Promise<T | null>` - 执行命名请求
- `cancel(key?: string): void` - 取消请求（不传参数则取消所有）
- `isLoading(key: string): boolean` - 获取指定请求的加载状态
- `getError(key: string): any` - 获取指定请求的错误信息

## 在 Store 中使用

Store 可以使用内置的 AbortController 管理请求取消：

```typescript
import { defineStore } from 'pinia'
import { ref } from 'vue'
import { portfolioApi } from '@/api/modules/portfolio'

export const usePortfolioStore = defineStore('portfolio', () => {
  const loading = ref(false)
  const _abortControllers = ref<Map<string, AbortController>>(new Map())

  function _cancelRequest(key: string) {
    const controller = _abortControllers.value.get(key)
    if (controller) {
      controller.abort()
      _abortControllers.value.delete(key)
    }
  }

  function _createController(key: string): AbortController {
    _cancelRequest(key)
    const controller = new AbortController()
    _abortControllers.value.set(key, controller)
    return controller
  }

  async function fetchPortfolios(params?: { mode?: string }) {
    const controller = _createController('fetchPortfolios')
    loading.value = true
    try {
      const response = await portfolioApi.list(params, {
        signal: controller.signal
      })
      return response
    } catch (e: any) {
      if (e.name !== 'AbortError') {
        throw e
      }
    } finally {
      loading.value = false
      _abortControllers.value.delete('fetchPortfolios')
    }
  }

  function $dispose() {
    // 取消所有进行中的请求
    _abortControllers.value.forEach((controller) => controller.abort())
    _abortControllers.value.clear()
  }

  return {
    loading,
    fetchPortfolios,
    $dispose
  }
})
```

## 注意事项

1. **组件卸载时自动取消**：`useRequestCancelable` 会在组件卸载时自动取消进行中的请求

2. **避免错误提示**：被取消的请求会抛出 `AbortError`，应在 `onError` 中忽略此类错误

3. **请求去重**：同一类型的重复请求会自动取消前一个请求

4. **Store 清理**：使用 Store 时，应在 `$dispose` 方法中清理进行中的请求

5. **兼容性**：所有 API 模块已支持 `signal` 参数，可以安全使用

## 完整示例

```vue
<script setup lang="ts">
import { ref, onMounted, watch } from 'vue'
import { useRequestCancelable } from '@/composables/useRequestCancelable'
import { portfolioApi } from '@/api/modules/portfolio'
import { message } from '@/utils/toast'

const portfolios = ref([])
const filterMode = ref('')

// 使用可取消请求
const { loading, execute: loadPortfolios } = useRequestCancelable()

async function loadData() {
  await loadPortfolios(
    (signal) => portfolioApi.list(
      filterMode.value ? { mode: filterMode.value } : undefined,
      { signal }
    ),
    {
      onSuccess: (response) => {
        portfolios.value = response.data || []
      },
      onError: (error) => {
        if (error.name !== 'AbortError') {
          message.error(`加载失败: ${error.message}`)
        }
      }
    }
  )
}

// 筛选变化时重新加载（会自动取消之前的请求）
watch(filterMode, () => {
  loadData()
})

onMounted(() => {
  loadData()
})
</script>

<template>
  <div>
    <a-radio-group v-model:value="filterMode">
      <a-radio-button value="">全部</a-radio-button>
      <a-radio-button value="BACKTEST">回测</a-radio-button>
      <a-radio-button value="PAPER">模拟</a-radio-button>
      <a-radio-button value="LIVE">实盘</a-radio-button>
    </a-radio-group>

    <a-spin :spinning="loading">
      <div v-for="portfolio in portfolios" :key="portfolio.uuid">
        {{ portfolio.name }}
      </div>
    </a-spin>
  </div>
</template>
```

## 相关文件

- `src/renderer/composables/useRequestCancelable.ts` - Composable 实现
- `src/renderer/api/request.ts` - Axios 请求配置
- `src/renderer/api/modules/*.ts` - 各 API 模块
- `src/renderer/stores/portfolio.ts` - Store 示例

---

## Composables 速查表

| Composable | 文件 | 一句话用途 |
|---|---|---|
| `useServerEvents` | `useServerEvents.ts` | 服务端薄事件订阅/断线补齐/刷新合并/notification toast（ADR-046） |
| `useWebSocket` | `useWebSocket.ts` | 全局通知 WS 连接（单例，登录态自管理）；一般只取 `isConnected` 做轮询兜底 |
| `useRequestCancelable` / `useMultiRequestCancelable` | `useRequestCancelable.ts` | AbortController 请求取消（见上文） |
| `usePolling` | `usePolling.ts` | 可组合轮询（start/stop），断线兜底轮询用 |
| `useListPage` | `useListPage.ts` | 列表页通用逻辑（搜索/筛选/分页） |
| `useStatusFormat` | `useStatusFormat.ts` | 回测状态/组合模式等枚举格式化 |
| `useLoading` | `useLoading.ts` | 多键 loading 状态 |
| `useErrorHandler` | `useErrorHandler.ts` | 错误处理 |
| `useContextMenu` | `useContextMenu.ts` | 右键菜单（全局单例组件配套） |
| `useBacktestFormatters` | `useBacktestFormatters.ts` | 回测数值格式化（百分比/小数等） |
| `useChartTheme` | `useChartTheme.ts` | 图表主题（跟随站点深浅色） |
| `useTheme` | `useTheme.ts` | 站点主题切换 |
| `useTable` | `useTable.ts` | 表格通用逻辑 |
