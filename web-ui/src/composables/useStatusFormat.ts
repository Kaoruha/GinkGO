/**
 * 状态格式化 Composable
 * 用于统一管理状态标签的颜色和文本映射
 */
import { computed, type ComputedRef } from 'vue'

/**
 * 状态配置类型
 */
export interface StatusConfig {
  color: string
  label: string
}

/**
 * 通用状态格式化 composable
 */
export function useStatusFormat<T extends string>(
  config: Record<T, StatusConfig>
) {
  const getColor = (status: T): string => {
    return config[status]?.color || 'default'
  }

  const getLabel = (status: T): string => {
    return config[status]?.label || status
  }

  return { getColor, getLabel }
}

/**
 * 预定义的状态映射配置
 */

// 回测状态
export const BACKTEST_STATUS_CONFIG: Record<string, StatusConfig> = {
  created: { color: 'default', label: '待启动' },
  pending: { color: 'warning', label: '等待中' },
  running: { color: 'processing', label: '运行中' },
  completed: { color: 'success', label: '已完成' },
  failed: { color: 'error', label: '失败' },
  stopped: { color: 'default', label: '已停止' },
}

// Portfolio 模式
export const PORTFOLIO_MODE_CONFIG: Record<number, StatusConfig> = {
  0: { color: 'blue', label: '回测' },
  1: { color: 'orange', label: '模拟' },
  2: { color: 'red', label: '实盘' },
}

// Portfolio 状态
export const PORTFOLIO_STATE_CONFIG: Record<number, StatusConfig> = {
  0: { color: 'default', label: '已停止' },
  1: { color: 'green', label: '运行中' },
  2: { color: 'blue', label: '已完成' },
  3: { color: 'red', label: '错误' },
}

/**
 * 回测状态格式化
 */
export function useBacktestStatus() {
  return useStatusFormat<string>(BACKTEST_STATUS_CONFIG)
}

/**
 * Portfolio 模式格式化
 */
export function usePortfolioMode() {
  const getColor = (mode: number): string => {
    return PORTFOLIO_MODE_CONFIG[mode]?.color || 'default'
  }

  const getLabel = (mode: number): string => {
    return PORTFOLIO_MODE_CONFIG[mode]?.label || '未知'
  }

  return { getColor, getLabel }
}

/**
 * Portfolio 状态格式化
 */
export function usePortfolioState() {
  const getColor = (state: number): string => {
    return PORTFOLIO_STATE_CONFIG[state]?.color || 'default'
  }

  const getLabel = (state: number): string => {
    return PORTFOLIO_STATE_CONFIG[state]?.label || '未知'
  }

  return { getColor, getLabel }
}
