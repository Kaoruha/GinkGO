# Web-UI 架构重构总结

## ✅ 已完成的重构模块

### 1. 核心请求模块 (`api/modules/core/`)
- Axios 统一配置
- 请求/响应拦截器
- Token 自动注入
- 错误统一处理

### 2. 通用 API 方法 (`api/modules/common.ts`)
- GET/POST/PUT/DELETE 封装
- 文件上传支持

### 3. 通用类型定义 (`api/types/common.ts`)
- PaginationParams、PaginatedResponse
- APIResponse 通用格式

### 4. 业务 API 模块 (`api/modules/business/`)
- **research.ts** - 因子研究 API (IC分析、分层回测、因子对比等)
- **backtest.ts** - 回测任务 API (创建、启动、停止、删除)
- **portfolio.ts** - 投资组合 API (CRUD、组件管理)

### 5. 可复用组件 (`components/`)
- **DataTable.vue** - 通用表格（分页、筛选、排序）
- **StatisticCard.vue** - 统计卡片（趋势、前缀、后缀）
- **ProForm.vue** - 增强表单（验证、布局、提交）

### 6. 工具函数 (`composables/`)
- **useApiError.ts** - 统一 API 错误处理
- **useCrudStore.ts** - 通用 CRUD Store 模式

## 📖 重构使用指南

### 在组件中使用通用 Store

```typescript
import { useCrudStore } from '@/composables/useCrudStore'
import { getBacktestList, createBacktest } from '@/api/modules/business/backtest'

const { items, loading, fetchList, create } = useCrudStore(
  getBacktestList,
  { itemsKey: 'tasks' }
)

// 查询数据
await fetchList({ page: 1, pageSize: 20 })

// 创建项目
await create({ name: '测试策略', portfolio_uuids: ['uuid-1'] })
```

### 使用通用表格组件

```vue
<DataTable
  :columns="columns"
  :data-source="items"
  :loading="loading"
  :page="pagination.page"
  :pageSize="pagination.pageSize"
  :total="pagination.total"
  @refresh="fetchList"
>
  <template #toolbar>
    <a-button type="primary" @click="showCreate">新建</a-button>
  </template>
</DataTable>
```

### 使用 API 错误处理

```typescript
import { useApiError } from '@/composables/useApiError'

const { handleError } = useApiError()

try {
  await apiCall()
} catch (error) {
  handleError(error, '操作失败')
}
```

## 🎯 下一步工作

1. 更新现有页面使用新的 API 模块
2. 替换重复的表格逻辑为 DataTable 组件
3. 统一表单验证使用 ProForm 组件
4. 更新所有 Store 使用统一的 Store 模式
