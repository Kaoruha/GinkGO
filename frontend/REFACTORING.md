# Web-UI 架构重构说明

## 📦 重构目标

1. **提高代码复用性** - 减少重复代码
2. **统一 API 请求封装** - 规范错误处理
3. **组件化开发** - 提取通用组件
4. **优化状态管理** - 简化数据流

## 📂 新增目录结构

```
src/
├── api/
│   ├── modules/
│   │   ├── core/           # 核心请求封装 ✅
│   │   ├── common.ts       # 通用请求方法 ✅
│   │   └── business/      # 业务 API 模块 ✅
│   └── types/
│       └── common.ts      # 通用类型定义 ✅
├── components/
│   ├── data/            # 数据展示组件 ✅
│   │   ├── DataTable.vue      # 通用表格
│   │   └── StatisticCard.vue # 统计卡片
│   └── form/            # 表单组件 ✅
│       └── ProForm.vue        # 增强表单
└── composables/
    └── useApiError.ts    # API 错误处理 ✅
```

## 📖 使用示例

### 1. API 请求封装

```typescript
// 使用新的通用 API
import { getBacktestList, createBacktest } from '@/api/modules/business/backtest'

// 分页查询
const result = await getBacktestList({
  page: 1,
  pageSize: 20,
  state: 'COMPLETED'
})

// 创建任务
await createBacktest({
  name: '测试策略',
  portfolio_uuids: ['uuid-1', 'uuid-2'],
  engine_config: {
    start_date: '2023-01-01',
    end_date: '2023-12-31',
    commission_rate: 0.0003
  }
})
```

### 2. 通用表格组件

```vue
<template>
  <DataTable
    :columns="columns"
    :data-source="dataSource"
    :loading="loading"
    :page="page"
    :pageSize="20"
    :total="total"
    @refresh="handleRefresh"
  >
    <template #toolbar>
      <a-button type="primary" @click="showCreateModal">新建</a-button>
    </template>
  </DataTable>
</template>
```

### 3. 增强表单组件

```vue
<template>
  <ProForm
    v-model="formData"
    :rules="formRules"
    :loading="submitting"
    submitText="保存"
    @submit="handleSubmit"
  >
    <a-form-item label="名称" name="name">
      <a-input v-model:value="formData.name" />
    </a-form-item>
  </ProForm>
</template>
```

### 4. API 错误处理

```typescript
import { useApiError } from '@/composables/useApiError'

const { handleError } = useApiError()

try {
  await apiCall()
} catch (error) {
  handleError(error, '操作失败')
}
```

## 🎨 设计原则

1. **单一职责** - 每个模块只负责一件事
2. **依赖注入** - 使用 composable 而非直接导入
3. **类型安全** - 使用 TypeScript 严格模式
4. **可测试性** - 所有函数可独立测试

## 📝 迁移指南

### 从旧代码迁移

1. 替换 `import { create } from '@/api/modules/backtest'`
   → `import { createBacktest } from '@/api/modules/business/backtest'`

2. 替换表格为 `DataTable`
   → 保留现有列配置，移除分页逻辑

3. 使用 `useApiError` 处理 API 错误
   → 移除 try-catch 中的错误处理代码
