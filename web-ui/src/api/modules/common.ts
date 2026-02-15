import request from '../modules/core/request'
import type { APIResponse, PaginatedResponse } from '../../types/common'

/**
 * 通用 API 请求方法
 */

/**
 * GET 请求封装
 */
export function get<T>(url: string, params?: Record<string, any>): Promise<APIResponse<T>> {
  return request({
    url,
    method: 'GET',
    params
  })
}

/**
 * POST 请求封装
 */
export function post<T>(url: string, data?: any): Promise<APIResponse<T>> {
  return request({
    url,
    method: 'POST',
    data
  })
}

/**
 * PUT 请求封装
 */
export function put<T>(url: string, data?: any): Promise<APIResponse<T>> {
  return request({
    url,
    method: 'PUT',
    data
  })
}

/**
 * DELETE 请求封装
 */
export function del<T>(url: string): Promise<APIResponse<T>> {
  return request({
    url,
    method: 'DELETE'
  })
}

/**
 * 分页查询封装
 */
export function getList<T>(url: string, params?: {
  page?: number
  pageSize?: number
  keyword?: string
}): Promise<APIResponse<PaginatedResponse<T>>> {
  return get<PaginatedResponse<T>>(url, params)
}

/**
 * 文件上传封装
 */
export function upload<T>(url: string, file: File, onProgress?: (percent: number) => void): Promise<APIResponse<T>> {
  const formData = new FormData()
  formData.append('file', file)

  return request({
    url,
    method: 'POST',
    data: formData,
    headers: {
      'Content-Type': 'multipart/form-data'
    },
    onUploadProgress: (progressEvent) => {
      if (onProgress && progressEvent.total) {
        const percent = Math.round((progressEvent.loaded / progressEvent.total) * 100)
        onProgress(percent)
      }
    }
  })
}
