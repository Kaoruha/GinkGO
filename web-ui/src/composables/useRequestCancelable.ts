import { ref, onUnmounted, type Ref } from 'vue'

/**
 * 可取消请求的 Composable
 * 基于 AbortController 实现请求取消机制
 *
 * @example
 * const { loading, error, execute, cancel } = useRequestCancelable()
 *
 * // 发起请求
 * await execute(
 *   (signal) => api.getData({ signal }),
 *   {
 *     onSuccess: (data) => console.log(data),
 *     onError: (err) => console.error(err)
 *   }
 * )
 *
 * // 手动取消请求
 * cancel()
 */
export interface RequestOptions<T> {
  /** 成功回调 */
  onSuccess?: (data: T) => void
  /** 错误回调 */
  onError?: (error: any) => void
  /** 最终回调 */
  onFinally?: () => void
}

export function useRequestCancelable() {
  const controller = ref<AbortController | null>(null)
  const loading = ref(false)
  const error = ref<any>(null)

  /**
   * 执行可取消的请求
   * @param requestFn 接收 AbortSignal 的请求函数
   * @param options 可选的回调配置
   * @returns 请求结果，取消时返回 null
   */
  async function execute<T>(
    requestFn: (signal: AbortSignal) => Promise<T>,
    options?: RequestOptions<T>
  ): Promise<T | null> {
    // 取消之前的请求
    cancel()

    // 创建新的 AbortController
    controller.value = new AbortController()
    loading.value = true
    error.value = null

    try {
      const result = await requestFn(controller.value.signal)
      options?.onSuccess?.(result)
      return result
    } catch (err: any) {
      // 如果是取消操作，静默处理
      if (err.name === 'AbortError') {
        console.log('请求已取消')
        return null
      }
      error.value = err
      options?.onError?.(err)
      throw err
    } finally {
      loading.value = false
      controller.value = null
      options?.onFinally?.()
    }
  }

  /**
   * 取消当前请求
   */
  function cancel() {
    if (controller.value) {
      controller.value.abort()
      controller.value = null
      loading.value = false
    }
  }

  /**
   * 组件卸载时自动取消请求
   */
  onUnmounted(() => {
    cancel()
  })

  return {
    loading,
    error,
    execute,
    cancel
  }
}

/**
 * 为多个并发请求提供可取消机制的 Composable
 * 允许同时发起多个请求，并能一键取消所有请求
 */
export function useMultiRequestCancelable() {
  const controllers = ref<Map<string, AbortController>>(new Map())
  const loadingStates = ref<Record<string, boolean>>({})
  const errors = ref<Record<string, any>>({})

  /**
   * 执行命名请求
   * @param key 请求唯一标识
   * @param requestFn 接收 AbortSignal 的请求函数
   * @param options 可选的回调配置
   */
  async function execute<T>(
    key: string,
    requestFn: (signal: AbortSignal) => Promise<T>,
    options?: RequestOptions<T>
  ): Promise<T | null> {
    // 取消该 key 之前的请求
    cancel(key)

    // 创建新的 AbortController
    const controller = new AbortController()
    controllers.value.set(key, controller)
    loadingStates.value[key] = true
    delete errors.value[key]

    try {
      const result = await requestFn(controller.signal)
      options?.onSuccess?.(result)
      return result
    } catch (err: any) {
      if (err.name === 'AbortError') {
        console.log(`请求 [${key}] 已取消`)
        return null
      }
      errors.value[key] = err
      options?.onError?.(err)
      throw err
    } finally {
      loadingStates.value[key] = false
      controllers.value.delete(key)
      options?.onFinally?.()
    }
  }

  /**
   * 取消指定请求
   * @param key 请求标识，不传则取消所有请求
   */
  function cancel(key?: string) {
    if (key) {
      const controller = controllers.value.get(key)
      if (controller) {
        controller.abort()
        controllers.value.delete(key)
        loadingStates.value[key] = false
      }
    } else {
      // 取消所有请求
      controllers.value.forEach((controller) => controller.abort())
      controllers.value.clear()
      Object.keys(loadingStates.value).forEach((k) => {
        loadingStates.value[k] = false
      })
    }
  }

  /**
   * 获取指定请求的加载状态
   */
  function isLoading(key: string): boolean {
    return loadingStates.value[key] || false
  }

  /**
   * 获取指定请求的错误信息
   */
  function getError(key: string): any {
    return errors.value[key]
  }

  /**
   * 组件卸载时取消所有请求
   */
  onUnmounted(() => {
    cancel()
  })

  return {
    loadingStates,
    errors,
    execute,
    cancel,
    isLoading,
    getError
  }
}

export default useRequestCancelable
