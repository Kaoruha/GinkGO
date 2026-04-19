import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { backtestApi } from '@/api'
import { useAuthStore } from './auth'
import type { BacktestTask, BacktestNetValue, AnalyzerInfo } from '@/api'
import { canStartByState, canStopByState, canCancelByState } from '@/constants'

/**
 * Upstream: data-model.md
 * Downstream: BacktestList.vue, BacktestDetail.vue
 * Role: 回测任务状态管理，提供任务列表、详情、操作、权限检查、批量操作等方法
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

  /** WebSocket 连接状态 */
  const wsConnected = ref(false)

  /** 轮询模式标志（WebSocket 断开时启用） */
  const pollingMode = ref(false)

  /** 轮询定时器 */
  let pollingTimer: number | null = null

  /** 批量操作加载状态 */
  const batchOperationLoading = ref(false)

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
   * 权限检查：判断当前用户是否可以操作指定任务
   * @param task 回测任务
   * @returns 是否有权限
   */
  function canOperateTask(task: BacktestTask): boolean {
    const authStore = useAuthStore()
    // 检查是否有 creator_id 属性，如果没有则只检查 admin 权限
    if ('creator_id' in task && task.creator_id) {
      return authStore.isAdmin || authStore.user?.uuid === task.creator_id
    }
    // 如果没有 creator_id，默认允许操作（向后兼容）
    return true
  }

  /**
   * 判断是否可以启动任务
   * 条件：状态允许 + 有权限
   */
  function canStartTask(task: BacktestTask): boolean {
    return canStartByState(task.status) && canOperateTask(task)
  }

  /**
   * 判断是否可以停止任务
   * 条件：状态允许 + 有权限
   */
  function canStopTask(task: BacktestTask): boolean {
    return canStopByState(task.status) && canOperateTask(task)
  }

  /**
   * 判断是否可以取消任务
   * 条件：状态允许 + 有权限
   */
  function canCancelTask(task: BacktestTask): boolean {
    return canCancelByState(task.status) && canOperateTask(task)
  }

  /**
   * 判断是否可以删除任务
   * 条件：非运行中 + 有权限
   */
  function canDeleteTask(task: BacktestTask): boolean {
    return task.status !== 'running' && canOperateTask(task)
  }

  /**
   * 获取任务列表
   */
  async function fetchList(params?: { status?: string; page?: number; size?: number; keyword?: string }) {
    loading.value = true
    try {
      const result = await backtestApi.list(params)
      tasks.value = result.data || []
      total.value = result.meta?.total || 0
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
      const payload = task.data
      currentTask.value = payload

      // 更新列表中的任务
      const index = tasks.value.findIndex(t => t.uuid === uuid)
      if (index !== -1) {
        tasks.value[index] = payload
      }

      // 更新运行状态
      if (payload.status === 'running') {
        runningTaskIds.value.add(uuid)
      } else {
        runningTaskIds.value.delete(uuid)
      }

      return payload
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
      const result = await backtestApi.getNetValue(uuid)
      const payload = result.data
      currentNetValue.value = payload
      return payload
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
      const payload = result.data
      currentAnalyzers.value = payload.analyzers || []
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
      const result = await backtestApi.create(data)
      const payload = result.data
      tasks.value.unshift(payload)
      total.value++
      return payload
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
   * 取消任务
   */
  async function cancelTask(uuid: string) {
    try {
      const result = await backtestApi.cancel(uuid)

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
      console.error('Failed to cancel backtest task:', error)
      throw error
    }
  }

  /**
   * 批量启动任务
   * 返回操作结果统计
   */
  async function batchStart(uuids: string[]): Promise<{
    total: number
    success: number
    failed: number
    failedTasks: Array<{ uuid: string; error: string }>
  }> {
    batchOperationLoading.value = true
    const results = await Promise.allSettled(
      uuids.map(uuid => {
        // 从任务列表中获取配置信息
        const task = tasks.value.find(t => t.uuid === uuid)
        let params: { start_date?: string; end_date?: string } = {}

        if (task?.config_snapshot) {
          try {
            const config = typeof task.config_snapshot === 'string'
              ? JSON.parse(task.config_snapshot)
              : task.config_snapshot
            params = {
              start_date: config.start_date,
              end_date: config.end_date
            }
          } catch (e) {
            console.warn('Failed to parse config_snapshot:', e)
          }
        }

        return startTask(uuid, params)
      })
    )

    const success = results.filter(r => r.status === 'fulfilled').length
    const failed = results.filter(r => r.status === 'rejected').length
    const failedTasks: Array<{ uuid: string; error: string }> = []

    results.forEach((result, index) => {
      if (result.status === 'rejected') {
        failedTasks.push({
          uuid: uuids[index],
          error: result.reason?.message || '未知错误'
        })
      }
    })

    batchOperationLoading.value = false
    return { total: uuids.length, success, failed, failedTasks }
  }

  /**
   * 批量停止任务
   */
  async function batchStop(uuids: string[]): Promise<{
    total: number
    success: number
    failed: number
    failedTasks: Array<{ uuid: string; error: string }>
  }> {
    batchOperationLoading.value = true
    const results = await Promise.allSettled(
      uuids.map(uuid => stopTask(uuid))
    )

    const success = results.filter(r => r.status === 'fulfilled').length
    const failed = results.filter(r => r.status === 'rejected').length
    const failedTasks: Array<{ uuid: string; error: string }> = []

    results.forEach((result, index) => {
      if (result.status === 'rejected') {
        failedTasks.push({
          uuid: uuids[index],
          error: result.reason?.message || '未知错误'
        })
      }
    })

    batchOperationLoading.value = false
    return { total: uuids.length, success, failed, failedTasks }
  }

  /**
   * 批量取消任务
   */
  async function batchCancel(uuids: string[]): Promise<{
    total: number
    success: number
    failed: number
    failedTasks: Array<{ uuid: string; error: string }>
  }> {
    batchOperationLoading.value = true
    const results = await Promise.allSettled(
      uuids.map(uuid => cancelTask(uuid))
    )

    const success = results.filter(r => r.status === 'fulfilled').length
    const failed = results.filter(r => r.status === 'rejected').length
    const failedTasks: Array<{ uuid: string; error: string }> = []

    results.forEach((result, index) => {
      if (result.status === 'rejected') {
        failedTasks.push({
          uuid: uuids[index],
          error: result.reason?.message || '未知错误'
        })
      }
    })

    batchOperationLoading.value = false
    return { total: uuids.length, success, failed, failedTasks }
  }

  /**
   * 处理 WebSocket 进度更新
   * 包含数据冲突处理（基于时间戳比较）
   * 由 WebSocket 消息处理器调用
   */
  function updateProgress(data: {
    task_id: string
    status?: string
    progress?: number
    current_stage?: string
    error_message?: string
    timestamp?: string  // 服务端时间戳，用于冲突处理
    updated_at?: string
  }) {
    const task = tasks.value.find(t => t.uuid === data.task_id)

    // 数据冲突处理：比较时间戳
    if (task && data.updated_at) {
      const existingTime = new Date(task.updated_at).getTime()
      const updateTime = new Date(data.updated_at).getTime()

      // 仅当服务端数据更新时才更新本地数据
      if (updateTime > existingTime) {
        if (data.status) task.status = data.status as any
        if (data.progress) task.progress = data.progress
        if (data.current_stage) task.current_stage = data.current_stage
        if (data.error_message) task.error_message = data.error_message
        if (data.updated_at) task.updated_at = data.updated_at
      }
    } else if (task) {
      // 没有时间戳信息时，直接更新
      if (data.status) task.status = data.status as any
      if (data.progress) task.progress = data.progress
      if (data.current_stage) task.current_stage = data.current_stage
      if (data.error_message) task.error_message = data.error_message
    }

    // 更新当前任务（同样进行冲突处理）
    if (currentTask.value?.uuid === data.task_id && data.updated_at) {
      const existingTime = new Date(currentTask.value.updated_at).getTime()
      const updateTime = new Date(data.updated_at).getTime()

      if (updateTime > existingTime) {
        if (data.status) currentTask.value.status = data.status as any
        if (data.progress) currentTask.value.progress = data.progress
        if (data.current_stage) currentTask.value.current_stage = data.current_stage
        if (data.error_message) currentTask.value.error_message = data.error_message
        if (data.updated_at) currentTask.value.updated_at = data.updated_at
      }
    } else if (currentTask.value?.uuid === data.task_id) {
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
   * 启动轮询模式（WebSocket 断开时）
   */
  function startPolling(interval = 5000) {
    if (pollingTimer) return // 避免重复启动

    pollingMode.value = true
    pollingTimer = window.setInterval(async () => {
      // 只在有运行中任务时才轮询
      if (runningTaskIds.value.size > 0) {
        await fetchList()
      }
    }, interval)
  }

  /**
   * 停止轮询模式（WebSocket 重连时）
   */
  function stopPolling() {
    pollingMode.value = false
    if (pollingTimer) {
      clearInterval(pollingTimer)
      pollingTimer = null
    }
  }

  /**
   * WebSocket 连接状态更新
   */
  function onWebSocketConnected() {
    wsConnected.value = true
    stopPolling() // 停止轮询
  }

  /**
   * WebSocket 断开处理
   */
  function onWebSocketDisconnected() {
    wsConnected.value = false
    startPolling() // 启动轮询降级
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
    wsConnected,
    pollingMode,
    batchOperationLoading,

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
    cancelTask,
    batchStart,
    batchStop,
    batchCancel,
    updateProgress,
    clearCurrentTask,
    refresh,
    onWebSocketConnected,
    onWebSocketDisconnected,
    startPolling,
    stopPolling,
    canOperateTask,
    canStartTask,
    canStopTask,
    canCancelTask,
    canDeleteTask,
  }
})
