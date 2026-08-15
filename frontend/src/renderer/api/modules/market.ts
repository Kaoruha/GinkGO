import request from '../request'

// 行情读接口统一 skipErrorToast:后端 market 模块尚未实现(404),且 tickers 为 5s 轮询——
// 全局 toast 会刷屏;由 MarketData 页内联降级态交代,写操作(订阅 CRUD)保留 toast
const SILENT_READ = { skipErrorToast: true } as const

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
  }): Promise<TradingPairsResponse> => {
    return request.get(
      '/api/v1/market/pairs',
      { params, ...SILENT_READ }
    )
  },

  /**
   * 获取订阅列表
   */
  getSubscriptions: (params?: {
    exchange?: ExchangeType
    environment?: EnvironmentType
    active_only?: boolean
  }): Promise<SubscriptionsResponse> => {
    return request.get(
      '/api/v1/market/subscriptions',
      { params, ...SILENT_READ }
    )
  },

  /**
   * 创建订阅
   */
  createSubscription: (data: CreateSubscriptionRequest): Promise<MarketSubscription> => {
    return request.post('/api/v1/market/subscriptions', data)
  },

  /**
   * 更新订阅
   */
  updateSubscription: (uuid: string, data: UpdateSubscriptionRequest): Promise<MarketSubscription> => {
    return request.put(
      `/api/v1/market/subscriptions/${uuid}`,
      data
    )
  },

  /**
   * 删除订阅
   */
  deleteSubscription: (uuid: string): Promise<void> => {
    return request.delete(`/api/v1/market/subscriptions/${uuid}`)
  },

  /**
   * 获取 Ticker 数据
   */
  getTicker: (symbol: string, params?: {
    exchange?: ExchangeType
    environment?: EnvironmentType
  }): Promise<TickerData> => {
    return request.get(
      `/api/v1/market/ticker/${symbol}`,
      { params, ...SILENT_READ }
    )
  },

  /**
   * 获取所有 Ticker 数据
   */
  getAllTickers: (params?: {
    exchange?: ExchangeType
    environment?: EnvironmentType
    inst_type?: string
  }): Promise<{ tickers: Record<string, TickerData>, total: number }> => {
    return request.get(
      '/api/v1/market/tickers',
      { params, ...SILENT_READ }
    )
  },

  /**
   * 获取订单簿数据
   */
  getOrderbook: (symbol: string, params?: {
    exchange?: ExchangeType
    depth?: number
  }): Promise<OrderBookData> => {
    return request.get(
      `/api/v1/market/orderbook/${symbol}`,
      { params, ...SILENT_READ }
    )
  }
}

export default marketApi
