# 请求取消快速参考

## 常用模式

### 1. 基本请求模式

```typescript
// 导入
import { useRequestCancelable } from '@/composables/useRequestCancelable'

// 使用
const { loading, execute, cancel } = useRequestCancelable()

// 发起请求
await execute(
  (signal) => api.method(params, { signal }),
  {
    onSuccess: (data) => { /* 成功处理 */ },
    onError: (error) => {
      if (error.name !== 'AbortError') {
        /* 错误处理 */
      }
    }
  }
)
```

### 2. 组件中使用

```vue
<script setup lang="ts">
import { onMounted } from 'vue'
import { useRequestCancelable } from '@/composables/useRequestCancelable'
import { portfolioApi } from '@/api/modules/portfolio'

const { loading, execute: loadData } = useRequestCancelable()

onMounted(() => {
  loadData(
    (signal) => portfolioApi.list(undefined, { signal }),
    { onSuccess: (data) => console.log(data) }
  )
})
</script>

<template>
  <a-spin :spinning="loading">内容</a-spin>
</template>
```

### 3. 搜索/筛选模式

```typescript
const { loading, execute } = useRequestCancelable()

watch(searchQuery, () => {
  execute(
    (signal) => api.search({ query: searchQuery.value }, { signal }),
    { onSuccess: (data) => results.value = data }
  )
}, { debounce: 300 })
```

### 4. 多请求管理

```typescript
import { useMultiRequestCancelable } from '@/composables/useRequestCancelable'

const { execute, cancel, isLoading } = useMultiRequestCancelable()

// 加载组合
execute('portfolios', (signal) => portfolioApi.list(undefined, { signal }))
// 加载回测
execute('backtests', (signal) => backtestApi.list(undefined, { signal }))

// 取消特定请求
cancel('portfolios')

// 取消所有请求
cancel()

// 检查状态
const loading = isLoading('portfolios')
```

## API 接口

### useRequestCancelable

```typescript
const {
  loading: Ref<boolean>,      // 加载状态
  error: Ref<any>,            // 错误信息
  execute,                    // 执行请求
  cancel                      // 取消请求
} = useRequestCancelable()
```

### execute 方法

```typescript
await execute<T>(
  requestFn: (signal: AbortSignal) => Promise<T>,
  options?: {
    onSuccess?: (data: T) => void,
    onError?: (error: any) => void,
    onFinally?: () => void
  }
): Promise<T | null>
```

## 错误处理

### 忽略取消错误

```typescript
onError: (error) => {
  if (error.name !== 'AbortError') {
    message.error(`请求失败: ${error.message}`)
  }
}
```

### 使用工具函数

```typescript
import { isAbortError } from '@/types/api-request'

onError: (error) => {
  if (!isAbortError(error)) {
    message.error(`请求失败: ${error.message}`)
  }
}
```

## 所有 API 已支持 signal

```typescript
// Portfolio
portfolioApi.list(params, { signal })
portfolioApi.get(uuid, { signal })
portfolioApi.create(data, { signal })
portfolioApi.update(uuid, data, { signal })
portfolioApi.delete(uuid, { signal })

// Backtest
backtestApi.list(params, { signal })
backtestApi.get(uuid, { signal })
backtestApi.create(data, { signal })
// ... 其他方法

// Components
componentsApi.list(params, { signal })
componentsApi.get(uuid, { signal })
// ... 其他方法

// NodeGraph
nodeGraphApi.list(params, { signal })
nodeGraphApi.get(uuid, { signal })
// ... 其他方法
```

## 注意事项

1. **自动清理**: 组件卸载时自动取消请求
2. **请求去重**: 新请求会自动取消旧请求
3. **错误判断**: 使用 `error.name === 'AbortError'` 或 `isAbortError(error)`
4. **Store 清理**: 在 `$dispose()` 中取消请求

## 文件位置

- Composable: `/home/kaoru/Ginkgo/web-ui/src/composables/useRequestCancelable.ts`
- 类型定义: `/home/kaoru/Ginkgo/web-ui/src/types/api-request.ts`
- 使用指南: `/home/kaoru/Ginkgo/web-ui/src/composables/README.md`
- 示例组件: `/home/kaoru/Ginkgo/web-ui/src/examples/CancelableRequestExample.vue`
