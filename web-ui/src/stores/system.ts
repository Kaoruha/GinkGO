import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { systemApi } from '@/api'
import type { WorkerInfo, InfrastructureStatus, SystemStatusResponse, ComponentCounts } from '@/api'

/**
 * 系统状态管理
 *
 * 职责：
 * - 管理系统运行状态
 * - 管理 Worker 列表和状态
 * - 管理 WebSocket 连接状态
 * - 提供系统健康检查
 */
export const useSystemStore = defineStore('system', () => {
  // ========== State ==========

  /** 系统状态 */
  const systemStatus = ref<SystemStatusResponse | null>(null)

  /** Worker 列表 */
  const workers = ref<WorkerInfo[]>([])

  /** 组件统计 */
  const componentCounts = ref<ComponentCounts>({
    data_workers: 0,
    backtest_workers: 0,
    execution_nodes: 0,
    schedulers: 0,
    task_timers: 0,
  })

  /** WebSocket 连接状态 */
  const wsConnected = ref(false)

  /** 加载状态 */
  const loading = ref(false)

  /** 自动刷新 */
  const autoRefresh = ref(false)

  /** 自动刷新间隔 (ms) */
  const refreshInterval = ref(5000)

  /** 最后更新时间 */
  const lastUpdate = ref<string | null>(null)

  /** 刷新定时器 */
  let refreshTimer: ReturnType<typeof setInterval> | null = null

  // ========== Getters ==========

  /** 基础设施状态 */
  const infrastructure = computed<InfrastructureStatus | null>(() =>
    systemStatus.value?.infrastructure || null
  )

  /** 数据库状态 */
  const dbStatus = computed(() => infrastructure.value)

  /** 数据库是否健康 */
  const dbHealthy = computed(() => {
    const infra = infrastructure.value
    if (!infra) return false
    return infra.mysql?.status === 'ok' &&
           infra.redis?.status === 'ok' &&
           infra.clickhouse?.status === 'ok'
  })

  /** 健康 Worker 数量 */
  const healthyWorkerCount = computed(() =>
    workers.value.filter(w => w.status === 'running' || w.status === 'healthy').length
  )

  /** 总 Worker 数量 */
  const totalWorkerCount = computed(() => workers.value.length)

  /** 系统整体健康状态 */
  const systemHealth = computed<'healthy' | 'degraded' | 'unhealthy' | 'unknown'>(() => {
    if (!systemStatus.value) return 'unknown'

    const infra = infrastructure.value
    const dbOk = infra?.mysql?.status === 'ok' &&
                 infra?.redis?.status === 'ok' &&
                 infra?.clickhouse?.status === 'ok'

    if (dbOk && healthyWorkerCount.value > 0) return 'healthy'
    if (dbOk || healthyWorkerCount.value > 0) return 'degraded'
    return 'unhealthy'
  })

  /** 系统状态颜色 */
  const healthColor = computed(() => {
    switch (systemHealth.value) {
      case 'healthy': return 'green'
      case 'degraded': return 'orange'
      case 'unhealthy': return 'red'
      default: return 'default'
    }
  })

  /** 运行中的 Worker */
  const runningWorkers = computed(() =>
    workers.value.filter(w => w.status === 'running')
  )

  /** 停止的 Worker */
  const stoppedWorkers = computed(() =>
    workers.value.filter(w => w.status === 'stopped' || w.status === 'idle')
  )

  /** 系统版本 */
  const version = computed(() => systemStatus.value?.version || '-')

  /** 系统运行时间 */
  const uptime = computed(() => systemStatus.value?.uptime || '-')

  /** 调试模式 */
  const debugMode = computed(() => systemStatus.value?.debug_mode || false)

  // ========== Actions ==========

  /**
   * 获取系统状态
   */
  async function fetchStatus() {
    loading.value = true
    try {
      const result = await systemApi.getFullStatus()
      systemStatus.value = result.status
      workers.value = result.workers.data || []
      componentCounts.value = result.workers.components || componentCounts.value
      lastUpdate.value = new Date().toISOString()
      return result
    } catch (error) {
      console.error('Failed to fetch system status:', error)
      return null
    } finally {
      loading.value = false
    }
  }

  /**
   * 仅获取 Worker 列表
   */
  async function fetchWorkers() {
    try {
      const result = await systemApi.getWorkers()
      workers.value = result.data || []
      componentCounts.value = result.components || componentCounts.value
      return result
    } catch (error) {
      console.error('Failed to fetch workers:', error)
      return null
    }
  }

  /**
   * 启动 Worker
   */
  async function startWorker(workerId: string) {
    try {
      const result = await systemApi.startWorker(workerId)
      // 更新本地状态
      const worker = workers.value.find(w => w.id === workerId)
      if (worker) {
        worker.status = 'running'
      }
      return result
    } catch (error) {
      console.error('Failed to start worker:', error)
      throw error
    }
  }

  /**
   * 停止 Worker
   */
  async function stopWorker(workerId: string) {
    try {
      const result = await systemApi.stopWorker(workerId)
      // 更新本地状态
      const worker = workers.value.find(w => w.id === workerId)
      if (worker) {
        worker.status = 'stopped'
      }
      return result
    } catch (error) {
      console.error('Failed to stop worker:', error)
      throw error
    }
  }

  /**
   * 设置 WebSocket 连接状态
   */
  function setWsConnected(connected: boolean) {
    wsConnected.value = connected
  }

  /**
   * 开启自动刷新
   */
  function enableAutoRefresh(interval?: number) {
    if (interval) {
      refreshInterval.value = interval
    }
    autoRefresh.value = true

    // 清除旧定时器
    if (refreshTimer) {
      clearInterval(refreshTimer)
    }

    // 设置新定时器
    refreshTimer = setInterval(() => {
      fetchStatus()
    }, refreshInterval.value)
  }

  /**
   * 关闭自动刷新
   */
  function disableAutoRefresh() {
    autoRefresh.value = false
    if (refreshTimer) {
      clearInterval(refreshTimer)
      refreshTimer = null
    }
  }

  /**
   * 切换自动刷新
   */
  function toggleAutoRefresh() {
    if (autoRefresh.value) {
      disableAutoRefresh()
    } else {
      enableAutoRefresh()
    }
  }

  /**
   * 刷新数据
   */
  async function refresh() {
    return fetchStatus()
  }

  return {
    // State
    systemStatus,
    workers,
    componentCounts,
    wsConnected,
    loading,
    autoRefresh,
    refreshInterval,
    lastUpdate,

    // Getters
    infrastructure,
    dbStatus,
    dbHealthy,
    healthyWorkerCount,
    totalWorkerCount,
    systemHealth,
    healthColor,
    runningWorkers,
    stoppedWorkers,
    version,
    uptime,
    debugMode,

    // Actions
    fetchStatus,
    fetchWorkers,
    startWorker,
    stopWorker,
    setWsConnected,
    enableAutoRefresh,
    disableAutoRefresh,
    toggleAutoRefresh,
    refresh,
  }
})
