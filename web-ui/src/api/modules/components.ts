import request from '../request'

// ==================== 组件管理 ====================

export interface ComponentSummary {
  uuid: string
  name: string
  component_type: string  // strategy, analyzer, risk, sizer, selector
  file_type: number
  description?: string
  created_at: string
  updated_at?: string
  is_active: boolean
}

export interface ComponentDetail {
  uuid: string
  name: string
  component_type: string
  file_type: number
  code?: string
  description?: string
  parameters: Array<{ [key: string]: any }>
  created_at: string
  updated_at?: string
}

export const componentsApi = {
  /**
   * 获取组件列表
   */
  list(params?: { component_type?: string; is_active?: boolean }): Promise<ComponentSummary[]> {
    return request.get('/components', { params })
  },

  /**
   * 获取组件详情
   */
  get(uuid: string): Promise<ComponentDetail> {
    return request.get(`/components/${uuid}`)
  },

  /**
   * 创建组件
   */
  create(data: {
    name: string
    component_type: string
    code: string
    description?: string
  }): Promise<ComponentDetail> {
    return request.post('/components', data)
  },

  /**
   * 更新组件
   */
  update(uuid: string, data: {
    name?: string
    code?: string
    description?: string
    parameters?: Record<string, any>
  }): Promise<{ message: string }> {
    return request.put(`/components/${uuid}`, data)
  },

  /**
   * 删除组件
   */
  delete(uuid: string): Promise<{ message: string }> {
    return request.delete(`/components/${uuid}`)
  }
}

// ==================== 数据管理 ====================

// 分页响应
export interface PaginatedResponse<T> {
  items: T[]
  total: number
  page: number
  page_size: number
  total_pages: number
}

export interface StockInfoSummary {
  uuid: string
  code: string
  name?: string
  market?: string
  industry?: string
  is_active: boolean
  updated_at?: string
}

export interface BarDataSummary {
  uuid: string
  code: string
  date: string
  period: string
  open: number
  high: number
  low: number
  close: number
  volume: number
  amount?: number
}

export interface TickDataSummary {
  uuid: string
  code: string
  timestamp: string
  price: number
  volume: number
  direction: number
}

export interface AdjustFactorSummary {
  uuid: string
  code: string
  date: string
  factor: number
}

export interface DataStats {
  total_stocks: number
  total_bars: number
  total_ticks: number
  total_adjust_factors: number
  data_sources: string[]
  latest_update?: string
}

export interface DataUpdateRequest {
  type: string  // stockinfo, bars, ticks, adjustfactor
  codes?: string[]
  start_date?: string
  end_date?: string
}

export interface DataSource {
  name: string
  enabled: boolean
  description: string
  status: string
}

export const dataApi = {
  /**
   * 获取数据统计
   */
  getStats(): Promise<DataStats> {
    return request.get('/data/stats')
  },

  /**
   * 获取股票信息列表（分页）
   */
  getStockInfo(params?: {
    search?: string
    page?: number
    page_size?: number
  }): Promise<PaginatedResponse<StockInfoSummary>> {
    return request.get('/data/stockinfo', { params })
  },

  /**
   * 获取K线数据列表（分页）
   */
  getBars(params?: {
    code?: string
    start_date?: string
    end_date?: string
    page?: number
    page_size?: number
  }): Promise<PaginatedResponse<BarDataSummary>> {
    return request.get('/data/bars', { params })
  },

  /**
   * 获取Tick数据列表（分页）
   */
  getTicks(params?: {
    code?: string
    start_date?: string
    end_date?: string
    page?: number
    page_size?: number
  }): Promise<PaginatedResponse<TickDataSummary>> {
    return request.get('/data/ticks', { params })
  },

  /**
   * 获取复权因子列表（分页）
   */
  getAdjustFactors(params?: {
    code?: string
    start_date?: string
    end_date?: string
    page?: number
    page_size?: number
  }): Promise<PaginatedResponse<AdjustFactorSummary>> {
    return request.get('/data/adjustfactors', { params })
  },

  /**
   * 触发数据更新
   */
  updateData(data: DataUpdateRequest): Promise<{
    message: string
    type: string
    codes?: string[]
  }> {
    return request.post('/data/update', data)
  },

  /**
   * 获取数据源状态
   */
  getDataSources(): Promise<DataSource[]> {
    return request.get('/data/sources')
  }
}
