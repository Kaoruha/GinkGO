# 迁移到可取消请求

## 概述

本文档指导如何将现有的组件迁移到使用可取消请求机制。

## 迁移步骤

### 1. 识别需要迁移的组件

查找包含以下特征的组件：

```vue
<script setup lang="ts">
import { onMounted } from 'vue'

const loading = ref(false)
const data = ref([])

onMounted(() => {
  loadData()  // ← 组件销毁后请求仍继续
})

async function loadData() {
  loading.value = true
  try {
    const response = await api.getData()  // ← 无法取消
    data.value = response.data
  } finally {
    loading.value = false
  }
}
</script>
```

### 2. 基本迁移

**之前**:
```vue
<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { portfolioApi } from '@/api/modules/portfolio'

const loading = ref(false)
const portfolios = ref([])

async function loadData() {
  loading.value = true
  try {
    const response = await portfolioApi.list()
    portfolios.value = response.data
  } finally {
    loading.value = false
  }
}

onMounted(() => {
  loadData()
})
</script>
```

**之后**:
```vue
<script setup lang="ts">
import { onMounted } from 'vue'
import { useRequestCancelable } from '@/composables/useRequestCancelable'
import { portfolioApi } from '@/api/modules/portfolio'

const portfolios = ref([])

// 使用可取消请求
const { loading, execute: loadData } = useRequestCancelable()

onMounted(() => {
  loadData(
    (signal) => portfolioApi.list(undefined, { signal }),
    {
      onSuccess: (response) => {
        portfolios.value = response.data
      }
    }
  )
})
</script>
```

### 3. 带错误处理的迁移

**之前**:
```typescript
async function loadData() {
  loading.value = true
  try {
    const response = await portfolioApi.list()
    portfolios.value = response.data
  } catch (error) {
    message.error(`加载失败: ${error.message}`)
  } finally {
    loading.value = false
  }
}
```

**之后**:
```typescript
const { loading, execute: loadData } = useRequestCancelable()

await loadData(
  (signal) => portfolioApi.list(undefined, { signal }),
  {
    onSuccess: (response) => {
      portfolios.value = response.data
    },
    onError: (error) => {
      if (error.name !== 'AbortError') {
        message.error(`加载失败: ${error.message}`)
      }
    }
  }
)
```

### 4. 搜索/筛选组件迁移

**之前**:
```typescript
const searchQuery = ref('')

watch(searchQuery, async () => {
  loading.value = true
  try {
    const response = await portfolioApi.list({ search: searchQuery.value })
    portfolios.value = response.data
  } finally {
    loading.value = false
  }
})
```

**之后**:
```typescript
const { loading, execute: searchPortfolios } = useRequestCancelable()

watch(searchQuery, () => {
  searchPortfolios(
    (signal) => portfolioApi.list({ search: searchQuery.value }, { signal }),
    {
      onSuccess: (response) => {
        portfolios.value = response.data
      }
    }
  )
})

// 新请求会自动取消旧请求，避免竞态条件
```

### 5. Store 迁移

**之前**:
```typescript
export const usePortfolioStore = defineStore('portfolio', () => {
  const loading = ref(false)
  const portfolios = ref([])

  async function fetchPortfolios() {
    loading.value = true
    try {
      const response = await portfolioApi.list()
      portfolios.value = response.data
    } finally {
      loading.value = false
    }
  }

  return { loading, portfolios, fetchPortfolios }
})
```

**之后**:
```typescript
export const usePortfolioStore = defineStore('portfolio', () => {
  const loading = ref(false)
  const portfolios = ref([])
  const _abortControllers = ref<Map<string, AbortController>>(new Map())

  async function fetchPortfolios() {
    const controller = new AbortController()
    _abortControllers.value.set('fetchPortfolios', controller)

    loading.value = true
    try {
      const response = await portfolioApi.list(undefined, {
        signal: controller.signal
      })
      portfolios.value = response.data
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
    _abortControllers.value.forEach((controller) => controller.abort())
    _abortControllers.value.clear()
  }

  return { loading, portfolios, fetchPortfolios, $dispose }
})
```

## 常见问题

### Q1: 如何判断错误是否为取消操作？

```typescript
// 方法1: 检查错误名称
if (error.name !== 'AbortError') {
  // 处理真实错误
}

// 方法2: 使用工具函数
import { isAbortError } from '@/types/api-request'

if (!isAbortError(error)) {
  // 处理真实错误
}
```

### Q2: 如何手动取消请求？

```typescript
const { execute, cancel } = useRequestCancelable()

// 发起请求
execute((signal) => api.getData({ signal }))

// 手动取消
cancel()
```

### Q3: 如何同时管理多个请求？

```typescript
import { useMultiRequestCancelable } from '@/composables/useRequestCancelable'

const { execute, cancel } = useMultiRequestCancelable()

// 发起多个请求
execute('portfolios', (signal) => portfolioApi.list(undefined, { signal }))
execute('backtests', (signal) => backtestApi.list(undefined, { signal }))

// 取消所有请求
cancel()

// 取消特定请求
cancel('portfolios')
```

### Q4: 组件卸载时需要手动清理吗？

不需要。`useRequestCancelable` 会在组件卸载时自动清理。

```typescript
// 自动清理，无需手动处理
const { execute } = useRequestCancelable()
```

## 迁移检查清单

- [ ] 导入 `useRequestCancelable`
- [ ] 使用 `execute` 方法包装 API 调用
- [ ] 传递 `signal` 参数到 API 方法
- [ ] 添加 `onError` 回调并检查 `AbortError`
- [ ] 移除手动的 loading 状态管理（使用返回的 loading）
- [ ] 测试组件卸载时的请求取消
- [ ] 测试快速切换时的请求去重

## 示例项目

查看完整示例：
- `/home/kaoru/Ginkgo/web-ui/src/examples/CancelableRequestExample.vue`

## 相关文档

- 使用指南: `/home/kaoru/Ginkgo/web-ui/src/composables/README.md`
- 快速参考: `/home/kaoru/Ginkgo/web-ui/docs/abortcontroller-quick-reference.md`
- 实现总结: `/home/kaoru/Ginkgo/web-ui/docs/abortcontroller-implementation.md`
