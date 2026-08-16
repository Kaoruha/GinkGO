/**
 * 统一的数据格式化工具库
 * 用于减少前端各组件中重复的格式化逻辑
 */

/**
 * 格式化百分比
 * @param value 数值 (0.01 表示 1%)
 * @param decimals 小数位数，默认 2
 * @returns 格式化后的百分比字符串，如 "1.23%" 或 "-"
 */
export function formatPercent(value: any, decimals = 2): string {
  if (value == null || value === '') return '-'
  const num = Number(value)
  if (isNaN(num)) return '-'
  return (num * 100).toFixed(decimals) + '%'
}

/**
 * 格式化数字
 * @param value 数值
 * @param decimals 小数位数，默认 2
 * @returns 格式化后的数字字符串，如 "123.45" 或 "-"
 */
export function formatNumber(value: any, decimals = 2): string {
  if (value == null || value === '') return '-'
  const num = Number(value)
  if (isNaN(num)) return '-'
  return num.toFixed(decimals)
}

/**
 * 格式化日期时间
 * @param timestamp ISO 时间戳字符串
 * @returns 格式化后的日期时间，如 "2024-01-01 12:00:00" 或 "-"
 */
export function formatDateTime(timestamp: string): string {
  if (!timestamp) return '-'
  // 处理 ISO 格式时间戳，将 T 替换为空格，并截取到秒
  return timestamp.replace('T', ' ').slice(0, 19)
}

/**
 * 格式化短日期
 * @param timestamp ISO 时间戳字符串
 * @returns 格式化后的短日期，如 "2024-01-01" 或 "-"
 */
export function formatShortDate(timestamp: string): string {
  if (!timestamp) return '-'
  return timestamp.slice(0, 10)
}

/**
 * 任务状态标签映射
 */
export const STATE_LABELS: Record<string, string> = {
  RUNNING: '运行中',
  PAUSED: '已暂停',
  STOPPED: '已停止',
  COMPLETED: '已完成',
  ERROR: '异常',
  PENDING: '排队中',
  CREATED: '已创建',
  FAILED: '失败'
}

/**
 * 获取状态标签文本
 * @param state 状态字符串
 * @returns 对应的中文标签，如未找到则返回原状态
 */
export function getStateLabel(state: string | number): string {
  return STATE_LABELS[String(state)] ?? String(state)
}

/**
 * 格式化日志时间戳
 * @param timestamp ISO 时间戳字符串或毫秒时间戳
 * @returns 格式化后的时间，如 "2024-01-01 12:00:00.123"
 */
export function formatLogTime(timestamp: string | number): string {
  if (!timestamp) return '-'

  const timeStr = String(timestamp)

  // 如果是毫秒时间戳（13位数字）
  if (/^\d{13}$/.test(timeStr)) {
    const date = new Date(Number(timeStr))
    return date.toISOString().replace('T', ' ').slice(0, 23)
  }

  // 如果是 ISO 格式
  return timeStr.replace('T', ' ').slice(0, 23)
}

/**
 * 格式化方向标签
 * @param direction 方向值 ('LONG', 'SHORT', 'CLOSE_LONG', 'CLOSE_SHORT')
 * @returns 中文方向标签
 */
export function getDirectionLabel(direction: string): string {
  const labels: Record<string, string> = {
    LONG: '做多',
    SHORT: '做空',
    CLOSE_LONG: '平多',
    CLOSE_SHORT: '平空'
  }
  return labels[direction] ?? direction
}

/**
 * 获取方向对应的颜色类名
 * @param direction 方向值
 * @returns Tailwind CSS 类名
 */
export function getDirectionColor(direction: string): string {
  const colors: Record<string, string> = {
    LONG: 'text-red-600',
    SHORT: 'text-green-600',
    CLOSE_LONG: 'text-blue-600',
    CLOSE_SHORT: 'text-blue-600'
  }
  return colors[direction] ?? 'text-gray-600'
}

/**
 * 格式化分析器数据
 * @param analyzer 分析器信息对象
 * @returns 格式化后的数值对象
 */
export function formatAnalyzerData(analyzer: any): Record<string, string | number> {
  if (!analyzer) return {}

  return {
    total_return: formatPercent(analyzer.total_return),
    annual_return: formatPercent(analyzer.annual_return),
    max_drawdown: formatPercent(analyzer.max_drawdown),
    sharpe_ratio: formatNumber(analyzer.sharpe_ratio, 3),
    volatility: formatPercent(analyzer.volatility),
    win_rate: formatPercent(analyzer.win_rate)
  }
}

/**
 * 获取分析器指标颜色（用于趋势显示）
 * @param value 数值
 * @param isInverse 是否反向（如回撤应该是负数为好）
 * @returns 颜色类名
 */
export function getAnalyzerColor(value: number, isInverse = false): string {
  if (value == null) return 'text-gray-500'

  const num = Number(value)
  if (isNaN(num)) return 'text-gray-500'

  if (isInverse) {
    // 回撤类指标，越小越好
    return num < 0 ? 'text-green-600' : num > 0 ? 'text-red-600' : 'text-gray-500'
  } else {
    // 收益类指标，越大越好
    return num > 0 ? 'text-red-600' : num < 0 ? 'text-green-600' : 'text-gray-500'
  }
}