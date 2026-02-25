<<<<<<< HEAD
/**
 * Loading 状态管理 Composable
 *
 * 提供统一的 Loading 状态管理，支持优先级、自动清理和错误处理。
 */

import { onUnmounted } from 'vue'
import { useLoadingStore } from '@/stores/loading'

export interface LoadingOptions {
  /** loading 键名 */
  key?: string
  /** 优先级 */
  priority?: number
  /** 成功回调 */
  onSuccess?: () => void
  /** 错误回调 */
  onError?: (error: any) => void
  /** 最终回调 */
  onFinally?: () => void
}

/**
 * Loading 状态管理 Composable
 *
 * @param options - 配置选项
 * @returns Loading 管理对象
 *
 * @example
 * ```ts
 * // 基本使用
 * const { isLoading, execute } = useLoading({
 *   key: 'portfolio-list'
 * })
 *
 * // 执行异步操作
 * const data = await execute(async () => {
 *   return await portfolioApi.list()
 * })
 *
 * // 检查加载状态
 * if (isLoading()) {
 *   console.log('正在加载...')
 * }
 *
 * // 带回调的使用
 * await execute(
 *   async () => await portfolioApi.create(data),
 *   {
 *     onSuccess: () => message.success('创建成功'),
 *     onError: (err) => message.error('创建失败')
 *   }
 * )
 * ```
 */
export function useLoading(options?: LoadingOptions) {
  const loadingStore = useLoadingStore()

  const key = options?.key || 'default'
  const priority = options?.priority || loadingStore.PRIORITY.NORMAL

  /**
   * 执行异步操作并自动管理 loading 状态
   *
   * @param fn - 异步函数
   * @param opts - 选项（可覆盖默认的 key 和回调）
   * @returns 函数执行结果
   */
  async function execute<T>(
    fn: () => Promise<T>,
    opts?: LoadingOptions
  ): Promise<T> {
    const loadingKey = opts?.key || key

    loadingStore.startLoading(loadingKey, priority)

    try {
      const result = await fn()
      opts?.onSuccess?.()
      return result
    } catch (error) {
      opts?.onError?.(error)
      throw error
    } finally {
      loadingStore.endLoading(loadingKey)
      opts?.onFinally?.()
    }
  }

  /**
   * 检查是否正在加载
   *
   * @param k - 指定检查的键名（默认使用实例的 key）
   * @returns 是否正在加载
   */
  function isLoading(k?: string): boolean {
    return loadingStore.isLoading(k || key)
  }

  /**
   * 手动开始加载
   */
  function start(): void {
    loadingStore.startLoading(key, priority)
  }

  /**
   * 手动结束加载
   */
  function end(): void {
    loadingStore.endLoading(key)
  }

  // 组件卸载时自动清理
  onUnmounted(() => {
    loadingStore.endLoading(key)
  })

  return {
    isLoading,
    execute,
    start,
    end
  }
}

/**
 * 全局 Loading Composable
 *
 * 用于管理全局级别的加载状态（如页面初始化）。
 *
 * @returns 全局 Loading 管理对象
 *
 * @example
 * ```ts
 * const { startGlobalLoading, endGlobalLoading, isGlobalLoading } = useGlobalLoading()
 *
 * // 开始全局加载
 * startGlobalLoading()
 *
 * // 执行操作
 * await someAsyncOperation()
 *
 * // 结束全局加载
 * endGlobalLoading()
 *
 * // 检查全局加载状态
 * if (isGlobalLoading()) {
 *   // 显示全局加载提示
 * }
 * ```
 */
export function useGlobalLoading() {
  const loadingStore = useLoadingStore()

  const GLOBAL_KEY = '_global_'

  /**
   * 开始全局加载
   */
  function startGlobalLoading(): void {
    loadingStore.startLoading(GLOBAL_KEY, loadingStore.PRIORITY.HIGH)
  }

  /**
   * 结束全局加载
   */
  function endGlobalLoading(): void {
    loadingStore.endLoading(GLOBAL_KEY)
  }

  /**
   * 检查全局加载状态
   */
  function isGlobalLoading(): boolean {
    return loadingStore.isLoading(GLOBAL_KEY)
  }

  return {
    startGlobalLoading,
    endGlobalLoading,
    isGlobalLoading
=======
import { ref, computed } from 'vue'

const globalLoading = ref<Set<string>>(new Set())

export function useLoading() {
  const startLoading = (key: string = 'default') => {
    globalLoading.value.add(key)
  }

  const stopLoading = (key: string = 'default') => {
    globalLoading.value.delete(key)
  }

  const isLoading = (key: string = 'default') => {
    return computed(() => globalLoading.value.has(key))
  }

  const isAnyLoading = computed(() => globalLoading.value.size > 0)

  const withLoading = async <T>(key: string, fn: () => Promise<T>): Promise<T> => {
    startLoading(key)
    try {
      return await fn()
    } finally {
      stopLoading(key)
    }
  }

  return {
    startLoading,
    stopLoading,
    isLoading,
    isAnyLoading,
    withLoading,
>>>>>>> 011-quant-research
  }
}
