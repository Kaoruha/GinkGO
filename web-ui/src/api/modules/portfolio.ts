import request from '../request'
<<<<<<< HEAD
import type { APIResponse } from '@/types/api'
import type { RequestOptions } from '@/types/api-request'

// 组件配置参数
export interface ComponentConfig {
  [key: string]: string | number | boolean | null
}

// 策略组件
export interface StrategyComponent {
  uuid: string
  name: string
  type: string
  weight: number
  config?: ComponentConfig
  performance?: {
    return: number
    sharpe: number
    max_drawdown: number
  }
}

// 选股器组件
export interface SelectorComponent {
  uuid: string
  name: string
  type: string
  codes: string[]
  config?: ComponentConfig
}

// Sizer组件
export interface SizerComponent {
  uuid: string
  name: string
  type: string
  config?: ComponentConfig
}

// 风控组件
export interface RiskManagementComponent {
  uuid: string
  name: string
  type: string
  config?: ComponentConfig
=======

export interface PortfolioComponent {
  uuid: string
  name: string
  config?: Record<string, any>
  weight?: number
}

export interface PortfolioComponents {
  selectors: PortfolioComponent[]
  sizer: PortfolioComponent | null
  strategies: PortfolioComponent[]
  risk_managers: PortfolioComponent[]
  analyzers: PortfolioComponent[]
>>>>>>> 011-quant-research
}

export interface Portfolio {
  uuid: string
  name: string
<<<<<<< HEAD
  mode: 'BACKTEST' | 'PAPER' | 'LIVE'
  state: 'INITIALIZED' | 'RUNNING' | 'PAUSED' | 'STOPPED'
  config_locked: boolean
  net_value: number
  created_at: string
}

export interface PortfolioDetail extends Portfolio {
  initial_cash: number
  current_cash: number
  benchmark?: string
  description?: string
  // 组件UUID引用
  selector_uuid?: string
  sizer_uuid?: string
  // 组件列表（包含详细信息）
  strategies: StrategyComponent[]
  selectors: SelectorComponent[]
  sizers: SizerComponent[]
  risk_managers: RiskManagementComponent[]
  analyzers: AnalyzerComponent[]
  // 持仓信息
  positions: Array<{
    code: string
    volume: number
    cost_price: number
    current_price: number
  }>
  // 风险预警
  risk_alerts: Array<{
    uuid: string
    type: string
    level: string
    message: string
    triggered_at: string
    handled: boolean
  }>
}

// 分析器组件
export interface AnalyzerComponent {
  uuid: string
  name: string
  type: string
  config?: ComponentConfig
}

// 创建/更新Portfolio的数据结构
export interface PortfolioCreateData {
  name: string
  initial_cash: number
  mode: 'BACKTEST' | 'PAPER' | 'LIVE'
  benchmark?: string
  description?: string
  selectors: Array<{
    component_uuid: string
    config?: Record<string, any>
  }>
  sizer_uuid: string
  strategies: Array<{
    component_uuid: string
    weight: number
    config?: Record<string, any>
  }>
  risk_managers?: Array<{
    component_uuid: string
    config?: Record<string, any>
  }>
  analyzers?: Array<{
    component_uuid: string
    config?: Record<string, any>
  }>
=======
  desc?: string
  mode: number | 'BACKTEST' | 'PAPER' | 'LIVE'
  state: number | 'RUNNING' | 'PAUSED' | 'STOPPED' | 'COMPLETED' | 'ERROR'
  initial_cash: number
  current_cash: number
  net_value: number
  config_locked: boolean
  positions: any[]
  risk_alerts: any[]
  components?: PortfolioComponents
  created_at: string
  updated_at: string
}

export interface PortfolioCreateRequest {
  name: string
  mode: 'BACKTEST' | 'PAPER' | 'LIVE'
  initial_cash?: number
  benchmark?: string
  description?: string
  selectors?: { component_uuid: string; config?: Record<string, any> }[]
  sizer_uuid?: string
  sizer_config?: Record<string, any>
  strategies?: { component_uuid: string; weight?: number; config?: Record<string, any> }[]
  risk_managers?: { component_uuid: string; config?: Record<string, any> }[]
  analyzers?: { component_uuid: string; config?: Record<string, any> }[]
  risk_config?: Record<string, any>
}

export interface PortfolioListParams {
  mode?: string
  state?: string
  page?: number
  page_size?: number
  keyword?: string
>>>>>>> 011-quant-research
}

export const portfolioApi = {
  /**
<<<<<<< HEAD
   * 获取Portfolio列表
   * @param params 查询参数
   * @param options 请求选项（支持 signal 取消请求）
   */
  list(params?: { mode?: string }, options?: RequestOptions): Promise<APIResponse<Portfolio[]>> {
    return request.get('/v1/portfolios/', { params, signal: options?.signal })
  },

  /**
   * 获取Portfolio详情
   * @param uuid Portfolio UUID
   * @param options 请求选项（支持 signal 取消请求）
   */
  get(uuid: string, options?: RequestOptions): Promise<APIResponse<PortfolioDetail>> {
    return request.get(`/v1/portfolios/${uuid}`, { signal: options?.signal })
  },

  /**
   * 创建Portfolio
   * @param data Portfolio 数据
   * @param options 请求选项（支持 signal 取消请求）
   */
  create(data: PortfolioCreateData, options?: RequestOptions): Promise<APIResponse<PortfolioDetail>> {
    return request.post('/v1/portfolios/', data, { signal: options?.signal })
  },

  /**
   * 更新Portfolio
   * @param uuid Portfolio UUID
   * @param data 更新数据
   * @param options 请求选项（支持 signal 取消请求）
   */
  update(uuid: string, data: Partial<PortfolioCreateData>, options?: RequestOptions): Promise<APIResponse<PortfolioDetail>> {
    return request.put(`/v1/portfolios/${uuid}`, data, { signal: options?.signal })
  },

  /**
   * 删除Portfolio
   * @param uuid Portfolio UUID
   * @param options 请求选项（支持 signal 取消请求）
   */
  delete(uuid: string, options?: RequestOptions): Promise<void> {
    return request.delete(`/v1/portfolios/${uuid}`, { signal: options?.signal })
  }
=======
   * 获取 Portfolio 列表
   */
  list(params?: PortfolioListParams): Promise<{ data: Portfolio[]; total: number }> {
    return request.get('/v1/portfolio', { params })
  },

  /**
   * 获取单个 Portfolio
   */
  get(uuid: string): Promise<Portfolio> {
    return request.get(`/v1/portfolio/${uuid}`)
  },

  /**
   * 创建 Portfolio
   */
  create(data: PortfolioCreateRequest): Promise<Portfolio> {
    return request.post('/v1/portfolio', data)
  },

  /**
   * 更新 Portfolio
   */
  update(uuid: string, data: Partial<Portfolio>): Promise<Portfolio> {
    return request.put(`/v1/portfolio/${uuid}`, data)
  },

  /**
   * 删除 Portfolio
   */
  delete(uuid: string): Promise<void> {
    return request.delete(`/v1/portfolio/${uuid}`)
  },

  /**
   * 启动 Portfolio
   */
  start(uuid: string): Promise<void> {
    return request.post(`/v1/portfolio/${uuid}/start`)
  },

  /**
   * 停止 Portfolio
   */
  stop(uuid: string): Promise<void> {
    return request.post(`/v1/portfolio/${uuid}/stop`)
  },

  /**
   * 获取 Portfolio 统计
   */
  getStats(): Promise<{
    total: number
    running: number
    avg_net_value: number
    total_assets: number
  }> {
    return request.get('/v1/portfolio/stats')
  },
>>>>>>> 011-quant-research
}
