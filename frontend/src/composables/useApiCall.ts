/**
 * 统一的API调用处理composable
 * 用于减少各组件中重复的异步调用逻辑
 */
import { ref, Ref } from 'vue'
import { handleApiError } from '@/utils/errorHandler'

/**
 * API调用状态接口
 */
interface ApiCallState<T> {
  data: Ref<T | null>
  loading: Ref<boolean>
  error: Ref<string | null>
  execute: (apiFn: () => Promise<T>, errorHandler?: (err: any) => void) => Promise<T | null>
  reset: () => void
}

/**
 * API调用配置选项
 */
interface ApiCallOptions {
  onSuccess?: (data: any) => void
  onError?: (error: string) => void
  showGlobalError?: boolean // 是否显示全局错误提示
}

/**
 * 统一的API调用处理composable
 * @param options 配置选项
 * @returns API调用状态和方法
 */
export function useApiCall<T = any>(options: ApiCallOptions = {}): ApiCallState<T> {
  const data = ref<T | null>(null)
  const loading = ref(false)
  const error = ref<string | null>(null)

  /**
   * 执行API调用
   * @param apiFn API函数
   * @param errorHandler 自定义错误处理器
   * @returns API响应数据或null
   */
  async function execute(
    apiFn: () => Promise<T>,
    errorHandler?: (err: any) => void
  ): Promise<T | null> {
    loading.value = true
    error.value = null

    try {
      const result = await apiFn()
      data.value = result

      // 成功回调
      if (options.onSuccess) {
        options.onSuccess(result)
      }

      return result
    } catch (err: any) {
      const errorMessage = handleApiError(err, '操作失败')
      error.value = errorMessage

      // 错误回调
      if (errorHandler) {
        errorHandler(err)
      } else if (options.onError) {
        options.onError(errorMessage)
      }

      return null
    } finally {
      loading.value = false
    }
  }

  /**
   * 重置状态
   */
  function reset() {
    data.value = null
    loading.value = false
    error.value = null
  }

  return {
    data,
    loading,
    error,
    execute,
    reset
  }
}

/**
 * 批量API调用处理composable
 * 用于处理多个并发API请求
 */
export function useBatchApiCall<T = any>() {
  const loading = ref(false)
  const progress = ref(0)
  const errors = ref<Array<{ index: number; error: string }>>([])

  /**
   * 执行批量API调用
   * @param apiCalls API函数数组
   * @returns 批量调用结果
   */
  async function executeBatch(
    apiCalls: Array<() => Promise<T>>
  ): Promise<{
    results: Array<T | null>
    successCount: number
    failCount: number
  }> {
    loading.value = true
    progress.value = 0
    errors.value = []

    const results: Array<T | null> = []

    for (let i = 0; i < apiCalls.length; i++) {
      try {
        const result = await apiCalls[i]()
        results.push(result)
        progress.value = ((i + 1) / apiCalls.length) * 100
      } catch (err: any) {
        results.push(null)
        errors.value.push({
          index: i,
          error: handleApiError(err, '请求失败')
        })
      }
    }

    loading.value = false

    return {
      results,
      successCount: results.filter(r => r !== null).length,
      failCount: results.filter(r => r === null).length
    }
  }

  return {
    loading,
    progress,
    errors,
    executeBatch
  }
}