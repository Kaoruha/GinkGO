# Data Model: Web UI 回测列表与详情修复

**Feature**: 013-webui-completion
**Date**: 2026-03-02

## Overview

本文档定义 Web UI 回测列表与详情修复功能涉及的数据模型。

## Core Entities

### BacktestTask (回测任务)

**描述**: 回测任务的核心数据模型

```typescript
interface BacktestTask {
  // 标识
  uuid: string                    // 任务唯一标识
  name: string                    // 任务名称

  // 状态 (六态模型)
  status: BacktestStatus          // 任务状态

  // 时间信息
  created_at: string              // 创建时间 (ISO 8601)
  updated_at: string              // 更新时间 (ISO 8601)
  started_at?: string             // 开始时间 (ISO 8601)
  completed_at?: string           // 完成时间 (ISO 8601)

  // 进度
  progress: number                // 进度百分比 (0-100)
  current_stage?: string          // 当前阶段描述

  // 权限
  creator_id: string              // 创建者用户 ID

  // 关联
  portfolio_uuid: string          // 关联的投资组合 UUID
  portfolio_name: string          // 投资组合名称

  // 配置
  config: BacktestConfig          // 回测配置

  // 结果
  result?: BacktestResult         // 回测结果（完成后可用）

  // 错误
  error_message?: string          // 错误信息（失败时可用）
}
```

### BacktestStatus (回测状态)

**描述**: 回测任务状态的枚举类型

```typescript
type BacktestStatus =
  | 'created'    // 待调度 - 任务已创建，等待调度
  | 'pending'    // 排队中 - 任务已排队，等待执行
  | 'running'    // 进行中 - 任务正在执行
  | 'completed'  // 已完成 - 任务执行完成
  | 'stopped'    // 已停止 - 任务被用户停止
  | 'failed'     // 失败 - 任务执行失败
```

**状态转换图**:

```
created → pending → running → completed
                              → failed
         ↑         ↑
         └─────────┴───────── stopped (用户停止/取消)
```

### BacktestConfig (回测配置)

```typescript
interface BacktestConfig {
  start_date: string             // 回测开始日期 (YYYY-MM-DD)
  end_date: string               // 回测结束日期 (YYYY-MM-DD)
  initial_cash?: number          // 初始资金
  commission_rate: number        // 手续费率
  slippage_rate: number          // 滑点率
  broker_attitude: number        // Broker 态度 (1=悲观, 2=乐观, 3=随机)
}
```

### BacktestResult (回测结果)

```typescript
interface BacktestResult {
  total_return: number           // 总收益率
  annual_return: number          // 年化收益率
  sharpe_ratio: number           // 夏普比率
  max_drawdown: number           // 最大回撤
  win_rate: number               // 胜率
}
```

### UserInfo (用户信息)

```typescript
interface UserInfo {
  id: string                     // 用户 ID
  username: string               // 用户名
  display_name?: string          // 显示名称
  is_admin: boolean              // 是否为管理员
}
```

## Component State Models

### BacktestList State (回测列表状态)

```typescript
interface BacktestListState {
  // 数据
  tasks: BacktestTask[]          // 任务列表
  total: number                  // 总数

  // 筛选
  filterStatus: BacktestStatus | ''  // 状态筛选
  searchKeyword: string          // 搜索关键词

  // 分页
  currentPage: number            // 当前页
  pageSize: number               // 每页数量

  // 选中
  selectedIds: Set<string>       // 已选中的任务 ID

  // 加载状态
  loading: boolean
  refreshing: boolean

  // 统计
  stats: {
    total: number
    running: number
    completed: number
    failed: number
  }

  // 实时更新
  wsConnected: boolean           // WebSocket 连接状态
  pollingMode: boolean           // 是否为轮询模式
}
```

### BacktestDetail State (回测详情状态)

```typescript
interface BacktestDetailState {
  // 数据
  task: BacktestTask | null       // 当前任务
  netValue: BacktestNetValue | null  // 净值数据
  analyzers: AnalyzerInfo[]       // 分析器列表

  // 加载状态
  loading: boolean
  detailLoading: boolean

  // 操作
  operationLoading: boolean       // 操作加载状态
}
```

## API Request/Response Models

### ListBacktestsRequest (获取回测列表请求)

```typescript
interface ListBacktestsRequest {
  page?: number                   // 页码（默认 1）
  size?: number                   // 每页数量（默认 20）
  status?: BacktestStatus         // 状态筛选
  search?: string                 // 搜索关键词
}
```

### ListBacktestsResponse (获取回测列表响应)

```typescript
interface ListBacktestsResponse<T> {
  data: T[]                       // 任务列表
  total: number                   // 总数
  page: number                    // 当前页
  size: number                    // 每页数量
}
```

### StartBacktestRequest (启动回测请求)

```typescript
interface StartBacktestRequest {
  // 启动时不传递参数，直接使用原配置
}
```

### StartBacktestResponse (启动回测响应)

```typescript
interface StartBacktestResponse {
  uuid: string                    // 新任务的 UUID（启动创建新实例）
  status: BacktestStatus           // 任务状态
  message: string                 // 操作消息
}
```

### BatchOperationResult (批量操作结果)

```typescript
interface BatchOperationResult {
  total: number                   // 总数
  success: number                 // 成功数
  failed: number                  // 失败数
  failed_tasks?: Array<{
    uuid: string
    error: string
  }>
}
```

## WebSocket Message Models

### TaskUpdateMessage (任务更新消息)

```typescript
interface TaskUpdateMessage {
  type: 'task_update'             // 消息类型
  task_id: string                 // 任务 ID
  timestamp: string               // 服务端时间戳
  data: {
    status?: BacktestStatus       // 状态更新
    progress?: number             // 进度更新
    current_stage?: string        // 阶段更新
    error_message?: string        // 错误信息
  }
}
```

### TaskProgressMessage (任务进度消息)

```typescript
interface TaskProgressMessage {
  type: 'task_progress'           // 消息类型
  task_id: string                 // 任务 ID
  timestamp: string               // 服务端时间戳
  data: {
    progress: number              // 进度百分比
    current_stage: string         // 当前阶段
  }
}
```

## Component Props Models

### StatusTagProps (状态标签组件)

```typescript
interface StatusTagProps {
  status: BacktestStatus          // 状态码
}

// 状态配置
const STATUS_CONFIG: Record<BacktestStatus, StatusConfig> = {
  created: { label: '待调度', color: 'default', badgeStatus: 'default' },
  pending: { label: '排队中', color: 'blue', badgeStatus: 'processing' },
  running: { label: '进行中', color: 'green', badgeStatus: 'processing' },
  completed: { label: '已完成', color: 'success', badgeStatus: 'success' },
  stopped: { label: '已停止', color: 'warning', badgeStatus: 'default' },
  failed: { label: '失败', color: 'error', badgeStatus: 'error' }
}

interface StatusConfig {
  label: string                   // 中文标签
  color: string                   // 颜色标识
  badgeStatus: string             // Badge 状态
}
```

### BatchActionBarProps (批量操作栏组件)

```typescript
interface BatchActionBarProps {
  selectedCount: number           // 已选中数量
  canStart: boolean               // 是否可启动
  canStop: boolean                // 是否可停止
  canCancel: boolean              // 是否可取消
  onStart: () => void             // 启动回调
  onStop: () => void              // 停止回调
  onCancel: () => void            // 取消回调
  onClear: () => void             // 清除选择回调
}
```

## Validation Rules

### BacktestTask Validation

| 字段 | 规则 | 错误提示 |
|------|------|----------|
| uuid | 必需，格式为 UUID | 无效的任务 ID |
| name | 必需，1-200 字符 | 任务名称不能为空 |
| status | 必需，为有效状态值 | 无效的状态 |
| created_at | 必需，有效日期时间 | 无效的创建时间 |
| creator_id | 必需 | 无效的创建者 ID |
| portfolio_uuid | 必需 | 无效的投资组合 |

### Operation Permission Validation

| 操作 | 条件 | 错误提示 |
|------|------|----------|
| 启动 | status ∈ {completed, failed, stopped} | 只有已完成/失败/已停止的任务可以启动 |
| 停止 | status ∈ {running} | 只有进行中的任务可以停止 |
| 取消 | status ∈ {created, pending} | 只有待调度/排队中的任务可以取消 |
| 删除 | status ∈ {completed, failed, stopped} | 只有已完成/失败/已停止的任务可以删除 |
| 所有操作 | user.id === task.creator_id \|\| user.is_admin | 仅创建者可操作 |

## State Transitions

### Valid State Transitions

```typescript
const VALID_TRANSITIONS: Record<BacktestStatus, BacktestStatus[]> = {
  created: ['pending', 'stopped'],
  pending: ['running', 'stopped'],
  running: ['completed', 'failed', 'stopped'],
  completed: [],
  stopped: [],
  failed: []
}
```

### Operation Availability by State

```typescript
const OPERATION_AVAILABILITY: Record<BacktestStatus, {
  start: boolean
  stop: boolean
  cancel: boolean
  delete: boolean
}> = {
  created: { start: false, stop: false, cancel: true, delete: true },
  pending: { start: false, stop: false, cancel: true, delete: true },
  running: { start: false, stop: true, cancel: false, delete: false },
  completed: { start: true, stop: false, cancel: false, delete: true },
  stopped: { start: true, stop: false, cancel: false, delete: true },
  failed: { start: true, stop: false, cancel: false, delete: true }
}
```

---

**Data Model Status**: Complete. Ready for implementation.
