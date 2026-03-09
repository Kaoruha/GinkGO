# Research: Web UI 回测列表与详情修复

**Feature**: 013-webui-completion
**Date**: 2026-03-02

## Overview

本文档记录 Web UI 回测列表与详情修复功能的研究结果和技术决策。

## Research Topics

### 1. WebSocket 与轮询降级最佳实践

**研究问题**: 如何实现 WebSocket 实时更新，并在断线时自动降级到轮询？

**决策**: 采用 WebSocket 优先 + 轮询降级的混合模式

**实现方案**:
```typescript
class BacktestWebSocketManager {
  private ws: WebSocket | null = null
  private pollingInterval: number | null = null
  private isManualClose: boolean = false

  connect() {
    this.ws = new WebSocket(wsUrl)
    this.ws.onopen = () => {
      // 连接成功，停止轮询
      this.stopPolling()
    }
    this.ws.onclose = () => {
      // 非手动关闭时，启动轮询
      if (!this.isManualClose) {
        this.startPolling()
      }
    }
    this.ws.onerror = () => {
      // 错误时启动轮询
      this.startPolling()
    }
  }

  startPolling() {
    if (this.pollingInterval) return
    this.pollingInterval = setInterval(() => {
      fetchLatestData()
    }, 5000) // 5秒间隔
  }

  stopPolling() {
    if (this.pollingInterval) {
      clearInterval(this.pollingInterval)
      this.pollingInterval = null
    }
  }
}
```

**替代方案比较**:
| 方案 | 优点 | 缺点 | 选择 |
|------|------|------|------|
| 纯 WebSocket | 实时性高 | 断线后无数据 | ❌ |
| 纯轮询 | 简单可靠 | 延迟高、服务器压力大 | ❌ |
| 混合模式 | 兼顾实时性和可靠性 | 实现稍复杂 | ✅ |

---

### 2. 前端批量操作 API 调用模式

**研究问题**: 批量启动/停止回测任务应如何实现？

**决策**: 前端并行调用单任务 API，使用 Promise.all

**实现方案**:
```typescript
async function batchStart(uuids: string[]) {
  const results = await Promise.allSettled(
    uuids.map(uuid => startBacktest(uuid))
  )

  const success = results.filter(r => r.status === 'fulfilled').length
  const failed = results.filter(r => r.status === 'rejected').length

  // 显示操作结果
  if (failed > 0) {
    message.warning(`批量启动完成：成功 ${success} 个，失败 ${failed} 个`)
  } else {
    message.success(`批量启动成功 ${success} 个任务`)
  }

  return results
}
```

**替代方案比较**:
| 方案 | 优点 | 缺点 | 选择 |
|------|------|------|------|
| 后端批量 API | 一次调用，原子性好 | 后端需新增接口 | ❌ |
| 前端并行调用 | 复用现有 API，灵活控制 | 多次网络请求 | ✅ |

---

### 3. 权限检查前端实现方案

**研究问题**: 如何检查用户是否有权操作回测任务？

**决策**: 从 useAuthStore 获取当前用户信息，比较 creatorId

**实现方案**:
```typescript
import { useAuthStore } from '@/stores/auth'

function canOperateTask(task: BacktestTask): boolean {
  const authStore = useAuthStore()
  const currentUserId = authStore.user?.id
  const isAdmin = authStore.isAdmin

  // admin 拥有所有权限
  if (isAdmin) return true

  // 仅创建者可操作
  return currentUserId === task.creatorId
}

function getTaskOperationTooltip(task: BacktestTask): string {
  if (canOperateTask(task)) return ''

  return '仅创建者可操作'
}
```

**权限规则**:
| 用户角色 | 操作自己的任务 | 操作他人的任务 |
|----------|----------------|----------------|
| 普通用户 | ✅ 允许 | ❌ 禁止 |
| Admin | ✅ 允许 | ✅ 允许 |

---

### 4. 六态模型状态转换规则

**研究问题**: 回测任务的六态之间如何转换？

**决策**: 采用以下状态转换图

```
created (待调度)
    ↓
pending (排队中)
    ↓
running (进行中)
    ↓
    ↓            ↓
completed    failed (失败)
(已完成)

stopped (已停止) ← created/pending/running
```

**状态转换规则**:
| 当前状态 | 可转换到 | 触发操作 |
|----------|----------|----------|
| created | pending, stopped | 调度器调度、用户取消 |
| pending | running, stopped | 开始执行、用户取消 |
| running | completed, failed, stopped | 执行完成、执行失败、用户停止 |
| completed | - | 终态，不可转换 |
| failed | - | 终态，不可转换 |
| stopped | - | 终态，不可转换 |

**操作按钮状态**:
| 状态 | 启动按钮 | 停止按钮 | 取消按钮 |
|------|----------|----------|----------|
| created | ❌ 禁用 | ❌ 禁用 | ✅ 启用 |
| pending | ❌ 禁用 | ❌ 禁用 | ✅ 启用 |
| running | ❌ 禁用 | ✅ 启用 | ❌ 禁用 |
| completed | ✅ 启用 | ❌ 禁用 | ❌ 禁用 |
| failed | ✅ 启用 | ❌ 禁用 | ❌ 禁用 |
| stopped | ✅ 启用 | ❌ 禁用 | ❌ 禁用 |

---

## Data Sync Conflict Resolution

### 数据同步冲突处理

**问题**: WebSocket 推送与轮询获取的数据可能冲突

**决策**: 比较服务端时间戳，以最新的为准

**实现方案**:
```typescript
function mergeTaskUpdate(
  existing: BacktestTask,
  update: BacktestTask
): BacktestTask {
  // 比较时间戳（假设后端返回 updated_at 字段）
  const existingTime = new Date(existing.updated_at || 0).getTime()
  const updateTime = new Date(update.updated_at || 0).getTime()

  if (updateTime > existingTime) {
    return { ...existing, ...update }
  }

  return existing
}
```

---

## Component Architecture Decisions

### StatusTag 组件设计

**职责**: 将英文状态码映射为中文标签显示

**Props**:
```typescript
interface StatusTagProps {
  status: 'created' | 'pending' | 'running' | 'completed' | 'stopped' | 'failed'
}
```

**状态映射**:
```typescript
const STATUS_CONFIG: Record<string, { label: string; color: string; status: string }> = {
  created: { label: '待调度', color: 'default', status: 'default' },
  pending: { label: '排队中', color: 'blue', status: 'processing' },
  running: { label: '进行中', color: 'green', status: 'processing' },
  completed: { label: '已完成', color: 'success', status: 'success' },
  stopped: { label: '已停止', color: 'orange', status: 'warning' },
  failed: { label: '失败', color: 'error', status: 'error' }
}
```

### 批量操作栏设计

**职责**: 显示已选中任务数量和批量操作按钮

**Props**:
```typescript
interface BatchActionBarProps {
  selectedCount: number
  onStart: () => void
  onStop: () => void
  onCancel: () => void
  onClear: () => void
}
```

---

## Dependencies and External Services

### WebSocket 端点

**端点**: `ws://localhost:8000/api/v1/backtests/ws`

**消息格式**:
```typescript
interface WebSocketMessage {
  type: 'task_update' | 'task_progress'
  task_id: string
  data: {
    status?: string
    progress?: number
    updated_at?: string
  }
}
```

### API 端点

| 端点 | 方法 | 描述 |
|------|------|------|
| `/v1/backtests` | GET | 获取回测列表 |
| `/v1/backtests/{uuid}` | GET | 获取回测详情 |
| `/v1/backtests/{uuid}/start` | POST | 启动回测 |
| `/v1/backtests/{uuid}/stop` | POST | 停止回测 |
| `/v1/backtests/{uuid}/cancel` | POST | 取消回测 |
| `/v1/backtests/{uuid}` | DELETE | 删除回测 |

---

## Testing Strategy

### 单元测试
- StatusTag 组件状态映射
- 权限检查函数
- 数据合并函数

### 集成测试
- 批量操作流程
- WebSocket 连接/断线重连
- 轮询降级

### E2E 测试
- 用户启动回测任务
- 用户停止回测任务
- 批量操作回测任务
- 权限控制（普通用户 vs admin）

---

## Research Summary

| 主题 | 决策 | 影响 |
|------|------|------|
| WebSocket 降级 | 混合模式 | 实时性和可靠性兼顾 |
| 批量操作 | 前端并行调用 | 简化后端，灵活控制 |
| 权限检查 | Pinia auth store | 统一状态管理 |
| 六态模型 | 严格状态转换 | 清晰的任务生命周期 |
| 数据冲突 | 时间戳比较 | 数据一致性保证 |
