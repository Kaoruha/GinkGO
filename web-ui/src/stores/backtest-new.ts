import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import * as backtestApi from '@/api/modules/business/backtest'
import { useApiError } from '@/composables/useApiError'

/**
 * 统一的 Store 模式
 * 规范状态管理、Actions、Getters
 */

// 回测任务状态类型
export type BacktestState = 'PENDING' | 'RUNNING' | 'COMPLETED' | 'FAILED' | 'CANCELLED'

interface BacktestTask {
  uuid: string
  name: string
  portfolio_name: string
  state: BacktestState
  progress: number
  created_at: string
}

export const useBacktestStore = defineStore('backtest', () => {
  // ============================================
  // State - 状态定义
  // ============================================

  const tasks = ref<BacktestTask[]>([])
  const loading = ref(false)
  const error = ref<string | null>(null)
  const pagination = ref({
    page: 1,
    pageSize: 20,
    total: 0
  })
  const filter = ref<{
    state?: BacktestState
    keyword?: string
  }>({})

  // ============================================
  // Getters - 计算属性
  // ============================================

  const filteredTasks = computed(() => {
    let result = tasks.value

    // 状态筛选
    if (filter.value.state) {
      result = result.filter(t => t.state === filter.value.state)
    }

    // 关键词搜索
    if (filter.value.keyword) {
      const keyword = filter.value.keyword.toLowerCase()
      result = result.filter(t =>
        t.name.toLowerCase().includes(keyword) ||
        t.portfolio_name.toLowerCase().includes(keyword)
      )
    }

    return result
  })

  const taskStats = computed(() => {
    const total = tasks.value.length
    const completed = tasks.value.filter(t => t.state === 'COMPLETED').length
    const running = tasks.value.filter(t => t.state === 'RUNNING').length
    const failed = tasks.value.filter(t => t.state === 'FAILED').length

    return { total, completed, running, failed }
  })

  const hasMore = computed(() => {
    return pagination.value.page * pagination.value.pageSize < pagination.value.total
  })

  // ============================================
  // Actions - 操作方法
  // ============================================

  /**
   * 获取回测任务列表
   */
  async function fetchTasks(params?: {
    page?: number
    state?: BacktestState
    keyword?: string
  }) {
    loading.value = true
    error.value = null

    try {
      const result = await backtestApi.getBacktestList(params)

      if (result.success && result.data) {
        if (params?.page === 1) {
          // 第一页，替换数据
          tasks.value = result.data.items
        } else {
          // 追加数据
          tasks.value.push(...result.data.items)
        }

        pagination.value.total = result.data.total
      }
    } catch (err) {
      error.value = err.message || '获取任务列表失败'
    } finally {
      loading.value = false
    }
  }

  /**
   * 创建回测任务
   */
  async function createTask(data: {
    name: string
    portfolio_uuids: string[]
    engine_config: any
  }) {
    loading.value = true
    error.value = null

    try {
      const result = await backtestApi.createBacktest(data)

      if (result.success && result.data) {
        tasks.value.unshift(result.data)
        pagination.value.total++
      }
    } catch (err) {
      error.value = err.message || '创建任务失败'
    } finally {
      loading.value = false
    }
  }

  /**
   * 启动回测任务
   */
  async function startTask(uuid: string) {
    loading.value = true
    error.value = null

    try {
      const result = await backtestApi.startBacktest(uuid)

      if (result.success) {
        const task = tasks.value.find(t => t.uuid === uuid)
        if (task) {
          task.state = 'RUNNING'
        }
      }
    } catch (err) {
      error.value = err.message || '启动任务失败'
    } finally {
      loading.value = false
    }
  }

  /**
   * 停止回测任务
   */
  async function stopTask(uuid: string) {
    loading.value = true
    error.value = null

    try {
      const result = await backtestApi.stopBacktest(uuid)

      if (result.success) {
        const task = tasks.value.find(t => t.uuid === uuid)
        if (task) {
          task.state = 'CANCELLED'
        }
      }
    } catch (err) {
      error.value = err.message || '停止任务失败'
    } finally {
      loading.value = false
    }
  }

  /**
   * 删除回测任务
   */
  async function deleteTask(uuid: string) {
    loading.value = true
    error.value = null

    try {
      await backtestApi.deleteBacktest(uuid)

      tasks.value = tasks.value.filter(t => t.uuid !== uuid)
      pagination.value.total--
    } catch (err) {
      error.value = err.message || '删除任务失败'
    } finally {
      loading.value = false
    }
  }

  /**
   * 设置筛选条件
   */
  function setFilter(newFilter: { state?: BacktestState; keyword?: string }) {
    filter.value = { ...filter.value, ...newFilter }
    pagination.page = 1
  }

  /**
   * 重置筛选条件
   */
  function resetFilter() {
    filter.value = {}
    pagination.page = 1
  }

  /**
   * 加载更多
   */
  async function loadMore() {
    if (!hasMore.value || loading.value) return

    pagination.page++
    await fetchTasks({
      page: pagination.page,
      state: filter.value.state,
      keyword: filter.value.keyword
    })
  }

  /**
   * 刷新数据
   */
  async function refresh() {
    pagination.page = 1
    await fetchTasks({
      page: pagination.page,
      state: filter.value.state,
      keyword: filter.value.keyword
    })
  }

  return {
    // State
    tasks,
    loading,
    error,
    pagination,
    filter,

    // Getters
    filteredTasks,
    taskStats,
    hasMore,

    // Actions
    fetchTasks,
    createTask,
    startTask,
    stopTask,
    deleteTask,
    setFilter,
    resetFilter,
    loadMore,
    refresh
  }
})
