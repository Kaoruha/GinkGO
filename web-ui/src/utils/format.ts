/**
 * 格式化工具函数
 */

/**
 * 格式化日期
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
}
