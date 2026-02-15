# AbortController 请求取消机制实现总结

## 概述

为 Ginkgo Web UI 项目实现了基于 `AbortController` 的请求取消机制，解决了组件销毁时请求仍在执行的问题。

## 实现的文件

### 1. 核心 Composable

**文件**: `/home/kaoru/Ginkgo/web-ui/src/composables/useRequestCancelable.ts`

提供了两个 Composable：

- `useRequestCancelable()` - 单个可取消请求
- `useMultiRequestCancelable()` - 多个并发可取消请求

**主要功能**：
- 自动管理 AbortController 生命周期
- 组件卸载时自动取消请求
- 支持成功、失败、最终回调
- 请求去重（新请求会自动取消旧请求）

### 2. 类型定义

**文件**: `/home/kaoru/Ginkgo/web-ui/src/types/api-request.ts`

统一的类型定义：

- `RequestOptions` - 基础请求选项
- `PageParams` - 分页参数
- `PaginatedResponse<T>` - 分页响应
- `APIResponse<T>` - API 响应
- `RequestError` - 请求错误
- `isAbortError()` - 判断是否为取消错误
- `createAbortError()` - 创建取消错误

### 3. 请求拦截器

**文件**: `/home/kaoru/Ginkgo/web-ui/src/api/request.ts`

更新了响应拦截器：
- 忽略 `AbortError` 的错误提示
- 支持原生 AbortSignal（Axios 已内置支持）

### 4. API 模块更新

所有 API 模块已添加 `signal` 参数支持：

- `/home/kaoru/Ginkgo/web-ui/src/api/modules/portfolio.ts`
- `/home/kaoru/Ginkgo/web-ui/src/api/modules/backtest.ts`
- `/home/kaoru/Ginkgo/web-ui/src/api/modules/components.ts`
- `/home/kaoru/Ginkgo/web-ui/src/api/modules/nodeGraph.ts`
- `/home/kaoru/Ginkgo/web-ui/src/api/modules/auth.ts`
- `/home/kaoru/Ginkgo/web-ui/src/api/modules/settings.ts`

### 5. Store 更新

**文件**: `/home/kaoru/Ginkgo/web-ui/src/stores/portfolio.ts`

添加了请求取消功能：
- 内置 AbortController 管理
- `$dispose()` 方法用于清理
- `cancelAllRequests()` 方法取消所有请求

### 6. 文档和示例

- `/home/kaoru/Ginkgo/web-ui/src/composables/README.md` - 使用指南
- `/home/kaoru/Ginkgo/web-ui/src/examples/CancelableRequestExample.vue` - 示例组件
- `/home/kaoru/Ginkgo/web-ui/src/composables/__tests__/useRequestCancelable.spec.ts` - 单元测试

## 使用方式

### 基本用法

```typescript
import { useRequestCancelable } from '@/composables/useRequestCancelable'

const { loading, execute, cancel } = useRequestCancelable()

async function loadData() {
  await execute(
    (signal) => portfolioApi.list(undefined, { signal }),
    {
      onSuccess: (data) => { /* ... */ },
      onError: (error) => {
        if (error.name !== 'AbortError') {
          // 处理错误
        }
      }
    }
  )
}
```

### 在组件中使用

```vue
<script setup lang="ts">
import { onMounted } from 'vue'
import { useRequestCancelable } from '@/composables/useRequestCancelable'
import { portfolioApi } from '@/api/modules/portfolio'

const { loading, execute: loadPortfolios } = useRequestCancelable()

onMounted(() => {
  loadPortfolios((signal) => portfolioApi.list(undefined, { signal }), {
    onSuccess: (data) => { /* ... */ }
  })
})

// 组件卸载时自动取消请求
</script>
```

### 在 Store 中使用

```typescript
import { defineStore } from 'pinia'
import { ref } from 'vue'

export const usePortfolioStore = defineStore('portfolio', () => {
  const _abortControllers = ref<Map<string, AbortController>>(new Map())

  async function fetchPortfolios(params?: { mode?: string }) {
    const controller = new AbortController()
    _abortControllers.value.set('fetchPortfolios', controller)

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
      _abortControllers.value.delete('fetchPortfolios')
    }
  }

  function $dispose() {
    _abortControllers.value.forEach((controller) => controller.abort())
    _abortControllers.value.clear()
  }

  return { fetchPortfolios, $dispose }
})
```

## 技术特点

1. **自动管理**: 组件卸载时自动取消请求，无需手动处理
2. **类型安全**: 完整的 TypeScript 类型支持
3. **请求去重**: 同类请求会自动取消之前的请求
4. **错误处理**: 区分取消错误和其他错误
5. **灵活性**: 支持单个和多个并发请求管理

## 兼容性

- Axios 原生支持 AbortSignal（v0.22.0+）
- 所有现代浏览器支持 AbortController
- Node.js v15.0.0+ 支持 AbortController

## 注意事项

1. 组件卸载时，useRequestCancelable 会自动取消进行中的请求
2. 被取消的请求会抛出 AbortError，应在 onError 中忽略
3. Store 使用时应在 $dispose 方法中清理进行中的请求
4. 所有 API 模块已支持 signal 参数，可安全使用

## 测试

提供了完整的单元测试，覆盖以下场景：
- 基本请求功能
- 请求取消功能
- 成功/失败回调
- 多请求管理
- 请求去重

测试文件: `/home/kaoru/Ginkgo/web-ui/src/composables/__tests__/useRequestCancelable.spec.ts`
