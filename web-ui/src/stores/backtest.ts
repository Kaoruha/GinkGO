import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
<<<<<<< HEAD
import {
  backtestApi,
  type BacktestTask,
  type BacktestTaskDetail,
  type BacktestCreate,
  type BacktestProgress
} from '@/api/modules/backtest'

export const useBacktestStore = defineStore('backtest', () => {
  // 状态
  const tasks = ref<BacktestTask[]>([])
  const currentTask = ref<BacktestTaskDetail | null>(null)
  const loading = ref(false)
  const error = ref<string | null>(null)
  const filterState = ref<string>('')

  // 计算属性
  const filteredTasks = computed(() => {
    if (!filterState.value) return tasks.value
    return tasks.value.filter(t => t.state === filterState.value)
  })

  const runningTasks = computed(() =>
    tasks.value.filter(t => t.state === 'RUNNING')
  )

  const completedTasks = computed(() =>
    tasks.value.filter(t => t.state === 'COMPLETED')
  )

  const failedTasks = computed(() =>
    tasks.value.filter(t => t.state === 'FAILED')
  )

  const pendingTasks = computed(() =>
    tasks.value.filter(t => t.state === 'PENDING')
  )

  // 统计数据
  const stats = computed(() => {
    const filtered = filterState.value
      ? tasks.value.filter(t => t.state === filterState.value)
      : tasks.value

    return {
      total: filtered.length,
      completed: filtered.filter(t => t.state === 'COMPLETED').length,
      running: filtered.filter(t => t.state === 'RUNNING').length,
      failed: filtered.filter(t => t.state === 'FAILED').length
    }
  })

  // 操作
  async function fetchTasks(state?: string) {
    loading.value = true
    error.value = null
    try {
      const response = await backtestApi.list({ state })
      // API返回PaginatedResponse，数据在data.items中
      tasks.value = response.data?.items || []
      if (state) {
        filterState.value = state
      }
    } catch (e: any) {
      error.value = e.message
      throw e
    } finally {
      loading.value = false
    }
  }

  async function fetchTask(uuid: string) {
    loading.value = true
    error.value = null
    try {
      const response = await backtestApi.get(uuid)
      currentTask.value = response.data || null
      return currentTask.value
    } catch (e: any) {
      error.value = e.message
      throw e
    } finally {
      loading.value = false
    }
  }

  async function createTask(data: BacktestCreate) {
    loading.value = true
    error.value = null
    try {
      const response = await backtestApi.create(data)
      const result = response.data
      if (result) {
        tasks.value.unshift(result)
      }
      return result
    } catch (e: any) {
      error.value = e.message
      throw e
=======
import { backtestApi } from '@/api'
import type { BacktestTask, BacktestNetValue, AnalyzerInfo } from '@/api'

/**
 * 回测任务状态管理
 *
 * 职责：
 * - 管理回测任务列表（带缓存）
 * - 管理当前查看的任务详情
 * - 追踪运行中的任务
 * - 处理 WebSocket 实时进度更新
 */
export const useBacktestStore = defineStore('backtest', () => {
  // ========== State ==========

  /** 任务列表 */
  const tasks = ref<BacktestTask[]>([])

  /** 当前查看的任务 */
  const currentTask = ref<BacktestTask | null>(null)

  /** 当前任务的净值数据 */
  const currentNetValue = ref<BacktestNetValue | null>(null)

  /** 当前任务的分析器列表 */
  const currentAnalyzers = ref<AnalyzerInfo[]>([])

  /** 运行中的任务 ID 集合 */
  const runningTaskIds = ref<Set<string>>(new Set())

  /** 列表加载状态 */
  const loading = ref(false)

  /** 详情加载状态 */
  const detailLoading = ref(false)

  /** 列表总数 */
  const total = ref(0)

  /** 最后更新时间 */
  const lastUpdate = ref<string | null>(null)

  // ========== Getters ==========

  /** 运行中任务数量 */
  const runningCount = computed(() => runningTaskIds.value.size)

  /** 运行中的任务列表 */
  const runningTasks = computed(() =>
    tasks.value.filter(t => runningTaskIds.value.has(t.uuid))
  )

  /** 已完成的任务 */
  const completedTasks = computed(() =>
    tasks.value.filter(t => t.status === 'completed')
  )

  /** 按状态分组 */
  const tasksByStatus = computed(() => {
    const groups: Record<string, BacktestTask[]> = {
      running: [],
      completed: [],
      failed: [],
      pending: [],
      other: [],
    }
    tasks.value.forEach(task => {
      if (task.status in groups) {
        groups[task.status].push(task)
      } else {
        groups.other.push(task)
      }
    })
    return groups
  })

  /** 按 ID 查找任务 */
  const getTaskById = computed(() => (uuid: string) =>
    tasks.value.find(t => t.uuid === uuid)
  )

  // ========== Actions ==========

  /**
   * 获取任务列表
   */
  async function fetchList(params?: { status?: string; page?: number; size?: number }) {
    loading.value = true
    try {
      const result = await backtestApi.list(params)
      tasks.value = result.data || []
      total.value = result.total || 0
      lastUpdate.value = new Date().toISOString()

      // 更新运行中任务集合
      tasks.value.forEach(task => {
        if (task.status === 'running') {
          runningTaskIds.value.add(task.uuid)
        } else {
          runningTaskIds.value.delete(task.uuid)
        }
      })

      return result
    } catch (error) {
      console.error('Failed to fetch backtest list:', error)
      return null
>>>>>>> 011-quant-research
    } finally {
      loading.value = false
    }
  }

<<<<<<< HEAD
  async function deleteTask(uuid: string) {
    await backtestApi.delete(uuid)
    tasks.value = tasks.value.filter(t => t.uuid !== uuid)
    if (currentTask.value?.uuid === uuid) {
      currentTask.value = null
    }
  }

  async function startTask(uuid: string) {
    await backtestApi.start(uuid)
    const task = tasks.value.find(t => t.uuid === uuid)
    if (task) {
      task.state = 'RUNNING'
    }
  }

  async function stopTask(uuid: string) {
    await backtestApi.stop(uuid)
    const task = tasks.value.find(t => t.uuid === uuid)
    if (task) {
      task.state = 'STOPPED'
    }
  }

  // 更新任务进度（用于 SSE 更新）
  function updateTaskProgress(uuid: string, progress: BacktestProgress) {
    const task = tasks.value.find(t => t.uuid === uuid)
    if (task) {
      task.progress = progress.progress
      if (progress.state) {
        task.state = progress.state as any
      }
      if (progress.current_date) {
        (task as any).current_date = progress.current_date
      }
    }
    if (currentTask.value?.uuid === uuid) {
      currentTask.value.progress = progress.progress
      if (progress.state) {
        currentTask.value.state = progress.state as any
      }
      if (progress.current_date) {
        currentTask.value.current_date = progress.current_date
      }
    }
  }

  function setFilterState(state: string) {
    filterState.value = state
  }

  function clearError() {
    error.value = null
  }

  function clearCurrentTask() {
    currentTask.value = null
  }

  return {
    // 状态
    tasks,
    currentTask,
    loading,
    error,
    filterState,

    // 计算属性
    filteredTasks,
    runningTasks,
    completedTasks,
    failedTasks,
    pendingTasks,
    stats,

    // 操作
    fetchTasks,
    fetchTask,
    createTask,
    deleteTask,
    startTask,
    stopTask,
    updateTaskProgress,
    setFilterState,
    clearError,
    clearCurrentTask
  }
}, {
  persist: {
    key: 'backtest-store',
    storage: localStorage,
    paths: ['filterState'] // 只持久化筛选状态
=======
  /**
   * 获取单个任务详情
   */
  async function fetchTask(uuid: string) {
    detailLoading.value = true
    try {
      const task = await backtestApi.get(uuid)
      currentTask.value = task

      // 更新列表中的任务
      const index = tasks.value.findIndex(t => t.uuid === uuid)
      if (index !== -1) {
        tasks.value[index] = task
      }

      // 更新运行状态
      if (task.status === 'running') {
        runningTaskIds.value.add(uuid)
      } else {
        runningTaskIds.value.delete(uuid)
      }

      return task
    } catch (error) {
      console.error('Failed to fetch backtest task:', error)
      return null
    } finally {
      detailLoading.value = false
    }
  }

  /**
   * 获取任务净值数据
   */
  async function fetchNetValue(uuid: string) {
    try {
      const data = await backtestApi.getNetValue(uuid)
      currentNetValue.value = data
      return data
    } catch (error) {
      console.error('Failed to fetch net value:', error)
      return null
    }
  }

  /**
   * 获取任务分析器
   */
  async function fetchAnalyzers(uuid: string) {
    try {
      const result = await backtestApi.getAnalyzers(uuid)
      currentAnalyzers.value = result.analyzers || []
      return result
    } catch (error) {
      console.error('Failed to fetch analyzers:', error)
      return null
    }
  }

  /**
   * 创建任务
   */
  async function createTask(data: { name?: string; portfolio_id: string; start_date?: string; end_date?: string }) {
    try {
      const task = await backtestApi.create(data)
      tasks.value.unshift(task)
      total.value++
      return task
    } catch (error) {
      console.error('Failed to create backtest task:', error)
      throw error
    }
  }

  /**
   * 启动任务
   */
  async function startTask(uuid: string, params?: { start_date?: string; end_date?: string }) {
    try {
      const result = await backtestApi.start(uuid, params)
      runningTaskIds.value.add(uuid)

      // 更新任务状态
      const task = tasks.value.find(t => t.uuid === uuid)
      if (task) {
        task.status = 'running'
        task.start_time = new Date().toISOString()
      }
      if (currentTask.value?.uuid === uuid) {
        currentTask.value.status = 'running'
        currentTask.value.start_time = new Date().toISOString()
      }

      return result
    } catch (error) {
      console.error('Failed to start backtest task:', error)
      throw error
    }
  }

  /**
   * 停止任务
   */
  async function stopTask(uuid: string) {
    try {
      const result = await backtestApi.stop(uuid)
      runningTaskIds.value.delete(uuid)

      // 更新任务状态
      const task = tasks.value.find(t => t.uuid === uuid)
      if (task) {
        task.status = 'stopped'
      }
      if (currentTask.value?.uuid === uuid) {
        currentTask.value.status = 'stopped'
      }

      return result
    } catch (error) {
      console.error('Failed to stop backtest task:', error)
      throw error
    }
  }

  /**
   * 删除任务
   */
  async function deleteTask(uuid: string) {
    try {
      await backtestApi.delete(uuid)
      tasks.value = tasks.value.filter(t => t.uuid !== uuid)
      total.value--
      runningTaskIds.value.delete(uuid)

      if (currentTask.value?.uuid === uuid) {
        currentTask.value = null
      }

      return true
    } catch (error) {
      console.error('Failed to delete backtest task:', error)
      throw error
    }
  }

  /**
   * 处理 WebSocket 进度更新
   * 由 WebSocket 消息处理器调用
   */
  function updateProgress(data: {
    task_id: string
    status?: string
    progress?: string
    current_stage?: string
    error_message?: string
  }) {
    const task = tasks.value.find(t => t.uuid === data.task_id)
    if (task) {
      if (data.status) task.status = data.status as any
      if (data.progress) task.progress = data.progress
      if (data.current_stage) task.current_stage = data.current_stage
      if (data.error_message) task.error_message = data.error_message
    }

    // 更新当前任务
    if (currentTask.value?.uuid === data.task_id) {
      if (data.status) currentTask.value.status = data.status as any
      if (data.progress) currentTask.value.progress = data.progress
      if (data.current_stage) currentTask.value.current_stage = data.current_stage
      if (data.error_message) currentTask.value.error_message = data.error_message
    }

    // 更新运行状态
    if (data.status === 'running') {
      runningTaskIds.value.add(data.task_id)
    } else if (['completed', 'failed', 'stopped'].includes(data.status || '')) {
      runningTaskIds.value.delete(data.task_id)
    }
  }

  /**
   * 清除当前任务详情
   */
  function clearCurrentTask() {
    currentTask.value = null
    currentNetValue.value = null
    currentAnalyzers.value = []
  }

  /**
   * 刷新列表（保留筛选条件）
   */
  async function refresh(params?: { status?: string; page?: number; size?: number }) {
    return fetchList(params)
  }

  return {
    // State
    tasks,
    currentTask,
    currentNetValue,
    currentAnalyzers,
    runningTaskIds,
    loading,
    detailLoading,
    total,
    lastUpdate,

    // Getters
    runningCount,
    runningTasks,
    completedTasks,
    tasksByStatus,
    getTaskById,

    // Actions
    fetchList,
    fetchTask,
    fetchNetValue,
    fetchAnalyzers,
    createTask,
    startTask,
    stopTask,
    deleteTask,
    updateProgress,
    clearCurrentTask,
    refresh,
>>>>>>> 011-quant-research
  }
})
