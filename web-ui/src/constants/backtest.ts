/**
 * 回测任务相关常量
 */

/** 回测任务状态 */
export const BACKTEST_STATES = {
  PENDING: 'PENDING',
  RUNNING: 'RUNNING',
  COMPLETED: 'COMPLETED',
  FAILED: 'FAILED',
  CANCELLED: 'CANCELLED'
} as const

export type BacktestState = typeof BACKTEST_STATES[keyof typeof BACKTEST_STATES]

/** 状态标签映射 */
export const STATE_LABELS: Record<string, string> = {
  PENDING: '等待中',
  RUNNING: '运行中',
  COMPLETED: '已完成',
  FAILED: '失败',
  CANCELLED: '已取消'
}

/** 状态颜色映射 */
export const STATE_COLORS: Record<string, string> = {
  PENDING: 'default',
  RUNNING: 'processing',
  COMPLETED: 'success',
  FAILED: 'error',
  CANCELLED: 'default'
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
export function getStateLabel(state: string): string {
  return STATE_LABELS[state] || state
}

/**
 * 获取状态颜色
 */
export function getStateColor(state: string): string {
  return STATE_COLORS[state] || 'default'
}

/**
 * 获取Broker态度标签
 */
export function getBrokerAttitudeLabel(value: number): string {
  return BROKER_ATTITUDE_LABELS[value] || `${value}`
}

/**
 * 获取状态类型（用于 a-tag 的 status 属性）
 * 注意：对于回测状态，颜色和状态类型使用相同的值
 */
export function getStateStatus(state: string): string {
  return STATE_COLORS[state] || 'default'
}
