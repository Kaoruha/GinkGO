import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
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
    } finally {
      loading.value = false
    }
  }

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
  }
})
