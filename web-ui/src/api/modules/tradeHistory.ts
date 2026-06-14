// 后端 API 客户端模块：tradeHistory
import request from '../request'
import type { APIResponse } from '@/types/api'

/** 交易记录 */
export interface TradeRecord {
  trade_id: string
  symbol: string
  side: 'buy' | 'sell'
  price: string
  quantity: string
  quote_quantity: string
  commission: string
  commission_asset: string
  order_id: string
  traded_at: string
}

/** 交易统计 */
export interface TradeStatistics {
  total_trades: number
  total_buy: number
  total_sell: number
  total_volume: number
  total_value: string
  total_commission: string
}

/** 每日汇总 */
export interface DailySummary {
  date: string
  trade_count: number
  buy_count: number
  sell_count: number
  volume: string
  value: string
  commission: string
}

/** 交易历史查询参数 */
export interface TradeHistoryParams {
  start_date?: string
  end_date?: string
  symbol?: string
  page?: number
  page_size?: number
}

/**
 * 交易历史 API
 */
export const tradeHistoryApi = {
  /** 获取交易记录 */
  getTrades: (accountId: string, params?: TradeHistoryParams) =>
    request.get<APIResponse<TradeRecord[]>>(`/api/v1/accounts/${accountId}/trades`, { params }),

  /** 获取交易统计 */
  getStatistics: (accountId: string) =>
    request.get<APIResponse<TradeStatistics>>(`/api/v1/accounts/${accountId}/trades/statistics`),

  /** 获取每日汇总 */
  getDailySummary: (accountId: string, params?: { start_date?: string; end_date?: string }) =>
    request.get<APIResponse<DailySummary[]>>(`/api/v1/accounts/${accountId}/trades/daily-summary`, { params }),

  /** 导出 CSV */
  exportCSV: (accountId: string) =>
    request.get(`/api/v1/accounts/${accountId}/trades/export`, { responseType: 'blob' }),
}

export default tradeHistoryApi
