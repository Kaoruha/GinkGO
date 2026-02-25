import { ref } from 'vue'
import { message } from 'ant-design-vue'

export interface AppError {
  message: string
  code?: string
  details?: any
}

export function useErrorHandler() {
  const error = ref<AppError | null>(null)
  const isError = ref(false)

  const setError = (err: AppError | string) => {
    if (typeof err === 'string') {
      error.value = { message: err }
    } else {
      error.value = err
    }
    isError.value = true
  }

  const clearError = () => {
    error.value = null
    isError.value = false
  }

  /**
   * 执行异步操作并自动处理错误
   */
  const execute = async <T>(
    fn: () => Promise<T>,
    options?: {
      onSuccess?: (result: T) => void
      onError?: (err: any) => void
      showError?: boolean
      errorMessage?: string
    }
  ): Promise<T | null> => {
    clearError()
    try {
      const result = await fn()
      options?.onSuccess?.(result)
      return result
    } catch (err: any) {
      const errorMsg = err.message || err.error || options?.errorMessage || '操作失败'
      setError({ message: errorMsg, code: err.code, details: err.details })

      if (options?.showError !== false) {
        message.error(errorMsg)
      }

      options?.onError?.(err)
      return null
    }
  }

  /**
   * 包装异步函数，自动处理错误
   */
  const wrap = <T extends (...args: any[]) => Promise<any>>(
    fn: T,
    options?: {
      onSuccess?: (result: any) => void
      onError?: (err: any) => void
      showError?: boolean
    }
  ): T => {
    return (async (...args: any[]) => {
      return execute(() => fn(...args), options)
    }) as T
  }

  return {
    error,
    isError,
    setError,
    clearError,
    execute,
    wrap,
  }
}

/**
 * 表单错误处理 composable
 */
export function useFormErrorHandler() {
  const loading = ref(false)
  const error = ref<string | null>(null)

  const submit = async <T>(fn: () => Promise<T>): Promise<T | null> => {
    loading.value = true
    error.value = null
    try {
      const result = await fn()
      return result
    } catch (err: any) {
      error.value = err.message || '操作失败'
      message.error(error.value)
      return null
    } finally {
      loading.value = false
    }
  }

  const reset = () => {
    loading.value = false
    error.value = null
  }

  return {
    loading,
    error,
    submit,
    reset,
  }
}
