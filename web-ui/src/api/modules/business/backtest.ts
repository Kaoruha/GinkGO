import { get, post, put, del, getList } from '../common'
import type { APIResponse, PaginatedResponse } from '../../../types/common'

/**
 * Upstream: data-model.md
 * Downstream: BacktestList.vue, BacktestDetail.vue, stores/backtest.ts
 * Role: 回测任务 API 接口，提供 CRUD 和操作接口
 */

/**
 * 回测任务状态（六态模型）
 */
export type BacktestState = 'created' | 'pending' | 'running' | 'completed' | 'stopped' | 'failed'

/**
 * 启动回测响应
 */
export interface StartBacktestResponse {
  uuid: string          // 新任务的 UUID（启动创建新实例）
  status: BacktestState
  message: string
}

/**
 * 操作响应
 */
export interface OperationResponse {
  success: boolean
  message: string
}

// 回测任务摘要
export interface BacktestTaskSummary {
  uuid: string
  name: string
  portfolio_name: string
  status: BacktestState
  progress: number
  created_at: string
}

// 回测任务详情
export interface BacktestTaskDetail extends BacktestTaskSummary {
  portfolio_uuid: string
  engine_uuid?: string | null
  config: BacktestConfig
  result?: BacktestResult
  worker_id?: string | null
  error?: string | null
  creator_id: string
  updated_at: string
  started_at?: string
  completed_at?: string
}

// 回测配置
export interface BacktestConfig {
  start_date: string
  end_date: string
  initial_cash?: number
  commission_rate: number
  slippage_rate: number
  broker_attitude: number
}

// 回测结果
export interface BacktestResult {
  total_return: number
  annual_return: number
  sharpe_ratio: number
  max_drawdown: number
  win_rate: number
}

/**
 * 获取回测任务列表
 */
export function getBacktestList(params?: {
  page?: number
  pageSize?: number
  status?: BacktestState
}) {
  return getList<PaginatedResponse<BacktestTaskSummary>>('/v1/backtests', params)
}

/**
 * 获取回测任务详情
 */
export function getBacktestDetail(uuid: string) {
  return get<BacktestTaskDetail>(`/v1/backtests/${uuid}`)
}

/**
 * 创建回测任务
 */
export function createBacktest(data: {
  name: string
  portfolio_uuids: string[]
  engine_config: BacktestConfig
}) {
  return post<BacktestTaskDetail>('/v1/backtests/', data)
}

/**
 * 启动回测任务
 * 返回新创建的任务 UUID
 */
export function startBacktest(uuid: string) {
  return post<StartBacktestResponse>(`/v1/backtests/${uuid}/start`)
}

/**
 * 停止回测任务
 */
export function stopBacktest(uuid: string) {
  return post<OperationResponse>(`/v1/backtests/${uuid}/stop`)
}

/**
 * 取消回测任务
 */
export function cancelBacktest(uuid: string) {
  return post<OperationResponse>(`/v1/backtests/${uuid}/cancel`)
}

/**
 * 删除回测任务
 */
export function deleteBacktest(uuid: string) {
  return del<OperationResponse>(`/v1/backtests/${uuid}`)
}

/**
 * 获取回测日志
 */
export function getBacktestLogs(uuid: string, params?: {
  page?: number
  pageSize?: number
}) {
  return get<PaginatedResponse<any>>(`/v1/backtests/${uuid}/logs`, params)
}

/**
 * 获取回测事件流（SSE）
 */
export function getBacktestEvents(uuid: string): EventSource {
  return new EventSource(
    `/api/v1/backtests/${uuid}/events`,
    { withCredentials: true }
  )
}
