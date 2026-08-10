/**
 * Portfolio 相关常量
 */

/** 投资组合模式 */
export const PORTFOLIO_MODES = {
  BACKTEST: 'BACKTEST',
  PAPER: 'PAPER',
  LIVE: 'LIVE'
} as const

export type PortfolioMode = typeof PORTFOLIO_MODES[keyof typeof PORTFOLIO_MODES]

/** 投资组合状态 */
export const PORTFOLIO_STATES = {
  INITIALIZED: 'INITIALIZED',
  RUNNING: 'RUNNING',
  PAUSED: 'PAUSED',
  STOPPED: 'STOPPED'
} as const

export type PortfolioState = typeof PORTFOLIO_STATES[keyof typeof PORTFOLIO_STATES]

/** 状态标签映射 */
export const STATE_LABELS: Record<string, string> = {
  INITIALIZED: '已初始化',
  RUNNING: '运行中',
  PAUSED: '已暂停',
  STOPPED: '已停止'
}

/** 状态颜色映射 */
export const STATE_COLORS: Record<string, string> = {
  INITIALIZED: 'default',
  RUNNING: 'green',
  PAUSED: 'orange',
  STOPPED: 'red'
}

/** 模式标签映射 */
export const MODE_LABELS: Record<string, string> = {
  BACKTEST: '回测',
  PAPER: '模拟',
  LIVE: '实盘'
}

/** 模式颜色映射 */
export const MODE_COLORS: Record<string, string> = {
  BACKTEST: 'blue',
  PAPER: 'orange',
  LIVE: 'green'
}

/**
 * 获取模式标签
 */
export function getModeLabel(mode: string): string {
  return MODE_LABELS[mode] || mode
}

/**
 * 获取模式颜色
 */
export function getModeColor(mode: string): string {
  return MODE_COLORS[mode] || 'default'
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

/** 状态类型映射（用于 a-tag 的 status 属性） */
export const STATE_STATUS: Record<string, string> = {
  INITIALIZED: 'default',
  RUNNING: 'processing',
  PAUSED: 'warning',
  STOPPED: 'default'
}

/**
 * 获取状态类型（用于 a-tag 的 status 属性）
 */
export function getStateStatus(state: string): string {
  return STATE_STATUS[state] || 'default'
}
