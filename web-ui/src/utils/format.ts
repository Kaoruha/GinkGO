/**
<<<<<<< HEAD
 * 通用格式化工具函数
 */

import dayjs from 'dayjs'

/**
 * 格式化日期时间
 */
export function formatDate(date: string | Date | null | undefined, format = 'YYYY-MM-DD HH:mm:ss'): string {
  if (!date) return '-'
  return dayjs(date).format(format)
}

/**
 * 格式化日期（仅日期）
 */
export function formatDateOnly(date: string | Date | null | undefined): string {
  return formatDate(date, 'YYYY-MM-DD')
}

/**
 * 格式化日期时间（不含秒）
 */
export function formatDateDateTime(date: string | Date | null | undefined): string {
  return formatDate(date, 'YYYY-MM-DD HH:mm')
}

/**
 * 格式化日期时间（含秒）
 */
export function formatDateTime(date: string | Date | null | undefined): string {
  return formatDate(date, 'YYYY-MM-DD HH:mm:ss')
}

/**
 * 格式化金额
 */
export function formatAmount(amount: number | null | undefined): string {
  if (amount == null) return '-'
  return amount.toLocaleString('zh-CN', {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2
  })
=======
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
 * 格式化数字（添加千分位）
 */
export function formatNumber(num: number | string | null | undefined): string {
  if (num === null || num === undefined) return '0'

  const n = typeof num === 'string' ? parseFloat(num) : num

  if (isNaN(n)) return '0'

  return n.toLocaleString('zh-CN')
>>>>>>> 011-quant-research
}

/**
 * 格式化百分比
 */
<<<<<<< HEAD
export function formatPercent(value: number | null | undefined, decimals = 2): string {
  if (value == null) return '-'
  return `${(value * 100).toFixed(decimals)}%`
}

/**
 * 格式化数字（整数不显示小数）
 */
export function formatDecimal(value: number | null | undefined, decimals = 4): string {
  if (value == null) return '-'
  if (Number.isInteger(value)) return value.toString()
  return parseFloat(value.toFixed(decimals)).toString()
}

/**
 * 格式化文件大小
 */
export function formatFileSize(bytes: number): string {
  if (bytes === 0) return '0 B'
  const k = 1024
  const sizes = ['B', 'KB', 'MB', 'GB', 'TB']
  const i = Math.floor(Math.log(bytes) / Math.log(k))
  return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i]
}

/**
 * 格式化数字（千分位）
 */
export function formatNumber(num: number, decimals = 2): string {
  return num.toLocaleString('zh-CN', {
    minimumFractionDigits: decimals,
    maximumFractionDigits: decimals
  })
}

/**
 * 格式化相对时间
 * 需要先配置 dayjs: dayjs.extend(relativeTime); dayjs.locale('zh-cn')
 */
export function formatRelativeTime(date: string | Date | null | undefined): string {
  if (!date) return '-'
  return dayjs(date).fromNow()
=======
export function formatPercent(val: number | string, decimals = 2): string {
  if (val === null || val === undefined) return '-'

  const n = typeof val === 'string' ? parseFloat(val) : val

  if (isNaN(n)) return '-'

  return (n * 100).toFixed(decimals) + '%'
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
 * 格式化金额
 */
export function formatMoney(amount: number | string | null | undefined, prefix = '¥'): string {
  if (amount === null || amount === undefined) return `${prefix}0`

  const n = typeof amount === 'string' ? parseFloat(amount) : amount

  if (isNaN(n)) return `${prefix}0`

  return prefix + n.toLocaleString('zh-CN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })
>>>>>>> 011-quant-research
}
