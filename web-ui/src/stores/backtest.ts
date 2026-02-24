import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
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
    } finally {
      loading.value = false
    }
  }

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
  }
})
