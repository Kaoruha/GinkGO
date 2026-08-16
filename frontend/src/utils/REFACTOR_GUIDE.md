# 前端代码重构指南

## 📦 新创建的公共模块

### 1. 数据格式化工具 (`@/utils/formatters.ts`)
**用途**: 统一所有数据格式化逻辑

**示例用法**:
```typescript
import { formatPercent, formatNumber, formatDateTime, getStateLabel } from '@/utils/formatters'

// 在组件中使用
const percentage = formatPercent(0.0123) // "1.23%"
const amount = formatNumber(1234.56, 2) // "1234.56"
const time = formatDateTime("2024-01-01T12:00:00") // "2024-01-01 12:00:00"
const statusText = getStateLabel('RUNNING') // "运行中"
```

### 2. 错误处理工具 (`@/utils/errorHandler.ts`)
**用途**: 统一错误消息提取和处理逻辑

**示例用法**:
```typescript
import { handleApiError, getErrorType, getFriendlyErrorMessage } from '@/utils/errorHandler'

try {
  await apiCall()
} catch (e) {
  const errorMessage = handleApiError(e, '操作失败')
  message.error(errorMessage)

  // 或者使用友好错误提示
  const errorType = getErrorType(e)
  const friendlyMsg = getFriendlyErrorMessage(errorType)
  message.error(friendlyMsg)
}
```

### 3. 任务状态工具 (`@/utils/taskState.ts`)
**用途**: 统一任务状态判断逻辑

**示例用法**:
```typescript
import {
  isTaskActive,
  isTaskTerminal,
  isTaskStoppable,
  getStateColor
} from '@/utils/taskState'

// 在组件中使用
const canStop = isTaskStoppable(task.state)
const isFinished = isTaskTerminal(task.state)
const statusColor = getStateColor(task.state)
```

### 4. 批量操作工具 (`@/utils/batchOperation.ts`)
**用途**: 统一批量操作处理逻辑

**示例用法**:
```typescript
import { executeBatchOperation, formatBatchResultMessage } from '@/utils/batchOperation'

// 在store中使用
async function batchStart(uuids: string[]) {
  const result = await executeBatchOperation(
    uuids,
    startTask,
    id => id,
    { concurrency: 5 } // 可选：限制并发数
  )

  const message = formatBatchResultMessage(result, '启动')
  return result
}
```

### 5. API调用Composable (`@/composables/useApiCall.ts`)
**用途**: 统一异步调用和状态管理

**示例用法**:
```typescript
import { useApiCall } from '@/composables/useApiCall'

// 在组件中
const { data, loading, error, execute } = useApiCall()

async function fetchTasks() {
  await execute(
    () => api.backtest.list(),
    (err) => message.error(err.message) // 可选的错误处理
  )
}
```

### 6. WebSocket处理Composable (`@/composables/useBacktestWebSocket.ts`)
**用途**: 统一实时订阅和断线处理逻辑

**示例用法**:
```typescript
import { useBacktestWebSocket } from '@/composables/useBacktestWebSocket'

const { isConnected, setupSubscription, setupPolling } = useBacktestWebSocket({
  getTaskId: () => currentTask.value?.uuid || null,
  onMessage: (data) => {
    // 更新任务数据
    updateTaskData(data)
  },
  enablePolling: true,
  pollingInterval: 5000,
  pollingFetch: fetchTaskDetail
})

// 设置订阅
setupSubscription(subscribe)
setupPolling()
```

### 7. 无限滚动Composable (`@/composables/useInfiniteScroll.ts`)
**用途**: 统一滚动加载逻辑

**示例用法**:
```typescript
import { useInfiniteScroll } from '@/composables/useInfiniteScroll'

const { triggerRef, setupObserver } = useInfiniteScroll({
  loadMore: () => fetchMoreLogs(),
  hasMore: computed(() => logs.hasMore),
  loading: computed(() => logs.loading)
})

// 在模板中
<div ref="triggerRef"></div>
```

### 8. 统一类型定义 (`@/types/backtest.ts`)
**用途**: 统一回测相关类型导入

**示例用法**:
```typescript
// 替代直接从API层导入
import type { BacktestTask, BacktestTaskStatus } from '@/types/backtest'

// 而不是
import type { BacktestTask } from '@/api/modules/backtest'
```

## 🔧 现有代码重构步骤

### Step 1: 更新 BacktestListPage.vue

**替换格式化函数**:
```typescript
// 删除这些内联函数
// const formatPct = (v: any) => ...
// const formatNum = (v: any, d: number) => ...
// const formatTime = (t: string) => ...

// 导入统一工具
import { formatPercent, formatNumber, formatDateTime, getStateLabel } from '@/utils/formatters'
```

**替换API调用**:
```typescript
import { useApiCall } from '@/composables/useApiCall'

const { loading, execute } = useApiCall()

// 简化的fetchTasks函数
async function fetchTasks() {
  await execute(() => api.backtest.list({ page: page.value, page_size: page_size.value }))
}
```

**替换WebSocket逻辑**:
```typescript
import { useBacktestWebSocket } from '@/composables/useBacktestWebSocket'

const { setupSubscription, setupPolling } = useBacktestWebSocket({
  getTaskId: () => null, // 列表页监听所有任务
  onMessage: handleTaskUpdate,
  enablePolling: true,
  pollingInterval: 5000,
  pollingFetch: fetchTasks
})
```

### Step 2: 更新 BacktestDetailPage.vue

**替换重复导入**:
```typescript
// 删除这些导入
// import { formatShortDate, directionLabel, directionColor, ... } from '@/composables/useBacktestFormatters'

// 统一导入
import {
  formatShortDate,
  getDirectionLabel,
  getDirectionColor,
  formatAnalyzerData,
  getAnalyzerColor,
  formatLogTime
} from '@/utils/formatters'
```

**替换状态判断**:
```typescript
import { isTaskActive, isTaskTerminal, isTaskStoppable } from '@/utils/taskState'

// 替换这些判断
// const running = record.state === 'RUNNING' || record.state === 'PENDING'
const running = isTaskActive(record.state)
```

### Step 3: 更新 stores/backtest.ts

**替换批量操作逻辑**:
```typescript
import { executeBatchOperation, formatBatchResultMessage } from '@/utils/batchOperation'

// 简化的批量启动函数
async function batchStart(uuids: string[]) {
  batchOperationLoading.value = true
  const result = await executeBatchOperation(uuids, startTask, id => id)
  batchOperationLoading.value = false
  return result
}
```

### Step 4: 更新 Dashboard.vue

**替换状态标签**:
```typescript
import { getStateLabel, getStateColor } from '@/utils/formatters'

// 替换内联的状态映射函数
function stateLabel(state: string | number): string {
  return getStateLabel(state)
}
```

## 📊 预期效果

### 代码减少量估算:
- **BacktestListPage.vue**: 减少 ~150 行代码 (-30%)
- **BacktestDetailPage.vue**: 减少 ~120 行代码 (-25%)
- **stores/backtest.ts**: 减少 ~80 行代码 (-35%)
- **Dashboard.vue**: 减少 ~40 行代码 (-20%)

### 维护性提升:
- ✅ 格式化规则统一修改
- ✅ 错误处理逻辑集中
- ✅ WebSocket策略统一调整
- ✅ 新增状态只需修改一处

### 测试覆盖率:
- ✅ 工具函数可独立单元测试
- ✅ Composable逻辑可单独测试
- ✅ 减少组件级测试复杂度

## 🚀 迁移优先级

### 第一阶段 (高优先级):
1. 创建格式化工具并替换所有内联格式化函数
2. 创建错误处理工具并统一错误提示
3. 替换API调用模式为useApiCall

### 第二阶段 (中优先级):
4. 重构WebSocket订阅逻辑
5. 统一批量操作处理

### 第三阶段 (低优先级):
6. 优化状态判断逻辑
7. 统一类型导入路径

## 💡 使用建议

1. **渐进式迁移**: 不需要一次性重构所有代码，可以逐个文件迁移
2. **保持兼容**: 新旧代码可以共存，逐步替换
3. **测试验证**: 每次重构后都要验证功能正常
4. **团队协作**: 告知团队成员使用新的公共模块

这些公共模块不仅减少了代码冗余，还提高了代码的一致性和可维护性！