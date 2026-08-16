/**
 * 回测相关的统一类型定义
 * 从API层导入并重新导出，确保类型定义的一致性
 */

// 重新导出API层的类型定义
export type {
  BacktestTask,
  BacktestCreateRequest,
  BacktestNetValue,
  AnalyzerInfo,
  BacktestLog,
  BacktestProgress,
  BacktestTrade,
  BacktestPosition,
  BacktestMetrics
} from '@/api/modules/backtest'

/**
 * 扩展的回测任务状态类型
 */
export type BacktestTaskStatus =
  | 'CREATED'
  | 'PENDING'
  | 'RUNNING'
  | 'PAUSED'
  | 'COMPLETED'
  | 'STOPPED'
  | 'FAILED'
  | 'ERROR'

/**
 * 回测任务摘要信息（用于列表显示）
 */
export interface BacktestTaskSummary {
  uuid: string
  name: string
  state: BacktestTaskStatus
  created_at: string
  updated_at: string
  portfolio_name?: string
  progress?: number
  total_return?: number
  max_drawdown?: number
  sharpe_ratio?: number
}

/**
 * 批量操作请求类型
 */
export interface BatchOperationRequest {
  uuids: string[]
  operation: 'start' | 'stop' | 'cancel' | 'delete'
}

/**
 * 批量操作响应类型
 */
export interface BatchOperationResponse {
  total: number
  success: number
  failed: number
  failed_tasks: Array<{
    uuid: string
    error: string
  }>
}

/**
 * WebSocket消息类型
 */
export interface WebSocketMessage {
  task_id?: string
  task_uuid?: string
  event_type?: string
  progress?: number
  state?: BacktestTaskStatus
  timestamp?: string
  [key: string]: any
}

/**
 * 分页请求参数
 */
export interface PageRequest {
  page?: number
  page_size?: number
  sort_by?: string
  order?: 'asc' | 'desc'
}

/**
 * 分页响应类型
 */
export interface PageResponse<T> {
  items: T[]
  total: number
  page: number
  page_size: number
  has_more: boolean
}