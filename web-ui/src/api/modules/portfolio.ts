import request from '../request'

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
}

export interface Portfolio {
  uuid: string
  name: string
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
}

export const portfolioApi = {
  /**
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
}
