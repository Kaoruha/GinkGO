/**
 * API 通用类型定义（旧文件，类型已迁移到 @/types/api.ts）
 * 保留分页参数类型供兼容使用
 */

export interface PaginationParams {
  page?: number
  pageSize?: number
  sortField?: string
  sortOrder?: 'ascend' | 'descend'
}

export interface ListParams extends PaginationParams {
  keyword?: string
  status?: string
  startDate?: string
  endDate?: string
}
