import request from '../request'

// ===== 类型定义 =====

export interface InfrastructureStatus {
  mysql: { status: string; latency_ms?: number; error?: string }
  redis: { status: string; latency_ms?: number; error?: string }
  kafka: { status: string; error?: string }
  clickhouse: { status: string; latency_ms?: number; error?: string }
}

export interface ModuleStatus {
  available: boolean
  type: string
  error: string | null
  cached: boolean
  load_time: number
}

export interface SystemStatusResponse {
  status: string
  version: string
  uptime: string
  modules: Record<string, ModuleStatus>
  infrastructure: InfrastructureStatus
  debug_mode: boolean
}

export interface WorkerInfo {
  id: string
  type: string
  status: string
  task_count?: number
  max_tasks?: number
  portfolio_count?: number
  jobs_count?: number
  last_heartbeat: string
}

export interface ComponentCounts {
  data_workers: number
  backtest_workers: number
  execution_nodes: number
  schedulers: number
  task_timers: number
  total?: number
}

export interface WorkersResponse {
  data: WorkerInfo[]
  components: ComponentCounts
}

// ===== API 模块 =====

export const systemApi = {
  /**
   * 获取系统状态
   */
  getStatus(): Promise<SystemStatusResponse> {
    return request.get('/v1/system/status')
  },

  /**
   * 获取所有组件/Worker状态
   */
  getWorkers(): Promise<WorkersResponse> {
    return request.get('/v1/system/workers')
  },

  /**
   * 获取DataWorker列表
   */
  getDataWorkers(): Promise<WorkerInfo[]> {
    return request.get('/v1/system/workers/data')
  },

  /**
   * 获取BacktestWorker列表
   */
  getBacktestWorkers(): Promise<WorkerInfo[]> {
    return request.get('/v1/system/workers/backtest')
  },

  /**
   * 获取ExecutionNode列表
   */
  getExecutionNodes(): Promise<WorkerInfo[]> {
    return request.get('/v1/system/workers/execution')
  },

  /**
   * 获取Scheduler列表
   */
  getSchedulers(): Promise<WorkerInfo[]> {
    return request.get('/v1/system/workers/scheduler')
  },

  /**
   * 获取TaskTimer列表
   */
  getTaskTimers(): Promise<WorkerInfo[]> {
    return request.get('/v1/system/workers/timer')
  },

  /**
   * 启动 Worker
   */
  startWorker(workerId: string): Promise<{ success: boolean; message: string }> {
    return request.post(`/v1/system/workers/${workerId}/start`)
  },

  /**
   * 停止 Worker
   */
  stopWorker(workerId: string): Promise<{ success: boolean; message: string }> {
    return request.post(`/v1/system/workers/${workerId}/stop`)
  },

  /**
   * 获取综合状态（合并系统状态和 Worker 列表）
   */
  async getFullStatus(): Promise<{
    status: SystemStatusResponse
    workers: WorkersResponse
  }> {
    const [status, workers] = await Promise.all([
      this.getStatus(),
      this.getWorkers(),
    ])
    return { status, workers }
  },
}
