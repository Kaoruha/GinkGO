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

/**
 * 后端统一响应信封。
 * request.ts 响应拦截器已 `return data`（= response.data = 后端 body），
 * 故 request.get() 返回的已经是 body 本身；API 模块不得再 `.data` 二次解包。
 * 后端 orders/positions 端点用 ok(data=...)，body = {code, data, message}，
 * 无 total/meta（分页由调用方自行处理）。
 */
export interface ApiResponse<T> {
  code: number
  data: T
  message: string
  trace_id?: string
}

export const orderApi = {
  /**
   * 获取订单列表
   */
  list(params: OrderListParams = {}): Promise<ApiResponse<Order[]>> {
    return request.get('/api/v1/orders', { params })
  },

  /**
   * 获取订单详情
   */
  get(orderId: string): Promise<ApiResponse<Order>> {
    return request.get(`/api/v1/orders/${orderId}`)
  },
}

export const positionApi = {
  /**
   * 获取持仓列表
   */
  list(params: PositionListParams = {}): Promise<ApiResponse<Position[]>> {
    return request.get('/api/v1/positions', { params })
  },

  /**
   * 获取持仓详情
   */
  get(positionId: string): Promise<ApiResponse<Position>> {
    return request.get(`/api/v1/positions/${positionId}`)
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
