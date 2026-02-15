import { ref } from 'vue'
import { message } from 'ant-design-vue'

/**
 * 简化的 API 错误处理 composable
 * 提供统一的错误处理逻辑
 */

export interface ApiErrorOptions {
  showMessage?: boolean
}

export function useApiError(options: ApiErrorOptions = {}) {
  const {
    showMessage = true
  } = options

  /**
   * 处理 API 错误
   */
  const handleError = (error: any, defaultMessage = '操作失败') => {
    let errorMessage = defaultMessage

    if (error.response) {
      const status = error.response.status
      const data = error.response.data

      // 业务错误处理
      switch (status) {
        case 400:
          errorMessage = data?.message || '请求参数错误'
          break
        case 401:
          errorMessage = '登录已过期'
          break
        case 403:
          errorMessage = '没有权限'
          break
        case 404:
          errorMessage = '资源不存在'
          break
        case 500:
          errorMessage = '服务器错误'
          break
        default:
          errorMessage = data?.message || errorMessage
      }
    } else if (error.request) {
      errorMessage = '网络连接失败'
    } else {
      errorMessage = error.message || errorMessage
    }

    if (showMessage) {
      message.error(errorMessage)
    }

    return errorMessage
  }

  return {
    handleError,
    errorMessage: ref(''),
    clearError: () => {
      errorMessage.value = ''
    }
  }
}
