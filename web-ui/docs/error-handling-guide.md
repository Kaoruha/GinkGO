# 错误处理使用指南

## 概述

Ginkgo Web UI 提供了统一的错误处理机制，确保用户在所有操作中获得一致的错误提示体验。

## 核心组件

### 1. 错误处理器 (`/src/utils/errorHandler.ts`)

提供基础的错误处理功能：

- `handleApiError(error, showMessage?, customMessage?)` - 统一的 API 错误处理
- `withErrorHandling(fn, errorCallback?)` - 包装异步函数自动处理错误
- `extractErrorInfo(error)` - 从 Axios 错误中提取标准化错误信息
- `createApiError(code, message, details?)` - 创建标准 API 错误对象

### 2. 错误处理 Composable (`/src/composables/useErrorHandler.ts`)

为 Vue 组件提供响应式的错误处理：

- `useErrorHandler()` - 基础错误处理
- `useBatchErrorHandler(count)` - 批量操作错误处理
- `useFormErrorHandler()` - 表单提交错误处理

## 使用方法

### 基础使用

```typescript
import { useErrorHandler } from '@/composables/useErrorHandler'

const { error, loading, execute, clearError } = useErrorHandler()

async function loadData() {
  const result = await execute(async () => {
    return await portfolioApi.list()
  })

  if (result) {
    // 处理成功结果
    console.log('数据加载成功', result)
  } else {
    // 错误已被自动处理（显示错误消息）
    console.log('数据加载失败', error.value)
  }
}
```

### 表单提交

```typescript
import { useFormErrorHandler } from '@/composables/useErrorHandler'

const { loading, submit, reset } = useFormErrorHandler()

async function handleSubmit() {
  await formRef.value.validate()

  const result = await submit(async () => {
    return await portfolioApi.create(formData)
  })

  if (result) {
    message.success('创建成功')
    reset()
  }
}
```

### 批量操作

```typescript
import { useBatchErrorHandler } from '@/composables/useErrorHandler'

const { errors, loading, executeAll, clearErrors } = useBatchErrorHandler(3)

const results = await executeAll([
  () => portfolioApi.get(uuid1),
  () => portfolioApi.get(uuid2),
  () => portfolioApi.get(uuid3)
])

// 检查结果
results.forEach((result, index) => {
  if (errors.value[index]) {
    console.error(`操作 ${index} 失败`, errors.value[index])
  } else if (result) {
    console.log(`操作 ${index} 成功`, result)
  }
})
```

### 直接错误处理

```typescript
import { handleApiError } from '@/utils/errorHandler'

try {
  await someApiCall()
} catch (error) {
  handleApiError(error) // 自动显示合适的错误消息
}
```

### 自定义错误消息

```typescript
import { handleApiError } from '@/utils/errorHandler'

try {
  await someApiCall()
} catch (error) {
  handleApiError(error, true, '自定义错误消息')
}
```

### 包装异步函数

```typescript
import { withErrorHandling } from '@/utils/errorHandler'

const safeApiCall = withErrorHandling(async () => {
  return await portfolioApi.get(uuid)
})

// 使用时自动处理错误
const result = await safeApiCall()
```

## 错误码

系统定义了标准的错误码：

```typescript
enum ErrorCode {
  // 网络错误
  NETWORK_ERROR = 'NETWORK_ERROR',
  TIMEOUT_ERROR = 'TIMEOUT_ERROR',

  // 客户端错误
  NOT_FOUND = 'NOT_FOUND',
  VALIDATION_ERROR = 'VALIDATION_ERROR',
  UNAUTHORIZED = 'UNAUTHORIZED',
  FORBIDDEN = 'FORBIDDEN',

  // 服务端错误
  INTERNAL_ERROR = 'INTERNAL_ERROR',
  SERVICE_UNAVAILABLE = 'SERVICE_UNAVAILABLE',

  // 业务错误
  BUSINESS_ERROR = 'BUSINESS_ERROR',
  CONFLICT_ERROR = 'CONFLICT_ERROR',
}
```

每个错误码都有对应的用户友好的错误消息，并且根据错误严重程度显示不同的提示类型（info/warning/error）。

## API 集成

### API 响应格式

API 响应应遵循以下格式：

```typescript
// 成功响应
{
  success: true,
  data: { ... }
}

// 错误响应
{
  success: false,
  error: 'ERROR_CODE',
  message: '错误描述'
}
```

### 后端错误码

后端应返回标准错误码，前端会自动映射为用户友好的错误消息。

```json
{
  "success": false,
  "error": "VALIDATION_ERROR",
  "message": "输入数据格式错误"
}
```

## 最佳实践

1. **始终使用统一的错误处理** - 不要在组件中直接使用 `message.error()`
2. **使用 Composable** - 在 Vue 组件中使用 `useErrorHandler` 或相关 composable
3. **区分严重程度** - 错误会根据严重程度显示不同类型的提示
4. **处理特殊情况** - AbortError（取消请求）会被自动忽略，不会显示错误消息
5. **登录跳转** - UNAUTHORIZED 错误会自动跳转到登录页

## 迁移指南

### 旧代码

```typescript
try {
  await portfolioApi.delete(uuid)
  message.success('删除成功')
} catch (error: any) {
  message.error(`删除失败: ${error.message}`)
}
```

### 新代码

```typescript
const { execute } = useErrorHandler()

const result = await execute(async () => {
  return await portfolioApi.delete(uuid)
})

if (result) {
  message.success('删除成功')
}
// 错误已自动处理
```

## 相关文件

- `/src/utils/errorHandler.ts` - 核心错误处理逻辑
- `/src/composables/useErrorHandler.ts` - Vue 错误处理 composable
- `/src/api/request.ts` - Axios 拦截器（错误标准化）
- `/src/types/api.ts` - API 类型定义
