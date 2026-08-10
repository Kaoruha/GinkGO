# Web-UI 组件使用指南

## 📚 Table of Contents

1. [通用组件](#通用组件)
   - [数据展示](#数据展示)
   - [业务组件](#业务组件)
   - [表单组件](#表单组件)
2. [Composables](#composables)
3. [API 模块](#api-模块)
4. [使用示例](#使用示例)

## 📊 通用组件

### 数据展示

#### DataTable - 通用表格
```vue
<DataTable
  :columns="columns"
  :data-source="items"
  :loading="loading"
  :page="page"
  :pageSize="20"
  :total="total"
  @refresh="handleRefresh"
/>
```

**特性：**
- ✅ 分页、筛选、排序
- ✅ 自定义工具栏插槽
- ✅ 行展开插槽

### StatisticCard - 统计卡片
```vue
<StatisticCard
  title="总资产"
  :value="1234567.89"
  :precision="2"
  prefix="¥"
  suffix="同比增长 12%"
  :trend="up"
  :trend-icon="ArrowUpOutlined"
/>
```

**特性：**
- ✅ 趋势显示
- ✅ 前缀后缀
- ✅ 多尺寸支持

## 📊 业务组件

### FactorSelector - 因子选择器
```vue
<FactorSelector
  v-model:selected="selectedFactors"
  :factors="factors"
  @update:selected="handleFactorsUpdate"
/>
```

### DateRangePicker - 日期范围选择
```vue
<DateRangePicker
  v-model:start-date="startDate"
  v-model:end-date="endDate"
  :quick-select="recent"
  @confirm="handleDateConfirm"
/>
```

## 📊 Composables

### useCrudStore - 通用 CRUD Store
```typescript
import { useCrudStore } from '@/composables/useCrudStore'

const { items, loading, fetchList, create, update, remove } = useCrudStore(
  '/api/modules/business/backtest',
  { itemsKey: 'tasks' }
)

await fetchList({ page: 1, pageSize: 20 })
await create({ name: '新策略', portfolio_uuids: ['uuid-1'] })
await update(uuid, { name: '更新策略' })
await remove(uuid)
```

### useApiError - API 错误处理
```typescript
import { useApiError } from '@/composables/useApiError'

const { handleError } = useApiError()

try {
  await apiCall()
} catch (error) {
  handleError(error, '操作失败')
}
```

## 🎯 迁移示例

### 从旧架构迁移

**Before (旧代码):**
```typescript
// 直接 API 调用
import { createBacktest } from '@/api/modules/backtest'
await createBacktest({ ... })
```

**After (新架构):**
```typescript
// 使用通用 Store
import { useCrudStore } from '@/composables/useCrudStore'
const { create } = useCrudStore('/api/modules/business/backtest', { itemsKey: 'tasks' })
await create({ name: '新策略' })
```

## 📐 最佳实践

1. **单一职责** - 每个组件/函数只做一件事
2. **类型安全** - 使用 TypeScript 严格模式
3. **可测试性** - composables 可独立测试
4. **响应式数据** - 使用 ref/computed 自动追踪
5. **错误边界** - 统一的错误处理和用户提示
