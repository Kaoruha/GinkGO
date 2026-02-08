/**
 * API 请求相关类型定义
 * 统一所有 API 模块的请求选项类型
 */

/**
 * 基础请求选项，支持 AbortSignal
 */
export interface RequestOptions {
  /** AbortSignal 用于取消请求 */
  signal?: AbortSignal
}

/**
 * 分页请求参数
 */
export interface PageParams {
  /** 页码，从 1 开始 */
  page?: number
  /** 每页数量 */
  page_size?: number
}

/**
 * 分页响应
 */
export interface PaginatedResponse<T> {
  /** 数据列表 */
  items: T[]
  /** 总数量 */
  total: number
  /** 当前页码 */
  page: number
  /** 每页数量 */
  page_size: number
  /** 总页数 */
  total_pages: number
}

/**
 * API 响应基础类型
 */
export interface APIResponse<T> {
  /** 响应数据 */
  data: T
  /** 响应消息 */
  message?: string
  /** 响应代码 */
  code?: number
}

/**
 * 请求错误类型
 */
export interface RequestError extends Error {
  /** 错误名称 */
  name: string
  /** 错误消息 */
  message: string
  /** 错误代码 */
  code?: string
  /** 响应状态码 */
  status?: number
  /** 是否为取消操作 */
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
