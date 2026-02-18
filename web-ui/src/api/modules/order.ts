/**
 * 订单和持仓 API 模块
 */
import request from '../request'

export interface Order {
  uuid: string
  portfolio_id: string
  code: string
  direction: number  // 1=LONG, -1=SHORT
  order_type: number
  status: number  // 0=NEW, 1=FILLED, 2=CANCELED, 3=PARTIAL
  volume: number
  limit_price: number
  transaction_price: number
  transaction_volume: number
  fee: number
  timestamp: string
  created_at: string
}

export interface Position {
  uuid: string
  portfolio_id: string
  code: string
  volume: number
  frozen_volume: number
  cost: number
  price: number
  market_value: number
  profit: number
  profit_pct: number
  fee: number
  updated_at: string
}

export interface PositionSummary {
  total_market_value: number
  total_profit: number
  total_fee: number
  position_count: number
}

export interface OrderListParams {
  mode?: 'paper' | 'live'
  portfolio_id?: string
  code?: string
  status?: string
  start_date?: string
  end_date?: string
  page?: number
  size?: number
}

export interface PositionListParams {
  portfolio_id?: string
  code?: string
  page?: number
  size?: number
}

export const orderApi = {
  /**
   * 获取订单列表
   */
  async list(params: OrderListParams = {}): Promise<{ data: Order[], total: number }> {
    const response = await request.get('/api/v1/orders', { params })
    return response.data
  },

  /**
   * 获取订单详情
   */
  async get(orderId: string): Promise<Order> {
    const response = await request.get(`/api/v1/orders/${orderId}`)
    return response.data
  },
}

export const positionApi = {
  /**
   * 获取持仓列表
   */
  async list(params: PositionListParams = {}): Promise<{ data: Position[], total: number, summary: PositionSummary }> {
    const response = await request.get('/api/v1/positions', { params })
    return response.data
  },

  /**
   * 获取持仓详情
   */
  async get(positionId: string): Promise<Position> {
    const response = await request.get(`/api/v1/positions/${positionId}`)
    return response.data
  },
}

// 订单状态映射
export const ORDER_STATUS_MAP: Record<number, { text: string, color: string }> = {
  0: { text: '待成交', color: 'blue' },
  1: { text: '已成交', color: 'green' },
  2: { text: '已取消', color: 'red' },
  3: { text: '部分成交', color: 'orange' },
}

// 订单方向映射
export const ORDER_DIRECTION_MAP: Record<number, { text: string, color: string }> = {
  1: { text: '买入', color: 'red' },
  [-1]: { text: '卖出', color: 'green' },
}
