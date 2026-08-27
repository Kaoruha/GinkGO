import request from '../request'
import type { PaginatedData } from '@/types/api'

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
  /** 最近一次数据更新时间（sync 页展示用，接口可能缺省） */
  latest_update?: string
}

export interface TickData {
  uuid: string
  code: string
  timestamp: string
  price: number
  volume: number
  direction: number
}

export interface AdjustFactorData {
  uuid: string
  code: string
  timestamp: string
  foreadjustfactor: number
  backadjustfactor: number
  adjustfactor: number
}

export interface SyncHistoryRecord {
  uuid: string
  sync_type: string
  code: string
  /** 触发来源(2026-08-18):manual=Web手动 / scheduled=tasktimer定时 */
  trigger_source?: string
  status: string
  started_at: string | null
  completed_at: string | null
  duration_ms: number
  records_processed: number
  records_added: number
  records_updated: number
  records_failed: number
  error_message: string | null
  sync_strategy: string
}

export const dataApi = {
  /**
   * 获取数据统计
   */
  getStats(): Promise<DataStats> {
    return request.get('/api/v1/data/stats')
  },

  // ===== 股票信息 =====
  /**
   * 获取股票列表
   */
  // 后端过滤参数名是 search(api/api/data.py get_stockinfo),前端统一 query,此处做映射
  listStocks(params?: { query?: string; page?: number; page_size?: number }): Promise<PaginatedData<StockInfo>> {
    const { query, ...rest } = params || {}
    return request.get('/api/v1/data/stockinfo', { params: { ...rest, search: query } })
  },

  /**
   * 获取单个股票信息
   */
  getStock(code: string): Promise<StockInfo> {
    return request.get(`/api/v1/data/stockinfo/${code}`)
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
    page_size?: number
  }): Promise<PaginatedData<BarData>> {
    return request.get('/api/v1/data/bars', { params })
  },

  // ===== 数据同步 =====
  /**
   * 发送同步命令
   */
  sync(params: {
    type: string
    codes?: string[]
    start_date?: string
    end_date?: string
  }): Promise<any> {
    return request.post('/api/v1/data/sync', {
      type: params.type,
      codes: params.codes,
      start_date: params.start_date,
      end_date: params.end_date,
    })
  },

  /**
   * 获取数据状态（对接 /api/v1/data/stats）
   */
  getStatus(): Promise<{
    bar_count: number
    tick_count: number
    stock_count: number
    last_sync: string
  }> {
    return request.get('/api/v1/data/stats').then((res: any) => ({
      bar_count: res.total_bars || 0,
      tick_count: res.total_ticks || 0,
      stock_count: res.total_stocks || 0,
      last_sync: res.latest_update || '-',
    }))
  },

  /**
   * 同步股票信息
   */
  syncStockInfo(): Promise<{ task_id: string }> {
    return request.post('/api/v1/data/sync/stockinfo')
  },

  /**
   * 同步 K 线数据
   */
  syncBars(codes: string[]): Promise<{ task_id: string }> {
    return request.post('/api/v1/data/sync/bars', { codes })
  },

  /**
   * 获取同步任务状态
   */
  getSyncStatus(taskId: string): Promise<{ status: string; progress: number; message: string }> {
    return request.get(`/api/v1/data/sync/status/${taskId}`)
  },

  /**
   * 获取同步历史记录
   */
  getSyncHistory(params?: {
    sync_type?: string
    trigger_source?: string
    page?: number
    page_size?: number
  }): Promise<PaginatedData<SyncHistoryRecord>> {
    return request.get('/api/v1/data/sync/history', { params })
  },

  // ===== Tick 数据 =====
  /**
   * 获取 Tick 数据（code 必填）
   */
  getTicks(params: {
    code: string
    start_date?: string
    end_date?: string
    page?: number
    page_size?: number
  }): Promise<PaginatedData<TickData>> {
    return request.get('/api/v1/data/ticks', { params })
  },

  // ===== 数据源 =====
  /**
   * 获取数据源列表
   */
  getSources(): Promise<{ name: string; enabled: boolean; description: string; status: string }[]> {
    return request.get('/api/v1/data/sources')
  },

  // ===== 复权因子 =====
  /**
   * 获取复权因子数据
   */
  getAdjustFactors(params?: {
    code?: string
    start_date?: string
    end_date?: string
    page?: number
    page_size?: number
  }): Promise<PaginatedData<AdjustFactorData>> {
    return request.get('/api/v1/data/adjustfactors', { params })
  },
}
