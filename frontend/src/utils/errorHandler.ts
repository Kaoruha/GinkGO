/**
 * 统一的错误处理工具库
 * 用于减少前端各组件中重复的错误处理逻辑
 */

/**
 * API错误响应接口
 */
interface ApiError {
  response?: {
    data?: {
      message?: string
      detail?: string
      error?: string
    }
  }
  message?: string
}

/**
 * 从错误对象中提取用户友好的错误消息
 * @param error 错误对象
 * @param fallbackMessage 默认回退消息
 * @returns 提取的错误消息
 */
export function handleApiError(error: ApiError, fallbackMessage = '操作失败'): string {
  // 优先使用 response.data.message
  if (error?.response?.data?.message) {
    return error.response.data.message
  }

  // 其次使用 response.data.detail
  if (error?.response?.data?.detail) {
    return error.response.data.detail
  }

  // 再次使用 response.data.error
  if (error?.response?.data?.error) {
    return error.response.data.error
  }

  // 然后使用 error.message
  if (error?.message) {
    return error.message
  }

  // 最后使用默认消息
  return fallbackMessage
}

/**
 * 判断是否为网络错误
 * @param error 错误对象
 * @returns 是否为网络错误
 */
export function isNetworkError(error: ApiError): boolean {
  return !error?.response && !!error?.message
}

/**
 * 判断是否为HTTP状态错误
 * @param error 错误对象
 * @param status 期望的HTTP状态码
 * @returns 是否为指定状态错误
 */
export function isHttpStatus(error: any, status: number): boolean {
  return error?.response?.status === status
}

/**
 * 判断是否为超时错误
 * @param error 错误对象
 * @returns 是否为超时错误
 */
export function isTimeoutError(error: ApiError): boolean {
  return error?.message?.toLowerCase().includes('timeout') ||
         error?.message?.toLowerCase().includes('timed out')
}

/**
 * 错误类型枚举
 */
export enum ErrorType {
  NETWORK = 'network',
  TIMEOUT = 'timeout',
  SERVER = 'server',
  CLIENT = 'client',
  UNKNOWN = 'unknown'
}

/**
 * 获取错误类型
 * @param error 错误对象
 * @returns 错误类型
 */
export function getErrorType(error: any): ErrorType {
  if (isTimeoutError(error)) return ErrorType.TIMEOUT
  if (isNetworkError(error)) return ErrorType.NETWORK

  const status = error?.response?.status
  if (!status) return ErrorType.UNKNOWN

  if (status >= 500) return ErrorType.SERVER
  if (status >= 400) return ErrorType.CLIENT

  return ErrorType.UNKNOWN
}

/**
 * 根据错误类型获取用户友好的提示消息
 * @param errorType 错误类型
 * @returns 用户友好的提示消息
 */
export function getFriendlyErrorMessage(errorType: ErrorType): string {
  const messages: Record<ErrorType, string> = {
    [ErrorType.NETWORK]: '网络连接失败，请检查网络设置',
    [ErrorType.TIMEOUT]: '请求超时，请稍后重试',
    [ErrorType.SERVER]: '服务器异常，请联系管理员',
    [ErrorType.CLIENT]: '请求参数错误，请检查输入',
    [ErrorType.UNKNOWN]: '操作失败，请稍后重试'
  }
  return messages[errorType] || messages[ErrorType.UNKNOWN]
}