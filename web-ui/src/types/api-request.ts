/**
 * API 请求相关类型定义
 */

export type { PaginationMeta } from './api'

/**
 * 基础请求选项，支持 AbortSignal
 */
export interface RequestOptions {
  signal?: AbortSignal
}

/**
 * 分页请求参数
 */
export interface PageParams {
  page?: number
  page_size?: number
}

/**
 * 请求错误类型
 */
export interface RequestError extends Error {
  name: string
  message: string
  code?: string
  status?: number
  isCanceled?: boolean
}

/**
 * 判断错误是否为取消操作
 */
export function isAbortError(error: any): error is RequestError {
  return error?.name === 'AbortError' || error?.isCanceled === true
}

/**
 * 创建取消错误
 */
export function createAbortError(message: string = '请求已取消'): RequestError {
  const error = new Error(message) as RequestError
  error.name = 'AbortError'
  error.isCanceled = true
  return error
}
