/**
 * 统一错误处理器
 *
 * 提供 API 错误的统一处理机制，包括错误分类、友好消息映射和自动化错误处理。
 */

import { message } from 'ant-design-vue'
import type { AxiosError } from 'axios'

/**
 * 错误码枚举
 */
export enum ErrorCode {
  // 网络错误
  NETWORK_ERROR = 'NETWORK_ERROR',
  TIMEOUT_ERROR = 'TIMEOUT_ERROR',

  // 客户端错误
  NOT_FOUND = 'NOT_FOUND',
  VALIDATION_ERROR = 'VALIDATION_ERROR',
  UNAUTHORIZED = 'UNAUTHORIZED',
  FORBIDDEN = 'FORBIDDEN',

  // 服务端错误
  INTERNAL_ERROR = 'INTERNAL_ERROR',
  SERVICE_UNAVAILABLE = 'SERVICE_UNAVAILABLE',

  // 业务错误
  BUSINESS_ERROR = 'BUSINESS_ERROR',
  CONFLICT_ERROR = 'CONFLICT_ERROR',
}

/**
 * 用户友好的错误消息映射
 */
const ERROR_MESSAGES: Record<ErrorCode, string> = {
  [ErrorCode.NETWORK_ERROR]: '网络连接失败，请检查网络设置',
  [ErrorCode.TIMEOUT_ERROR]: '请求超时，请稍后重试',
  [ErrorCode.NOT_FOUND]: '请求的资源不存在',
  [ErrorCode.VALIDATION_ERROR]: '输入数据格式错误',
  [ErrorCode.UNAUTHORIZED]: '请先登录',
  [ErrorCode.FORBIDDEN]: '没有权限执行此操作',
  [ErrorCode.INTERNAL_ERROR]: '服务器内部错误',
  [ErrorCode.SERVICE_UNAVAILABLE]: '服务暂时不可用',
  [ErrorCode.BUSINESS_ERROR]: '操作失败',
  [ErrorCode.CONFLICT_ERROR]: '数据冲突，请刷新后重试',
}

/**
 * 错误严重程度
 */
export enum ErrorSeverity {
  INFO = 'info',
  WARNING = 'warning',
  ERROR = 'error',
}

/**
 * 获取错误严重程度
 */
function getErrorSeverity(code: ErrorCode): ErrorSeverity {
  switch (code) {
    case ErrorCode.NOT_FOUND:
    case ErrorCode.FORBIDDEN:
      return ErrorSeverity.WARNING
    case ErrorCode.VALIDATION_ERROR:
    case ErrorCode.UNAUTHORIZED:
    case ErrorCode.NETWORK_ERROR:
    case ErrorCode.TIMEOUT_ERROR:
    case ErrorCode.INTERNAL_ERROR:
    case ErrorCode.SERVICE_UNAVAILABLE:
    case ErrorCode.BUSINESS_ERROR:
    case ErrorCode.CONFLICT_ERROR:
    default:
      return ErrorSeverity.ERROR
  }
}

/**
 * 判断是否为取消操作错误
 */
function isAbortError(error: any): boolean {
  return error?.name === 'AbortError' ||
         error?.code === 'ERR_CANCELED' ||
         error?.message === 'canceled'
}

/**
 * 处理 API 错误
 *
 * @param error - 错误对象
 * @param showMessage - 是否显示错误消息（默认 true）
 * @param customMessage - 自定义错误消息（可选）
 */
export function handleApiError(
  error: any,
  showMessage: boolean = true,
  customMessage?: string
): void {
  console.error('API Error:', error)

  // AbortError 是取消操作，不提示错误
  if (isAbortError(error)) {
    return
  }

  // ApiError 类型（包含 code 字段）
  if (error?.code) {
    const code = error.code as ErrorCode
    const errorMessage = customMessage || error.message || ERROR_MESSAGES[code] || '操作失败'
    const severity = getErrorSeverity(code)

    if (showMessage) {
      switch (severity) {
        case ErrorSeverity.WARNING:
          message.warning(errorMessage)
          break
        case ErrorSeverity.ERROR:
          message.error(errorMessage)
          break
        default:
          message.info(errorMessage)
      }
    }

    // 特殊处理：未授权跳转登录页
    if (code === ErrorCode.UNAUTHORIZED) {
      localStorage.removeItem('access_token')
      setTimeout(() => {
        window.location.href = '/login'
      }, 1000)
    }

    return
  }

  // Axios Error
  if (error?.isAxiosError) {
    if (error.code === 'ECONNABORTED') {
      if (showMessage) {
        message.error('请求超时，请稍后重试')
      }
      return
    }

    if (error.response) {
      const status = error.response.status
      const responseMessage = (error.response.data as any)?.message

      if (showMessage) {
        switch (status) {
          case 401:
            message.error('未授权，请先登录')
            localStorage.removeItem('access_token')
            setTimeout(() => {
              window.location.href = '/login'
            }, 1000)
            break
          case 403:
            message.warning('没有权限执行此操作')
            break
          case 404:
            message.warning('请求的资源不存在')
            break
          case 409:
            message.error(responseMessage || '数据冲突，请刷新后重试')
            break
          case 500:
            message.error('服务器内部错误')
            break
          case 502:
          case 503:
          case 504:
            message.error('服务暂时不可用，请稍后重试')
            break
          default:
            message.error(responseMessage || `请求失败 (${status})`)
        }
      }
      return
    }

    if (error.request) {
      if (showMessage) {
        message.error('网络连接失败，请检查网络设置')
      }
      return
    }
  }

  // 通用 Error
  if (showMessage) {
    message.error(customMessage || error?.message || '操作失败')
  }
}

/**
 * 包装异步函数，自动处理错误
 *
 * @param fn - 异步函数
 * @param errorCallback - 自定义错误处理函数（可选）
 * @returns 包装后的函数
 */
export function withErrorHandling<T extends (...args: any[]) => Promise<any>>(
  fn: T,
  errorCallback?: (error: any) => void
): T {
  return (async (...args: any[]) => {
    try {
      return await fn(...args)
    } catch (error) {
      if (errorCallback) {
        errorCallback(error)
      } else {
        handleApiError(error)
      }
      throw error
    }
  }) as T
}

/**
 * 从 Axios 错误中提取标准错误信息
 *
 * @param error - Axios 错误对象
 * @returns 标准化的错误信息
 */
export function extractErrorInfo(error: AxiosError<any>): { code: string; message: string } {
  // 业务错误（响应体中有 error 字段）
  if (error.response?.data?.error) {
    return {
      code: error.response.data.error,
      message: error.response.data.message || '操作失败'
    }
  }

  // HTTP 状态码错误
  if (error.response?.status) {
    const status = error.response.status
    const statusMessages: Record<number, string> = {
      400: '请求参数错误',
      401: '未授权，请先登录',
      403: '没有权限执行此操作',
      404: '请求的资源不存在',
      409: '数据冲突，请刷新后重试',
      500: '服务器内部错误',
      502: '网关错误',
      503: '服务暂时不可用',
      504: '网关超时'
    }
    return {
      code: `HTTP_${status}`,
      message: statusMessages[status] || error.response.data?.message || `请求失败 (${status})`
    }
  }

  // 网络错误
  if (error.code === 'ECONNABORTED') {
    return {
      code: ErrorCode.TIMEOUT_ERROR,
      message: '请求超时，请稍后重试'
    }
  }

  if (error.request) {
    return {
      code: ErrorCode.NETWORK_ERROR,
      message: '网络连接失败，请检查网络设置'
    }
  }

  // 默认错误
  return {
    code: ErrorCode.INTERNAL_ERROR,
    message: error.message || '未知错误'
  }
}

/**
 * 创建 API 错误对象
 *
 * @param code - 错误码
 * @param message - 错误消息
 * @param details - 错误详情（可选）
 * @returns API 错误对象
 */
export function createApiError(
  code: string,
  message: string,
  details?: any
): { code: string; message: string; details?: any } {
  return { code, message, details }
}
