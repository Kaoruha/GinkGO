/**
 * API 通用类型定义
 */

/**
 * 分页参数
 */
export interface PaginationParams {
  page?: number
  pageSize?: number
  sortField?: string
  sortOrder?: 'ascend' | 'descend'
}

/**
 * 分页响应
 */
export interface PaginatedResponse<T> {
  items: T[]
  total: number
  page: number
  pageSize: number
}

/**
 * API 统一响应格式
 */
export interface APIResponse<T> {
  success: boolean
  data: T
  error?: string
  message?: string
}

/**
 * 通用错误响应
 */
export interface ErrorResponse {
  success: false
  data: null
  error: string
  message: string
}

/**
 * 列表查询参数
 */
export interface ListParams extends PaginationParams {
  keyword?: string
  status?: string
  startDate?: string
  endDate?: string
}
