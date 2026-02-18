import request from '../request'

export interface StockInfo {
  uuid: string
  code: string
  name: string
  exchange: string
  type: string
  list_date: string
  is_active: boolean
}

export interface BarData {
  uuid: string
  code: string
  timestamp: string
  open: number
  high: number
  low: number
  close: number
  volume: number
  amount: number
}

export interface DataStats {
  total_stocks: number
  total_bars: number
  total_ticks: number
  total_adjust_factors: number
}

export const dataApi = {
  /**
   * 获取数据统计
   */
  getStats(): Promise<DataStats> {
    return request.get('/v1/data/stats')
  },

  // ===== 股票信息 =====
  /**
   * 获取股票列表
   */
  listStocks(params?: { query?: string; page?: number; page_size?: number }): Promise<{ data: StockInfo[]; total: number }> {
    return request.get('/v1/data/stockinfo', { params })
  },

  /**
   * 获取单个股票信息
   */
  getStock(code: string): Promise<StockInfo> {
    return request.get(`/v1/data/stockinfo/${code}`)
  },

  // ===== K线数据 =====
  /**
   * 获取 K 线数据
   */
  getBars(params: {
    code: string
    start_date?: string
    end_date?: string
    frequency?: string
    adjustment?: string
    page?: number
    size?: number
  }): Promise<{ data: BarData[]; total: number }> {
    const { code, ...queryParams } = params
    return request.get(`/v1/data/bars/${code}`, { params: queryParams })
  },

  // ===== 数据同步 =====
  /**
   * 同步股票信息
   */
  syncStockInfo(): Promise<{ task_id: string }> {
    return request.post('/v1/data/sync/stockinfo')
  },

  /**
   * 同步 K 线数据
   */
  syncBars(codes: string[]): Promise<{ task_id: string }> {
    return request.post('/v1/data/sync/bars', { codes })
  },

  /**
   * 获取同步任务状态
   */
  getSyncStatus(taskId: string): Promise<{ status: string; progress: number; message: string }> {
    return request.get(`/v1/data/sync/status/${taskId}`)
  },
}
