/**
 * Upstream: data-model.md
 * Downstream: StatusTag.vue, BacktestList.vue, BacktestDetail.vue
 * Role: 回测任务状态常量，提供六态模型配置
 */

/** 回测默认时间范围（单位：月） */
export const BACKTEST_DEFAULT_RANGE_MONTHS = 12

/**
 * 回测任务状态（六态模型）
 * - created: 待调度 - 任务已创建，等待调度
 * - pending: 排队中 - 任务已排队，等待执行
 * - running: 进行中 - 任务正在执行
 * - completed: 已完成 - 任务执行完成
 * - stopped: 已停止 - 任务被用户停止
 * - failed: 失败 - 任务执行失败
 */
export const BACKTEST_STATES = {
  CREATED: 'created',
  PENDING: 'pending',
  RUNNING: 'running',
  COMPLETED: 'completed',
  STOPPED: 'stopped',
  FAILED: 'failed'
} as const

export type BacktestState = typeof BACKTEST_STATES[keyof typeof BACKTEST_STATES]

/** 状态标签映射（六态模型） */
export const BACKTEST_STATE_LABELS: Record<string, string> = {
  created: '待调度',
  pending: '排队中',
  running: '进行中',
  completed: '已完成',
  stopped: '已停止',
  failed: '失败'
}

/** 状态颜色映射（六态模型） */
export const BACKTEST_STATE_COLORS: Record<string, string> = {
  created: 'default',
  pending: 'blue',
  running: 'processing',
  completed: 'success',
  stopped: 'warning',
  failed: 'error'
}

/** 状态 Badge 配置（用于 a-badge） */
export const BACKTEST_STATE_BADGE_STATUS: Record<string, string> = {
  created: 'default',
  pending: 'processing',
  running: 'processing',
  completed: 'success',
  stopped: 'default',
  failed: 'error'
}

/**
 * 状态可用操作配置
 * 用于判断某个状态下可以执行哪些操作
 */
export const STATE_OPERATIONS: Record<string, {
  canStart: boolean
  canStop: boolean
  canCancel: boolean
  canDelete: boolean
}> = {
  created: { canStart: false, canStop: false, canCancel: true, canDelete: true },
  pending: { canStart: false, canStop: false, canCancel: true, canDelete: true },
  running: { canStart: false, canStop: true, canCancel: false, canDelete: false },
  completed: { canStart: true, canStop: false, canCancel: false, canDelete: true },
  stopped: { canStart: true, canStop: false, canCancel: false, canDelete: true },
  failed: { canStart: true, canStop: false, canCancel: false, canDelete: true }
}

/** Broker 态度选项 */
export const BROKER_ATTITUDES = [
  { label: '悲观（成交难）', value: 1 },
  { label: '乐观（成交易）', value: 2 },
  { label: '随机', value: 3 }
]

/** Broker 态度标签 */
export const BROKER_ATTITUDE_LABELS: Record<number, string> = {
  1: '悲观',
  2: '乐观',
  3: '随机'
}

/**
 * 获取状态标签
 */
export function getBacktestStateLabel(state: string): string {
  return BACKTEST_STATE_LABELS[state] || state
}

/**
 * 获取状态颜色
 */
export function getBacktestStateColor(state: string): string {
  return BACKTEST_STATE_COLORS[state] || 'default'
}

/**
 * 获取状态 Badge 状态
 */
export function getBacktestStateBadgeStatus(state: string): string {
  return BACKTEST_STATE_BADGE_STATUS[state] || 'default'
}

/**
 * 判断状态是否可以启动
 * 只有已完成、失败、已停止的任务可以启动
 */
export function canStartByState(state: string): boolean {
  return STATE_OPERATIONS[state]?.canStart || false
}

/**
 * 判断状态是否可以停止
 * 只有进行中的任务可以停止
 */
export function canStopByState(state: string): boolean {
  return STATE_OPERATIONS[state]?.canStop || false
}

/**
 * 判断状态是否可以取消
 * 只有待调度、排队中的任务可以取消
 */
export function canCancelByState(state: string): boolean {
  return STATE_OPERATIONS[state]?.canCancel || false
}

/**
 * 判断状态是否可以删除
 * 只有非运行中的任务可以删除
 */
export function canDeleteByState(state: string): boolean {
  return STATE_OPERATIONS[state]?.canDelete || false
}

/**
 * 判断状态是否为运行中
 */
export function isRunning(state: string): boolean {
  return state === 'running'
}

/**
 * 判断状态是否为已完成（成功、停止、失败都算已完成）
 */
export function isCompleted(state: string): boolean {
  return ['completed', 'stopped', 'failed'].includes(state)
}

/**
 * 获取Broker态度标签
 */
export function getBrokerAttitudeLabel(value: number): string {
  return BROKER_ATTITUDE_LABELS[value] || `${value}`
}

/**
 * 获取状态类型（用于 a-tag 的 status 属性）
 * @deprecated 使用 getStateBadgeStatus 代替
 */
export function getStateStatus(state: string): string {
  return BACKTEST_STATE_COLORS[state] || 'default'
}
