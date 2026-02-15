import { get, post, put, del, getList } from '../common'
import type { APIResponse, PaginatedResponse } from '../../../types/common'

/**
 * 回测业务 API 模块
 * 封装回测相关的所有 API 调用
 */

// 回测任务状态
export type BacktestState = 'PENDING' | 'RUNNING' | 'COMPLETED' | 'FAILED' | 'CANCELLED'

// 回测任务摘要
export interface BacktestTaskSummary {
  uuid: string
  name: string
  portfolio_name: string
  state: BacktestState
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
  state?: BacktestState
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
 */
export function startBacktest(uuid: string) {
  return post<any>(`/v1/backtests/${uuid}/start`)
}

/**
 * 停止回测任务
 */
export function stopBacktest(uuid: string) {
  return post<any>(`/v1/backtests/${uuid}/stop`)
}

/**
 * 删除回测任务
 */
export function deleteBacktest(uuid: string) {
  return del<any>(`/v1/backtests/${uuid}`)
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
