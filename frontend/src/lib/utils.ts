import { type ClassValue, clsx } from 'clsx'
import { twMerge } from 'tailwind-merge'

/**
 * 合并 Tailwind CSS 类名的工具函数
 * 使用 clsx 处理条件类名，然后用 tailwind-merge 解决冲突
 *
 * @param inputs - 类名或类名数组
 * @returns 合并后的类名字符串
 *
 * @example
 * cn('px-2', 'py-1', someCondition && 'bg-blue-500')
 * // => 'px-2 py-1 bg-blue-500' (当 someCondition 为 true)
 */
export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs))
}

/**
 * 格式化日期时间为本地字符串
 *
 * @param dateTime - 日期时间字符串或Date对象
 * @returns 格式化后的日期时间字符串
 */
export function formatDateTime(dateTime: string | Date | null | undefined): string {
  if (!dateTime) return '-'
  return new Date(dateTime).toLocaleString('zh-CN')
}

/**
 * 获取状态对应的颜色
 *
 * @param status - 状态字符串
 * @returns Tailwind 颜色类名
 */
export function getStatusColor(status: string): string {
  const colorMap: Record<string, string> = {
    enabled: 'text-green-600',
    disabled: 'text-gray-400',
    connecting: 'text-blue-600',
    connected: 'text-green-600',
    disconnected: 'text-yellow-600',
    error: 'text-red-600',
    active: 'text-green-600',
    inactive: 'text-gray-400',
  }
  return colorMap[status] || 'text-gray-600'
}

/**
 * 获取状态对应的背景色
 *
 * @param status - 状态字符串
 * @returns Tailwind 背景颜色类名
 */
export function getStatusBgColor(status: string): string {
  const colorMap: Record<string, string> = {
    enabled: 'bg-green-100',
    disabled: 'bg-gray-100',
    connecting: 'bg-blue-100',
    connected: 'bg-green-100',
    disconnected: 'bg-yellow-100',
    error: 'bg-red-100',
    active: 'bg-green-100',
    inactive: 'bg-gray-100',
  }
  return colorMap[status] || 'bg-gray-100'
}
