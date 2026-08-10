import request from '../request'

// ===== 类型定义 =====

export interface TaskTimerExecution {
  uuid: string
  job_name: string
  command: string
  node_id: string
  cron_expr: string
  status: 'triggered' | 'success' | 'failed'
  triggered_at: string | null
  completed_at: string | null
  duration_ms: number
  error_message: string | null
  params: Record<string, any> | null
  result: Record<string, any> | null
}

export interface TaskTimerJob {
  name: string
  cron: string
  command: string
  enabled: boolean
}

export interface ExecutionSummary {
  total: number
  success: number
  failed: number
  triggered: number
  by_job: Record<string, { total: number; success: number; failed: number }>
}

// ===== API =====

export const taskTimerApi = {
  /**
   * 分页查询执行历史
   */
  getExecutions(params?: {
    job_name?: string
    status?: string
    start_date?: string
    end_date?: string
    page?: number
    page_size?: number
  }) {
    return request.get('/api/v1/task-timer/executions', { params })
  },

  /**
   * 获取执行统计摘要
   */
  getSummary() {
    return request.get('/api/v1/task-timer/executions/summary')
  },

  /**
   * 获取已注册的定时任务列表
   */
  getJobs() {
    return request.get('/api/v1/task-timer/jobs')
  },
}
