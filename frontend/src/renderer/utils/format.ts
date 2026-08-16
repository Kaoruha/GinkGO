/**
 * 格式化工具函数
 */

/**
 * 格式化日期时间 (完整格式)
 */
export function formatDate(dateStr: string | Date | null | undefined): string {
  if (!dateStr) return ''

  try {
    const date = typeof dateStr === 'string' ? new Date(dateStr) : dateStr

    if (isNaN(date.getTime())) return ''

    const year = date.getFullYear()
    const month = String(date.getMonth() + 1).padStart(2, '0')
    const day = String(date.getDate()).padStart(2, '0')
    const hours = String(date.getHours()).padStart(2, '0')
    const minutes = String(date.getMinutes()).padStart(2, '0')

    return `${year}-${month}-${day} ${hours}:${minutes}`
  } catch {
    return ''
  }
}

/**
 * 格式化日期 (仅日期,YYYY-MM-DD,用于日期列/按日分组标签)
 */
export function formatDay(dateStr: string | Date | null | undefined): string {
  if (!dateStr) return '-'
  try {
    const date = typeof dateStr === 'string' ? new Date(dateStr) : dateStr
    if (isNaN(date.getTime())) return '-'
    const month = String(date.getMonth() + 1).padStart(2, '0')
    const day = String(date.getDate()).padStart(2, '0')
    return `${date.getFullYear()}-${month}-${day}`
  } catch {
    return '-'
  }
}

/**
 * 格式化数字（添加千分位）
 */
export function formatNumber(num: number | string | null | undefined): string {
  if (num === null || num === undefined) return '0'

  const n = typeof num === 'string' ? parseFloat(num) : num

  if (isNaN(n)) return '0'

  return n.toLocaleString('zh-CN')
}

/**
 * 定点小数(字符串入参安全,NaN→0.00):AccountInfo 域余额/持仓展示
 * (后端金额为字符串,须先 parseFloat 再 toFixed)
 */
export function formatFixed(num: string | number, decimals = 2): string {
  const n = typeof num === 'string' ? parseFloat(num) : num
  if (isNaN(n)) return (0).toFixed(decimals)
  return n.toFixed(decimals)
}

/**
 * 格式化百分比
 */
export function formatPercent(val: number | string | null | undefined, decimals = 2): string {
  if (val == null) return '-'

  const n = typeof val === 'string' ? parseFloat(val) : val

  if (isNaN(n)) return '-'

  return (n * 100).toFixed(decimals) + '%'
}

/**
 * 格式化大数字为中文缩写(万/亿),用于资金·成交量·市值等大额场景。
 * 例:formatCompact(1234567) → "123.46万",formatCompact(1.23e8) → "1.23亿"
 * 小于万的数走千分位,与 formatNumber 一致,保持列内对齐。
 */
export function formatCompact(num: number | string | null | undefined, decimals = 2): string {
  if (num === null || num === undefined) return '-'
  const n = typeof num === 'string' ? parseFloat(num) : num
  if (isNaN(n)) return '-'
  const abs = Math.abs(n)
  if (abs >= 1e8) return (n / 1e8).toFixed(decimals) + '亿'
  if (abs >= 1e4) return (n / 1e4).toFixed(decimals) + '万'
  return n.toLocaleString('zh-CN')
}

/**
 * 格式化持续时间
 */
export function formatDuration(seconds?: number): string {
  if (!seconds) return '-'
  if (seconds < 60) return `${seconds}秒`
  if (seconds < 3600) return `${Math.floor(seconds / 60)}分${seconds % 60}秒`
  return `${Math.floor(seconds / 3600)}时${Math.floor((seconds % 3600) / 60)}分`
}

/**
 * 格式化日期时间 (短格式，用于表格)
 */
export function formatDateTime(dateStr?: string): string {
  if (!dateStr) return '-'

  try {
    const date = new Date(dateStr)
    if (isNaN(date.getTime())) return '-'

    const month = date.getMonth() + 1
    const day = date.getDate()
    const hours = String(date.getHours()).padStart(2, '0')
    const minutes = String(date.getMinutes()).padStart(2, '0')
    const seconds = String(date.getSeconds()).padStart(2, '0')

    return `${month}/${day} ${hours}:${minutes}:${seconds}`
  } catch {
    return '-'
  }
}

/**
 * 格式化相对时间（用于心跳/时间戳新鲜度，"3秒前" / "5分钟前" / "2天前"）
 * 超过 30 天回退为日期时间短格式
 */
export function formatRelativeTime(dateStr?: string | null, now: Date = new Date()): string {
  if (!dateStr) return '-'

  try {
    const date = new Date(dateStr)
    const ms = date.getTime()
    if (isNaN(ms)) return '-'

    const diff = Math.floor((now.getTime() - ms) / 1000)
    if (diff < 0) return formatDateTime(dateStr)
    if (diff < 60) return `${diff}秒前`
    if (diff < 3600) return `${Math.floor(diff / 60)}分钟前`
    if (diff < 86400) return `${Math.floor(diff / 3600)}小时前`
    if (diff < 2592000) return `${Math.floor(diff / 86400)}天前`
    return formatDateTime(dateStr)
  } catch {
    return '-'
  }
}

/**
 * 心跳 stale 分级（对齐 backtest worker 心跳节奏：interval=10s、ttl=30s）
 * 0=新鲜 | 1=超 TTL 30s（橙） | 2=超两倍 TTL 60s（红）
 */
export function heartbeatStaleLevel(dateStr?: string | null, now: Date = new Date()): 0 | 1 | 2 {
  if (!dateStr) return 0

  try {
    const ms = new Date(dateStr).getTime()
    if (isNaN(ms)) return 0
    const diff = (now.getTime() - ms) / 1000
    if (diff >= 60) return 2
    if (diff >= 30) return 1
    return 0
  } catch {
    return 0
  }
}

/**
 * 格式化金额
 */
export function formatMoney(amount: number | string | null | undefined, prefix = '¥'): string {
  if (amount === null || amount === undefined) return `${prefix}0`

  const n = typeof amount === 'string' ? parseFloat(amount) : amount

  if (isNaN(n)) return `${prefix}0`

  return prefix + n.toLocaleString('zh-CN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })
}
