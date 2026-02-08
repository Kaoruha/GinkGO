/**
 * Loading 状态管理 Store
 *
 * 提供全局统一的 Loading 状态管理，支持优先级和多任务并发。
 */

import { defineStore } from 'pinia'
import { ref, computed } from 'vue'

export const useLoadingStore = defineStore('loading', () => {
  // 所有 loading 状态
  const loadingStates = ref<Record<string, boolean>>({})
  // loading 优先级
  const loadingPriorities = ref<Record<string, number>>({})

  // 优先级常量
  const PRIORITY = {
    LOW: 1,
    NORMAL: 2,
    HIGH: 3,
    CRITICAL: 4
  } as const

  /**
   * 开始加载
   * @param key - 加载键名
   * @param priority - 优先级（默认 NORMAL）
   */
  function startLoading(key: string, priority: number = PRIORITY.NORMAL): void {
    loadingStates.value[key] = true
    loadingPriorities.value[key] = priority
  }

  /**
   * 结束加载
   * @param key - 加载键名
   */
  function endLoading(key: string): void {
    loadingStates.value[key] = false
    delete loadingPriorities.value[key]
  }

  /**
   * 设置加载状态
   * @param key - 加载键名
   * @param value - 是否加载中
   * @param priority - 优先级（设置状态时提供）
   */
  function setLoading(key: string, value: boolean, priority?: number): void {
    if (value) {
      startLoading(key, priority || PRIORITY.NORMAL)
    } else {
      endLoading(key)
    }
  }

  /**
   * 清除加载状态
   * @param key - 加载键名（不提供则清除所有）
   */
  function clearLoading(key?: string): void {
    if (key) {
      delete loadingStates.value[key]
      delete loadingPriorities.value[key]
    } else {
      loadingStates.value = {}
      loadingPriorities.value = {}
    }
  }

  /**
   * 检查是否正在加载
   * @param key - 加载键名（不提供则检查是否有任何加载）
   * @returns 是否加载中
   */
  function isLoading(key?: string): boolean {
    if (key) return loadingStates.value[key] || false
    return Object.values(loadingStates.value).some(Boolean)
  }

  /**
   * 是否有任何加载任务
   */
  const hasAnyLoading = computed(() => {
    return Object.values(loadingStates.value).some(Boolean)
  })

  /**
   * 所有正在加载的键名
   */
  const loadingKeys = computed(() => {
    return Object.keys(loadingStates.value).filter(
      key => loadingStates.value[key]
    )
  })

  /**
   * 所有正在加载的任务（别名，更语义化）
   */
  const activeLoadings = computed(() => {
    return Object.entries(loadingStates.value)
      .filter(([_, loading]) => loading)
      .map(([key, _]) => key)
  })

  /**
   * 获取最高优先级的加载任务
   */
  const highestPriorityLoading = computed(() => {
    const entries = Object.entries(loadingPriorities.value)
      .filter(([key, _]) => loadingStates.value[key])

    if (entries.length === 0) return null

    const [key, priority] = entries.reduce((max, current) =>
      current[1] > max[1] ? current : max
    )

    return { key, priority }
  })

  /**
   * 清除所有加载状态（别名）
   */
  function clearAll(): void {
    clearLoading()
  }

  return {
    // 状态
    loadingStates,
    loadingPriorities,

    // 计算属性
    hasAnyLoading,
    loadingKeys,
    activeLoadings,
    highestPriorityLoading,

    // 方法
    startLoading,
    endLoading,
    setLoading,
    clearLoading,
    clearAll,
    isLoading,

    // 常量
    PRIORITY
  }
})
