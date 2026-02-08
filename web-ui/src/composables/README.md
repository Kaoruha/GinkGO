# 可取消请求 Composable 使用指南

## 概述

`useRequestCancelable` 是基于 `AbortController` 实现的请求取消机制，用于解决组件销毁时请求仍在执行的问题。

## 基本用法

### 1. 单个可取消请求

```typescript
import { useRequestCancelable } from '@/composables/useRequestCancelable'
import * as portfolioApi from '@/api/modules/portfolio'
import { message } from 'ant-design-vue'

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
import { message } from 'ant-design-vue'

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
import { message } from 'ant-design-vue'

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

- `/home/kaoru/Ginkgo/web-ui/src/composables/useRequestCancelable.ts` - Composable 实现
- `/home/kaoru/Ginkgo/web-ui/src/api/request.ts` - Axios 请求配置
- `/home/kaoru/Ginkgo/web-ui/src/api/modules/*.ts` - 各 API 模块
- `/home/kaoru/Ginkgo/web-ui/src/stores/portfolio.ts` - Store 示例
