/**
 * 状态格式化 Composable
 * 用于统一管理状态标签的颜色和文本映射
 */
import { computed, type ComputedRef } from 'vue'

/**
 * 状态配置类型
 */
export interface StatusConfig {
  /** tag CSS 类名，如 'tag-blue', 'tag-green' */
  tagClass: string
  /** 显示文本 */
  label: string
}

/**
 * 通用状态格式化 composable
 */
export function useStatusFormat<T extends string | number>(
  config: Record<string, StatusConfig>
) {
  const getTagClass = (status: T): string => {
    return config[String(status)]?.tagClass || 'tag-gray'
  }

  const getLabel = (status: T): string => {
    return config[String(status)]?.label || String(status)
  }

  return { getTagClass, getLabel }
}

/**
 * 预定义的状态映射配置
 */

// 回测状态
export const BACKTEST_STATUS_CONFIG: Record<string, StatusConfig> = {
  created: { tagClass: 'tag-gray', label: '待启动' },
  pending: { tagClass: 'tag-orange', label: '等待中' },
  running: { tagClass: 'tag-blue', label: '运行中' },
  completed: { tagClass: 'tag-green', label: '已完成' },
  failed: { tagClass: 'tag-red', label: '失败' },
  stopped: { tagClass: 'tag-gray', label: '已停止' },
  cancelled: { tagClass: 'tag-orange', label: '已取消' },
}

// Portfolio 模式
export const PORTFOLIO_MODE_CONFIG: Record<string, StatusConfig> = {
  '0': { tagClass: 'tag-blue', label: '回测' },
  '1': { tagClass: 'tag-orange', label: '模拟' },
  '2': { tagClass: 'tag-red', label: '实盘' },
  'BACKTEST': { tagClass: 'tag-blue', label: '回测' },
  'PAPER': { tagClass: 'tag-orange', label: '模拟' },
  'LIVE': { tagClass: 'tag-red', label: '实盘' },
}

// Portfolio 状态
export const PORTFOLIO_STATE_CONFIG: Record<string, StatusConfig> = {
  '0': { tagClass: 'tag-gray', label: '已停止' },
  '1': { tagClass: 'tag-green', label: '运行中' },
  '2': { tagClass: 'tag-blue', label: '已完成' },
  '3': { tagClass: 'tag-red', label: '错误' },
  'RUNNING': { tagClass: 'tag-green', label: '运行中' },
  'PAUSED': { tagClass: 'tag-orange', label: '已暂停' },
  'STOPPED': { tagClass: 'tag-gray', label: '已停止' },
  'COMPLETED': { tagClass: 'tag-blue', label: '已完成' },
  'ERROR': { tagClass: 'tag-red', label: '错误' },
  'INITIALIZED': { tagClass: 'tag-gray', label: '未启动' },
}

// 订单状态
export const ORDER_STATUS_CONFIG: Record<string, StatusConfig> = {
  '0': { tagClass: 'tag-orange', label: '待处理' },
  '1': { tagClass: 'tag-green', label: '已成交' },
  '2': { tagClass: 'tag-gray', label: '已取消' },
  '3': { tagClass: 'tag-blue', label: '部分成交' },
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
  return useStatusFormat<number>(PORTFOLIO_MODE_CONFIG)
}

/**
 * Portfolio 状态格式化
 */
export function usePortfolioState() {
  return useStatusFormat<number>(PORTFOLIO_STATE_CONFIG)
}

/**
 * 订单状态格式化
 */
export function useOrderStatus() {
  return useStatusFormat<number>(ORDER_STATUS_CONFIG)
}
