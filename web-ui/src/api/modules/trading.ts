import request from '../request'
import type { APIResponse } from '@/types/api'

// 账户类型
export type AccountType = 'paper' | 'live'

// 账户状态
export type AccountStatus = 'stopped' | 'running' | 'error'

// 订单状态
export type OrderStatus = 'pending' | 'partial' | 'filled' | 'cancelled' | 'rejected'

// 订单方向
export type OrderSide = 'buy' | 'sell'

// 模拟盘账户
export interface PaperAccount {
  uuid: string
  name: string
  initial_capital: number
  available_cash: number
  position_value: number
  total_asset: number
  today_pnl: number
  total_pnl: number
  status: AccountStatus
  created_at: string
}

// 持仓信息
export interface Position {
  code: string
  name: string
  shares: number
  cost: number
  current: number
  market_value: number
  pnl: number
  pnl_ratio: number
  updated_at: string
}

// 订单信息
export interface Order {
  order_id: string
  strategy_id?: string
  account_id: string
  code: string
  name: string
  side: OrderSide
  price: number
  volume: number
  filled: number
  avg_price: number
  status: OrderStatus
  time: string
  updated_at: string
}

// 实盘账户连接信息
export interface LiveAccount {
  uuid: string
  name: string
  broker_type: string
  status: 'connected' | 'disconnected' | 'error'
  total_asset: number
  available_cash: number
  position_value: number
  today_pnl: number
}

// 风险状态
export interface RiskStatus {
  account_id: string
  position_ratio: number
  total_pnl_ratio: number
  max_drawdown: number
  status: 'normal' | 'warning' | 'danger'
  warnings: string[]
}

// 创建模拟盘请求
export interface CreatePaperAccount {
  name: string
  initial_capital: number
  slippage_model: 'fixed' | 'percentage' | 'none'
  slippage_value?: number
  slippage_pct?: number
  commission_rate: number
  restrictions: string[]  // ['t1', 'limit', 'time']
  data_source: 'replay' | 'paper'
  replay_date?: string
}

// API方法

/**
 * 获取模拟盘账户列表
 */
export function getPaperAccounts() {
  return request<APIResponse<PaperAccount[]>>({
    url: '/v1/paper-trading/accounts',
    method: 'GET'
  })
}

/**
 * 创建模拟盘账户
 */
export function createPaperAccount(data: CreatePaperAccount) {
  return request<APIResponse<{ account_id: string }>>({
    url: '/v1/paper-trading/accounts',
    method: 'POST',
    data
  })
}

/**
 * 获取模拟盘账户详情
 */
export function getPaperAccount(accountId: string) {
  return request<APIResponse<PaperAccount & {
    positions: Position[]
    active_orders: Order[]
    today_trades: Order[]
  }>>({
    url: `/v1/paper-trading/accounts/${accountId}`,
    method: 'GET'
  })
}

/**
 * 启动模拟盘
 */
export function startPaperTrading(accountId: string, strategyIds: string[]) {
  return request<APIResponse<{ success: boolean }>>({
    url: `/v1/paper-trading/${accountId}/start`,
    method: 'POST',
    data: { strategy_ids: strategyIds }
  })
}

/**
 * 停止模拟盘
 */
export function stopPaperTrading(accountId: string) {
  return request<APIResponse<{ success: boolean }>>({
    url: `/v1/paper-trading/${accountId}/stop`,
    method: 'POST'
  })
}

/**
 * 获取模拟盘持仓
 */
export function getPaperPositions(accountId: string) {
  return request<APIResponse<Position[]>>({
    url: `/v1/paper-trading/${accountId}/positions`,
    method: 'GET'
  })
}

/**
 * 获取模拟盘订单
 */
export function getPaperOrders(accountId: string, status?: OrderStatus[]) {
  return request<APIResponse<Order[]>>({
    url: `/v1/paper-trading/${accountId}/orders`,
    method: 'GET',
    params: { status }
  })
}

/**
 * 撤销模拟盘订单
 */
export function cancelPaperOrder(accountId: string, orderId: string) {
  return request<APIResponse<{ success: boolean }>>({
    url: `/v1/paper-trading/${accountId}/orders/${orderId}`,
    method: 'DELETE'
  })
}

/**
 * 获取模拟盘日报
 */
export function getPaperReport(accountId: string, date: string) {
  return request<APIResponse<{
    date: string
    total_return: number
    daily_return: number
    trades_count: number
    positions_count: number
  }>>({
    url: `/v1/paper-trading/${accountId}/report/daily`,
    method: 'GET',
    params: { date }
  })
}

// 实盘相关API

/**
 * 获取实盘账户列表
 */
export function getLiveAccounts() {
  return request<APIResponse<LiveAccount[]>>({
    url: '/v1/live-trading/accounts',
    method: 'GET'
  })
}

/**
 * 连接券商
 */
export function connectBroker(accountId: string) {
  return request<APIResponse<{ success: boolean }>>({
    url: `/v1/live-trading/accounts/${accountId}/connect`,
    method: 'POST'
  })
}

/**
 * 断开券商连接
 */
export function disconnectBroker(accountId: string) {
  return request<APIResponse<{ success: boolean }>>({
    url: `/v1/live-trading/accounts/${accountId}/disconnect`,
    method: 'POST'
  })
}

/**
 * 获取实盘持仓
 */
export function getLivePositions(accountId: string) {
  return request<APIResponse<Position[]>>({
    url: `/v1/live-trading/${accountId}/positions`,
    method: 'GET'
  })
}

/**
 * 获取实盘活跃订单
 */
export function getLiveActiveOrders(accountId: string) {
  return request<APIResponse<Order[]>>({
    url: `/v1/live-trading/${accountId}/active-orders`,
    method: 'GET'
  })
}

/**
 * 撤销实盘订单
 */
export function cancelLiveOrder(accountId: string, orderId: string) {
  return request<APIResponse<{ success: boolean }>>({
    url: `/v1/live-trading/${accountId}/orders/${orderId}`,
    method: 'DELETE'
  })
}

/**
 * 获取资金信息
 */
export function getLiveCapital(accountId: string) {
  return request<APIResponse<{
    total_asset: number
    available_cash: number
    position_value: number
    frozen_cash: number
    today_pnl: number
  }>>({
    url: `/v1/live-trading/${accountId}/capital`,
    method: 'GET'
  })
}

/**
 * 获取风险状态
 */
export function getRiskStatus(accountId: string) {
  return request<APIResponse<RiskStatus>>({
    url: `/v1/live-trading/${accountId}/risk/status`,
    method: 'GET'
  })
}

/**
 * 触发熔断
 */
export function triggerCircuitBreaker(accountId: string) {
  return request<APIResponse<{ success: boolean }>>({
    url: `/v1/live-trading/${accountId}/risk/circuit-breaker`,
    method: 'POST'
  })
}

/**
 * 获取交易日志
 */
export function getTradingLogs(params: {
  account_id: string
  account_type: AccountType
  log_type?: 'strategy' | 'order' | 'system'
  start_date?: string
  end_date?: string
  limit?: number
}) {
  return request<APIResponse<Array<{
    time: string
    type: string
    level: string
    message: string
    details?: any
  }>>>({
    url: '/v1/live-trading/logs',
    method: 'GET',
    params
  })
}
