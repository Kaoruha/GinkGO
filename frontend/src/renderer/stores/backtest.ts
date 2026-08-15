import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { backtestApi } from '@/api'
import { useAuthStore } from './auth'
import type { BacktestTask, BacktestNetValue, AnalyzerInfo, BacktestCreateRequest } from '@/api'
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
   * @param opts.silent 静默拉取（轮询场景），不触发 loading 闪烁
   */
  async function fetchList(params?: { status?: string; page?: number; size?: number; keyword?: string }, opts?: { silent?: boolean }) {
    if (!opts?.silent) loading.value = true
    try {
      const result = await backtestApi.list(params)
      tasks.value = result.items || []
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
      if (!opts?.silent) loading.value = false
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
      const result = await backtestApi.getNetValue(uuid)
      currentNetValue.value = result
      return result
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
  async function createTask(data: { name: string; portfolio_uuids: string[]; engine_config: Record<string, any> }) {
    try {
      const result = await backtestApi.create(data as BacktestCreateRequest)
      tasks.value.unshift(result)
      total.value++
      return result
    } catch (error) {
      console.error('Failed to create backtest task:', error)
      throw error
    }
  }

  /**
   * 启动任务
   */
  async function startTask(uuid: string) {
    try {
      const result = await backtestApi.start(uuid)
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
   * 批量操作通用执行:Promise.allSettled 并发 + 成功/失败统计。
   * batchStart/Stop/Cancel 三者仅操作函数不同,统计逻辑完全一致,归集于此。
   */
  async function runBatch(
    uuids: string[],
    op: (uuid: string) => Promise<any>
  ): Promise<{
    total: number
    success: number
    failed: number
    failedTasks: Array<{ uuid: string; error: string }>
  }> {
    batchOperationLoading.value = true
    try {
      const results = await Promise.allSettled(uuids.map(uuid => op(uuid)))
      const failedTasks = results
        .map((r, i) => r.status === 'rejected'
          ? { uuid: uuids[i], error: r.reason?.message || '未知错误' }
          : null)
        .filter((x): x is { uuid: string; error: string } => x !== null)
      return {
        total: uuids.length,
        success: results.length - failedTasks.length,
        failed: failedTasks.length,
        failedTasks,
      }
    } finally {
      batchOperationLoading.value = false
    }
  }

  /** 批量启动任务,返回操作结果统计 */
  const batchStart = (uuids: string[]) => runBatch(uuids, startTask)

  /** 批量停止任务 */
  const batchStop = (uuids: string[]) => runBatch(uuids, stopTask)

  /** 批量取消任务 */
  const batchCancel = (uuids: string[]) => runBatch(uuids, cancelTask)

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
    clearCurrentTask,
    refresh,
    canOperateTask,
    canStartTask,
    canStopTask,
    canCancelTask,
    canDeleteTask,
  }
})
