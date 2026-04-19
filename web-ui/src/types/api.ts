/**
 * 统一 API 响应类型
 *
 * 所有 API 端点返回统一格式:
 * {code: 0, data: T, message: "ok", meta?: PaginationMeta, trace_id: "..."}
 */

/**
 * 分页元数据
 */
export interface PaginationMeta {
  page: number
  page_size: number
  total: number
  total_pages: number
}

/**
 * 统一 API 响应格式
 */
export interface APIResponse<T> {
  /** 0=成功, 非零=错误码 */
  code: number
  /** 业务数据 */
  data: T
  /** 描述信息 */
  message: string
  /** 分页元数据（仅分页接口） */
  meta?: PaginationMeta
  /** 请求追踪ID */
  trace_id: string
}

/**
 * 分页响应的 data 类型（拦截器拆包后）
 */
export interface PaginatedData<T> {
  items: T[]
  total: number
  page: number
  page_size: number
  total_pages: number
}

/**
 * 判断响应是否成功
 */
export function isOk<T>(response: APIResponse<T>): response is APIResponse<T> & { code: 0 } {
  return response.code === 0
}
