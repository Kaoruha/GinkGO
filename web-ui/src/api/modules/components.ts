import request from '../request'
<<<<<<< HEAD
import type { RequestOptions } from '@/types/api-request'
import type {
  ComponentSummary,
  ComponentDetail,
  ComponentCreate,
  ComponentUpdate,
  ComponentParameter,
  ComponentParameterDefinitions
} from '@/types/component'

// ==================== 组件管理 ====================

// 重新导出类型（保持向后兼容）
export type {
  ComponentSummary,
  ComponentDetail,
  ComponentCreate,
  ComponentUpdate,
  ComponentParameter,
  ComponentParameterDefinitions,
  ComponentConfig,
  ParamType
} from '@/types/component'

export const componentsApi = {
  /**
   * 获取组件列表
   * @param params 查询参数
   * @param options 请求选项（支持 signal 取消请求）
   */
  list(params?: { component_type?: string; is_active?: boolean }, options?: RequestOptions): Promise<ComponentSummary[]> {
    return request.get('/v1/components/', { params, signal: options?.signal })
  },

  /**
   * 获取组件详情
   * @param uuid 组件 UUID
   * @param options 请求选项（支持 signal 取消请求）
   */
  get(uuid: string, options?: RequestOptions): Promise<ComponentDetail> {
    return request.get(`/v1/components/${uuid}`, { signal: options?.signal })
  },

  /**
   * 创建组件
   * @param data 组件数据
   * @param options 请求选项（支持 signal 取消请求）
   */
  create(data: {
    name: string
    component_type: string
    code: string
    description?: string
  }, options?: RequestOptions): Promise<ComponentDetail> {
    return request.post('/v1/components/', data, { signal: options?.signal })
  },

  /**
   * 更新组件
   * @param uuid 组件 UUID
   * @param data 更新数据
   * @param options 请求选项（支持 signal 取消请求）
   */
  update(uuid: string, data: {
    name?: string
    code?: string
    description?: string
    parameters?: Record<string, any>
  }, options?: RequestOptions): Promise<{ message: string }> {
    return request.put(`/v1/components/${uuid}`, data, { signal: options?.signal })
  },

  /**
   * 删除组件
   * @param uuid 组件 UUID
   * @param options 请求选项（支持 signal 取消请求）
   */
  delete(uuid: string, options?: RequestOptions): Promise<{ message: string }> {
    return request.delete(`/v1/components/${uuid}`, { signal: options?.signal })
  },

  // ==================== 组件参数管理 ====================

  /**
   * 获取组件参数定义
   * @param componentName 组件名称
   * @param options 请求选项（支持 signal 取消请求）
   */
  getParameters(componentName: string, options?: RequestOptions): Promise<ComponentParameter[]> {
    return request.get(`/v1/components/parameters/${componentName}`, { signal: options?.signal })
  },

  /**
   * 获取所有组件参数定义
   * @param options 请求选项（支持 signal 取消请求）
   */
  getAllParameters(options?: RequestOptions): Promise<ComponentParameterDefinitions> {
    return request.get('/v1/components/parameters', { signal: options?.signal })
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
   * @param options 请求选项（支持 signal 取消请求）
   */
  getStats(options?: RequestOptions): Promise<DataStats> {
    return request.get('/v1/data/stats', { signal: options?.signal })
  },

  /**
   * 获取股票信息列表（分页）
   * @param params 查询参数
   * @param options 请求选项（支持 signal 取消请求）
   */
  getStockInfo(params?: {
    search?: string
    page?: number
    page_size?: number
  }, options?: RequestOptions): Promise<PaginatedResponse<StockInfoSummary>> {
    return request.get('/v1/data/stockinfo', { params, signal: options?.signal })
  },

  /**
   * 获取K线数据列表（分页）
   * @param params 查询参数
   * @param options 请求选项（支持 signal 取消请求）
   */
  getBars(params?: {
    code?: string
    start_date?: string
    end_date?: string
    page?: number
    page_size?: number
  }, options?: RequestOptions): Promise<PaginatedResponse<BarDataSummary>> {
    return request.get('/v1/data/bars', { params, signal: options?.signal })
  },

  /**
   * 获取Tick数据列表（分页）
   * @param params 查询参数
   * @param options 请求选项（支持 signal 取消请求）
   */
  getTicks(params?: {
    code?: string
    start_date?: string
    end_date?: string
    page?: number
    page_size?: number
  }, options?: RequestOptions): Promise<PaginatedResponse<TickDataSummary>> {
    return request.get('/v1/data/ticks', { params, signal: options?.signal })
  },

  /**
   * 获取复权因子列表（分页）
   * @param params 查询参数
   * @param options 请求选项（支持 signal 取消请求）
   */
  getAdjustFactors(params?: {
    code?: string
    start_date?: string
    end_date?: string
    page?: number
    page_size?: number
  }, options?: RequestOptions): Promise<PaginatedResponse<AdjustFactorSummary>> {
    return request.get('/v1/data/adjustfactors', { params, signal: options?.signal })
  },

  /**
   * 触发数据更新
   * @param data 更新请求
   * @param options 请求选项（支持 signal 取消请求）
   */
  updateData(data: DataUpdateRequest, options?: RequestOptions): Promise<{
    message: string
    type: string
    codes?: string[]
  }> {
    return request.post('/v1/data/update', data, { signal: options?.signal })
  },

  /**
   * 获取数据源状态
   * @param options 请求选项（支持 signal 取消请求）
   */
  getDataSources(options?: RequestOptions): Promise<DataSource[]> {
    return request.get('/v1/data/sources', { signal: options?.signal })
  }
=======

export interface ComponentSummary {
  uuid: string
  name: string
  type: string
  component_type: 'strategy' | 'selector' | 'sizer' | 'risk' | 'analyzer'
  description?: string
  version?: string
  is_latest?: boolean
  params?: any[]
  parameters?: any[]
}

export const componentsApi = {
  /**
   * 获取所有组件列表
   */
  async list(): Promise<ComponentSummary[]> {
    const [strategies, selectors, risks, sizers, analyzers] = await Promise.all([
      this.getStrategies(),
      this.getSelectors(),
      this.getRisks(),
      this.getSizers(),
      this.getAnalyzers(),
    ])
    return [...strategies, ...selectors, ...risks, ...sizers, ...analyzers]
  },

  /**
   * 获取策略组件列表
   */
  async getStrategies(): Promise<ComponentSummary[]> {
    const res: any = await request.get('/v1/components/strategies')
    return (res.data || []).map((item: any) => ({ ...item, component_type: 'strategy', parameters: item.params }))
  },

  /**
   * 获取选股器组件列表
   */
  async getSelectors(): Promise<ComponentSummary[]> {
    const res: any = await request.get('/v1/components/selectors')
    return (res.data || []).map((item: any) => ({ ...item, component_type: 'selector', parameters: item.params }))
  },

  /**
   * 获取风控组件列表
   */
  async getRisks(): Promise<ComponentSummary[]> {
    const res: any = await request.get('/v1/components/risks')
    return (res.data || []).map((item: any) => ({ ...item, component_type: 'risk', parameters: item.params }))
  },

  /**
   * 获取仓位组件列表
   */
  async getSizers(): Promise<ComponentSummary[]> {
    const res: any = await request.get('/v1/components/sizers')
    return (res.data || []).map((item: any) => ({ ...item, component_type: 'sizer', parameters: item.params }))
  },

  /**
   * 获取分析器组件列表
   */
  async getAnalyzers(): Promise<ComponentSummary[]> {
    const res: any = await request.get('/v1/components/analyzers')
    return (res.data || []).map((item: any) => ({ ...item, component_type: 'analyzer', parameters: item.params }))
  },

  /**
   * 获取指定组件的所有版本
   */
  async getVersions(name: string, type: number): Promise<ComponentSummary[]> {
    const res: any = await request.get(`/v1/file/${name}/versions?type=${type}`)
    return (res.data || []).map((item: any) => ({ ...item, parameters: item.params }))
  },
>>>>>>> 011-quant-research
}
