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
  running_tasks?: number
  pending_tasks?: number
  task_uuids?: string[]
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

export interface WorkerTaskInfo {
  task_id: string
  name: string
  status: string
  progress: number
  portfolio_id: string
}

export interface WorkerTasksResponse {
  worker_id: string
  found: boolean
  tasks: WorkerTaskInfo[]
}

// ===== API 模块 =====

export const systemApi = {
  /**
   * 获取系统状态
   */
  getStatus(): Promise<SystemStatusResponse> {
    return request.get('/api/v1/system/status')
  },

  /**
   * 获取所有组件/Worker状态
   */
  getWorkers(): Promise<WorkersResponse> {
    return request.get('/api/v1/system/workers')
  },

  /**
   * 获取DataWorker列表
   */
  getDataWorkers(): Promise<WorkerInfo[]> {
    return request.get('/api/v1/system/workers/data')
  },

  /**
   * 获取BacktestWorker列表
   */
  getBacktestWorkers(): Promise<WorkerInfo[]> {
    return request.get('/api/v1/system/workers/backtest')
  },

  /**
   * 获取ExecutionNode列表
   */
  getExecutionNodes(): Promise<WorkerInfo[]> {
    return request.get('/api/v1/system/workers/execution')
  },

  /**
   * 获取Scheduler列表
   */
  getSchedulers(): Promise<WorkerInfo[]> {
    return request.get('/api/v1/system/workers/scheduler')
  },

  /**
   * 获取TaskTimer列表
   */
  getTaskTimers(): Promise<WorkerInfo[]> {
    return request.get('/api/v1/system/workers/timer')
  },

  /**
   * 回测 Worker 活跃任务下钻（行内展开懒加载）
   */
  getWorkerTasks(workerId: string): Promise<WorkerTasksResponse> {
    return request.get(`/api/v1/system/workers/${workerId}/tasks`)
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
