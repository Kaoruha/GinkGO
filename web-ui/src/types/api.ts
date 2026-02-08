/**
 * 统一 API 响应类型
 *
 * 定义所有 API 端点返回的统一响应格式。
 */

/**
 * 基础 API 响应格式
 */
export interface APIResponse<T> {
  success: boolean
  data?: T
  error?: string
  message?: string
}

/**
 * 分页数据容器
 */
export interface PaginatedData<T> {
  items: T[]
  total: number
  page: number
  page_size: number
  total_pages: number
}

/**
 * 分页响应格式
 */
export interface PaginatedResponse<T> {
  success: boolean
  data: PaginatedData<T>
  message?: string
}

/**
 * API 错误信息
 */
export interface APIError {
  success: false
  data: null
  error: string
  message: string
}

/**
 * 标准化的 API 错误对象
 * 用于错误处理和用户提示
 */
export interface ApiError {
  code: string
  message: string
  details?: any
}

/**
 * 判断响应是否为成功响应
 */
export function isSuccessResponse<T>(response: APIResponse<T> | APIError): response is APIResponse<T> {
  return response.success === true && response.data !== undefined
}

/**
 * 判断响应是否为错误响应
 */
export function isErrorResponse(response: APIResponse<unknown> | APIError): response is APIError {
  return response.success === false
}

/**
 * 从 API 响应中提取数据，如果响应失败则抛出错误
 */
export function extractData<T>(response: APIResponse<T>): T {
  if (!response.success || response.data === undefined) {
    throw new Error(response.message || response.error || 'Unknown API error')
  }
  return response.data
}

/**
 * 创建成功响应（用于测试或模拟数据）
 */
export function createSuccessResponse<T>(data: T, message?: string): APIResponse<T> {
  return {
    success: true,
    data,
    error: undefined,
    message
  }
}

/**
 * 创建错误响应（用于测试或模拟数据）
 */
export function createErrorResponse(error: string, message?: string): APIError {
  return {
    success: false,
    data: null,
    error,
    message: message || error
  }
}

/**
 * 创建分页响应（用于测试或模拟数据）
 */
export function createPaginatedResponse<T>(
  items: T[],
  total: number,
  page: number = 1,
  page_size: number = 20,
  message?: string
): PaginatedResponse<T> {
  const total_pages = Math.ceil(total / page_size)
  return {
    success: true,
    data: {
      items,
      total,
      page,
      page_size,
      total_pages
    },
    message
  }
}
