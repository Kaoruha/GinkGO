# Quickstart Guide: Web UI 回测列表与详情修复

**Feature**: 013-webui-completion
**Date**: 2026-03-02

## Overview

本文档提供 Web UI 回测列表与详情修复功能的快速开发指南。

## Prerequisites

### Required Software

- **Node.js**: 18.x 或更高版本
- **pnpm**: 8.x 或更高版本（包管理器）
- **浏览器**: Chrome/Edge/Firefox 最新版本

### Required Knowledge

- Vue 3 Composition API
- TypeScript 基础
- Pinia 状态管理
- Ant Design Vue 组件库

## Project Setup

### 1. 克隆并安装依赖

```bash
cd /home/kaoru/Ginkgo/web-ui
pnpm install
```

### 2. 启动开发服务器

```bash
pnpm dev
```

访问: http://localhost:5173

### 3. 启动后端 API 服务

```bash
# 在 Ginkgo 项目根目录
cd /home/kaoru/Ginkgo
docker-compose up -d
```

## Development Workflow

### 1. 创建功能分支

```bash
git checkout -b 013-webui-completion
```

### 2. 修改文件结构

```
web-ui/src/
├── api/modules/business/
│   └── backtest.ts          # API 接口（可能需要更新）
├── views/Backtest/
│   ├── BacktestList.vue     # 列表页（主要修改）
│   └── BacktestDetail.vue   # 详情页（主要修改）
├── components/common/
│   └── StatusTag.vue        # 新增：状态标签组件
├── stores/
│   └── backtest.ts          # Store（需要更新）
├── composables/
│   └── useErrorHandler.ts   # 新增：统一错误处理
└── constants/
    ├── backtest.ts          # 常量（需要更新）
    └── index.ts             # 导出（需要更新）
```

### 3. 实现顺序

**Phase 1: 基础组件和工具**
1. 创建 `StatusTag.vue` 组件
2. 创建 `useErrorHandler.ts` composable
3. 更新 `constants/backtest.ts` 添加六态配置

**Phase 2: Store 更新**
1. 更新 `stores/backtest.ts` 添加权限检查方法
2. 添加批量操作方法
3. 添加 WebSocket 降级逻辑

**Phase 3: 列表页实现**
1. 添加复选框列
2. 添加批量操作栏
3. 更新操作按钮逻辑
4. 添加 WebSocket 订阅

**Phase 4: 详情页实现**
1. 添加启动/删除/复制按钮
2. 添加权限检查
3. 添加操作确认对话框

## Coding Standards

### 1. 文件头部注释

```typescript
/**
 * Upstream: none
 * Downstream: BacktestList.vue, BacktestDetail.vue
 * Role: 回测任务状态管理，提供任务列表、详情、操作等方法
 */
```

### 2. TypeScript 类型定义

```typescript
// ✅ 正确：明确的类型定义
interface BacktestTask {
  uuid: string
  name: string
  status: BacktestStatus
}

// ❌ 错误：使用 any
const task: any = {}
```

### 3. 组件命名

```typescript
// 组件文件名：PascalCase
StatusTag.vue
BatchActionBar.vue

// composable 文件名：use 前缀 + camelCase
useErrorHandler.ts
useBatchOperations.ts
```

### 4. API 调用

```typescript
// ✅ 正确：使用统一的错误处理
import { useErrorHandler } from '@/composables/useErrorHandler'

const { execute } = useErrorHandler()
const result = await execute(() => startBacktest(uuid))

// ❌ 错误：直接调用不处理错误
const result = await startBacktest(uuid)
```

## Testing

### 单元测试

```bash
pnpm test:unit
```

### 组件测试

```bash
pnpm test:component
```

### E2E 测试

```bash
pnpm test:e2e
```

## Key Implementation Details

### 1. 权限检查

```typescript
import { useAuthStore } from '@/stores/auth'

function canOperateTask(task: BacktestTask): boolean {
  const authStore = useAuthStore()
  return authStore.isAdmin || authStore.user?.id === task.creator_id
}
```

### 2. 批量操作

```typescript
async function batchStart(uuids: string[]) {
  const results = await Promise.allSettled(
    uuids.map(uuid => startBacktest(uuid))
  )

  const success = results.filter(r => r.status === 'fulfilled').length
  const failed = results.filter(r => r.status === 'rejected').length

  message.info(`批量启动完成：成功 ${success} 个，失败 ${failed} 个`)
}
```

### 3. WebSocket 降级

```typescript
class WebSocketManager {
  private pollingTimer: number | null = null

  onDisconnected() {
    // 启动轮询
    this.startPolling()
  }

  onReconnected() {
    // 停止轮询
    this.stopPolling()
  }

  private startPolling() {
    this.pollingTimer = setInterval(() => {
      fetchLatestData()
    }, 5000)
  }
}
```

### 4. 数据同步冲突

```typescript
function mergeTaskUpdate(
  existing: BacktestTask,
  update: BacktestUpdate
): BacktestTask {
  const existingTime = new Date(existing.updated_at).getTime()
  const updateTime = new Date(update.updated_at).getTime()

  return updateTime > existingTime
    ? { ...existing, ...update }
    : existing
}
```

## Common Patterns

### 1. 操作确认对话框

```typescript
function handleStop(task: BacktestTask) {
  Modal.confirm({
    title: '确认停止',
    content: `确定要停止回测任务"${task.name}"吗？`,
    onOk: async () => {
      await stopTask(task.uuid)
      message.success('已停止')
    }
  })
}
```

### 2. 动态按钮状态

```vue
<template>
  <a-button
    :disabled="!canStartTask(task)"
    @click="handleStart(task)"
  >
    启动
  </a-button>
</template>

<script setup lang="ts">
const canStartTask = (task: BacktestTask) => {
  return ['completed', 'failed', 'stopped'].includes(task.status) &&
         canOperateTask(task)
}
</script>
```

### 3. 批量选择管理

```vue
<script setup lang="ts">
const selectedIds = ref<Set<string>>(new Set())

const toggleSelect = (uuid: string) => {
  if (selectedIds.value.has(uuid)) {
    selectedIds.value.delete(uuid)
  } else {
    selectedIds.value.add(uuid)
  }
}

const isAllSelected = computed(() => {
  return tasks.value.length > 0 &&
         tasks.value.every(t => selectedIds.value.has(t.uuid))
})

const toggleSelectAll = () => {
  if (isAllSelected.value) {
    selectedIds.value.clear()
  } else {
    tasks.value.forEach(t => selectedIds.value.add(t.uuid))
  }
}
</script>
```

## Debugging

### 1. 检查 WebSocket 连接

```typescript
console.log('WebSocket 状态:', ws.readyState)
// 0 = CONNECTING, 1 = OPEN, 2 = CLOSING, 3 = CLOSED
```

### 2. 检查权限

```typescript
const authStore = useAuthStore()
console.log('当前用户:', authStore.user)
console.log('是否 Admin:', authStore.isAdmin)
```

### 3. 检查状态转换

```typescript
console.log('当前状态:', task.status)
console.log('可执行操作:', getAvailableOperations(task.status))
```

## Troubleshooting

### 问题 1: WebSocket 连接失败

**症状**: 任务状态不实时更新

**解决方案**:
1. 检查后端 WebSocket 服务是否启动
2. 检查浏览器控制台是否有连接错误
3. 系统应自动降级到轮询模式

### 问题 2: 批量操作部分失败

**症状**: 部分任务操作成功，部分失败

**解决方案**:
1. 使用 `Promise.allSettled` 而非 `Promise.all`
2. 显示成功/失败统计
3. 提供失败任务详情

### 问题 3: 权限检查不生效

**症状**: 用户可以操作他人的任务

**解决方案**:
1. 检查 `useAuthStore` 是否正确初始化
2. 检查 `task.creator_id` 是否正确返回
3. 检查 `user.is_admin` 标志

## Deployment

### 1. 构建生产版本

```bash
pnpm build
```

### 2. 预览生产构建

```bash
pnpm preview
```

### 3. 部署到服务器

```bash
# 将 dist 目录上传到服务器
scp -r dist/* user@server:/var/www/html/
```

---

**Quickstart Status**: Complete. Ready for development.
