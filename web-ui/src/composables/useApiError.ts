import { ref } from 'vue'
import { message } from '@/utils/toast'

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

  const errorMessage = ref('')

  /**
   * 处理 API 错误
   */
  const handleError = (error: any, defaultMessage = '操作失败'): string => {
    let msg = defaultMessage

    if (error.response) {
      const status = error.response.status
      const data = error.response.data

      // 业务错误处理
      switch (status) {
        case 400:
          msg = data?.message || '请求参数错误'
          break
        case 401:
          msg = '登录已过期'
          break
        case 403:
          msg = '没有权限'
          break
        case 404:
          msg = '资源不存在'
          break
        case 500:
          msg = '服务器错误'
          break
        default:
          msg = data?.message || msg
      }
    } else if (error.request) {
      msg = '网络连接失败'
    } else {
      msg = error.message || msg
    }

    errorMessage.value = msg

    if (showMessage) {
      message.error(msg)
    }

    return msg
  }

  const clearError = () => {
    errorMessage.value = ''
  }

  return {
    handleError,
    errorMessage,
    clearError,
  }
}
