/**
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
}

/**
 * 格式化百分比
 */
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
}
