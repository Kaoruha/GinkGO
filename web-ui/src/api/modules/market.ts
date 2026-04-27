import request from '../request'
import type { APIResponse } from '@/types/api'

// 交易所类型
export type ExchangeType = 'okx' | 'binance'

// 环境类型
export type EnvironmentType = 'testnet' | 'production'

// 数据类型
export type DataType = 'ticker' | 'candlesticks' | 'trades' | 'orderbook'

// 交易对信息
export interface TradingPair {
  symbol: string
  base_currency: string
  quote_currency: string
  state: string
  list_time: string
  tick_size: string
  lot_size: string
  min_size: string
}

// 订阅信息
export interface MarketSubscription {
  uuid: string
  exchange: ExchangeType
  environment: EnvironmentType
  symbol: string
  data_types: DataType[]
  is_active: boolean
  create_at: string
  update_at: string
}

// 创建订阅请求
export interface CreateSubscriptionRequest {
  exchange: ExchangeType
  symbol: string
  data_types?: DataType[]
  environment?: EnvironmentType
}

// 更新订阅请求
export interface UpdateSubscriptionRequest {
  data_types?: DataType[]
  is_active?: boolean
}

// Ticker 数据
export interface TickerData {
  symbol: string
  last: string
  lastSz: string
  askPx: string
  bidPx: string
  open24h: string
  high24h: string
  low24h: string
  volCcy24h: string
  vol24h: string
  ts: string
}

// 订单簿数据
export interface OrderBookData {
  symbol: string
  bids: [string, string][]
  asks: [string, string][]
  timestamp: string
}

// 交易对列表响应
export interface TradingPairsResponse {
  pairs: TradingPair[]
  total: number
  exchange: string
  environment: string
}

// 订阅列表响应
export interface SubscriptionsResponse {
  subscriptions: MarketSubscription[]
  total: number
}

/**
 * 市场数据 API
 */
export const marketApi = {
  /**
   * 获取交易对列表
   */
  getTradingPairs: (params?: {
    exchange?: ExchangeType
    environment?: EnvironmentType
    quote_ccy?: string
    search?: string
  }) => {
    return request.get<APIResponse<TradingPairsResponse>>(
      '/api/v1/market/pairs',
      { params }
    )
  },

  /**
   * 获取订阅列表
   */
  getSubscriptions: (params?: {
    exchange?: ExchangeType
    environment?: EnvironmentType
    active_only?: boolean
  }) => {
    return request.get<APIResponse<SubscriptionsResponse>>(
      '/api/v1/market/subscriptions',
      { params }
    )
  },

  /**
   * 创建订阅
   */
  createSubscription: (data: CreateSubscriptionRequest) => {
    return request.post<APIResponse<MarketSubscription>>('/api/v1/market/subscriptions', data)
  },

  /**
   * 更新订阅
   */
  updateSubscription: (uuid: string, data: UpdateSubscriptionRequest) => {
    return request.put<APIResponse<MarketSubscription>>(
      `/api/v1/market/subscriptions/${uuid}`,
      data
    )
  },

  /**
   * 删除订阅
   */
  deleteSubscription: (uuid: string) => {
    return request.delete<APIResponse<void>>(`/api/v1/market/subscriptions/${uuid}`)
  },

  /**
   * 获取 Ticker 数据
   */
  getTicker: (symbol: string, params?: {
    exchange?: ExchangeType
    environment?: EnvironmentType
  }) => {
    return request.get<APIResponse<TickerData>>(
      `/api/v1/market/ticker/${symbol}`,
      { params }
    )
  },

  /**
   * 获取所有 Ticker 数据
   */
  getAllTickers: (params?: {
    exchange?: ExchangeType
    environment?: EnvironmentType
    inst_type?: string
  }) => {
    return request.get<APIResponse<{ tickers: Record<string, TickerData>, total: number }>>(
      '/api/v1/market/tickers',
      { params }
    )
  },

  /**
   * 获取订单簿数据
   */
  getOrderbook: (symbol: string, params?: {
    exchange?: ExchangeType
    depth?: number
  }) => {
    return request.get<APIResponse<OrderBookData>>(
      `/api/v1/market/orderbook/${symbol}`,
      { params }
    )
  }
}

export default marketApi
