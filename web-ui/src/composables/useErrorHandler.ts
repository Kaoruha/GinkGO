<<<<<<< HEAD
/**
 * 错误处理 Composable
 *
 * 提供 Vue 组件中的错误处理状态管理和自动化错误处理功能。
 */

import { ref, type Ref } from 'vue'
import { handleApiError } from '@/utils/errorHandler'

export interface UseErrorHandlerReturn {
  /** 错误对象 */
  error: Ref<any>
  /** 加载状态 */
  loading: Ref<boolean>
  /** 清除错误 */
  clearError: () => void
  /** 执行异步操作并自动处理错误 */
  execute: <T>(fn: () => Promise<T>, showMessage?: boolean) => Promise<T | null>
  /** 手动处理错误 */
  handleError: (err: any, showMessage?: boolean) => void
}

/**
 * 错误处理 Composable
 *
 * @param initialLoading - 初始加载状态（默认 false）
 * @returns 错误处理对象
 *
 * @example
 * ```ts
 * const { error, loading, execute, clearError } = useErrorHandler()
 *
 * async function loadData() {
 *   const result = await execute(async () => {
 *     return await portfolioApi.list()
 *   })
 *
 *   if (result) {
 *     // 处理成功结果
 *   } else {
 *     // 错误已被自动处理
 *     if (error.value) {
 *       console.log('操作失败:', error.value)
 *     }
 *   }
 * }
 * ```
 */
export function useErrorHandler(initialLoading: boolean = false): UseErrorHandlerReturn {
  const error = ref<any>(null)
  const loading = ref<boolean>(initialLoading)

  /**
   * 清除错误状态
   */
  function clearError(): void {
    error.value = null
=======
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
>>>>>>> 011-quant-research
  }

  /**
   * 执行异步操作并自动处理错误
<<<<<<< HEAD
   *
   * @param fn - 异步函数
   * @param showMessage - 是否显示错误消息（默认 true）
   * @returns 函数执行结果，错误时返回 null
   */
  async function execute<T>(
    fn: () => Promise<T>,
    showMessage: boolean = true
  ): Promise<T | null> {
    loading.value = true
    error.value = null

    try {
      const result = await fn()
      return result
    } catch (err) {
      error.value = err
      handleApiError(err, showMessage)
=======
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
>>>>>>> 011-quant-research
      return null
    } finally {
      loading.value = false
    }
  }

<<<<<<< HEAD
  /**
   * 手动处理错误
   *
   * @param err - 错误对象
   * @param showMessage - 是否显示错误消息（默认 true）
   */
  function handleError(err: any, showMessage: boolean = true): void {
    error.value = err
    handleApiError(err, showMessage)
  }

  return {
    error,
    loading,
    clearError,
    execute,
    handleError
  }
}

/**
 * 批量错误处理 Composable
 *
 * 用于管理多个异步操作的错误状态。
 *
 * @param count - 操作数量
 * @returns 批量错误处理对象
 *
 * @example
 * ```ts
 * const { errors, loading, executeAll, clearErrors } = useBatchErrorHandler(3)
 *
 * await executeAll([
 *   () => portfolioApi.get(uuid1),
 *   () => portfolioApi.get(uuid2),
 *   () => portfolioApi.get(uuid3)
 * ])
 *
 * // 检查哪些操作失败了
 * errors.forEach((err, index) => {
 *   if (err) {
 *     console.log(`操作 ${index} 失败:`, err)
 *   }
 * })
 * ```
 */
export function useBatchErrorHandler(count: number) {
  const errors = ref<any[]>(new Array(count).fill(null))
  const loading = ref<boolean>(false)

  /**
   * 清除所有错误
   */
  function clearErrors(): void {
    errors.value = new Array(count).fill(null)
  }

  /**
   * 批量执行异步操作
   *
   * @param fns - 异步函数数组
   * @param showMessages - 是否显示错误消息（默认 true）
   * @returns 所有操作的结果数组
   */
  async function executeAll<T>(
    fns: Array<() => Promise<T>>,
    showMessages: boolean = true
  ): Promise<Array<T | null>> {
    loading.value = true
    clearErrors()

    const results: Array<T | null> = []

    for (let i = 0; i < fns.length; i++) {
      try {
        const result = await fns[i]()
        results[i] = result
      } catch (err) {
        errors.value[i] = err
        results[i] = null
        if (showMessages) {
          handleApiError(err)
        }
      }
    }

    loading.value = false
    return results
  }

  return {
    errors,
    loading,
    clearErrors,
    executeAll
  }
}

/**
 * 表单错误处理 Composable
 *
 * 专门用于表单提交的错误处理。
 *
 * @returns 表单错误处理对象
 *
 * @example
 * ```ts
 * const { error, loading, submit, reset } = useFormErrorHandler()
 *
 * async function handleSubmit() {
 *   const result = await submit(async () => {
 *     return await portfolioApi.create(formData)
 *   })
 *
 *   if (result) {
 *     message.success('创建成功')
 *     reset()
 *   }
 * }
 * ```
 */
export function useFormErrorHandler() {
  const { error, loading, execute, clearError } = useErrorHandler()

  /**
   * 提交表单
   *
   * @param fn - 提交函数
   * @param showSuccessMessage - 成功时是否显示消息（默认 false，由调用方处理）
   * @returns 提交结果
   */
  async function submit<T>(
    fn: () => Promise<T>,
    showSuccessMessage: boolean = false
  ): Promise<T | null> {
    const result = await execute(fn)

    if (result && showSuccessMessage) {
      // 这里可以添加默认的成功消息
      // 默认情况下由调用方处理成功消息
    }

    return result
  }

  /**
   * 重置表单状态
   */
  function reset(): void {
    clearError()
  }

  return {
    error,
    loading,
    submit,
    reset,
    clearError
=======
  const reset = () => {
    loading.value = false
    error.value = null
  }

  return {
    loading,
    error,
    submit,
    reset,
>>>>>>> 011-quant-research
  }
}
