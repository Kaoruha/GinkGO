import request from '../request'

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
}

// Note: Analyzers 已移至 Engine 级别配置

export interface Portfolio {
  uuid: string
  name: string
  mode: 'BACKTEST' | 'PAPER' | 'LIVE'
  state: 'INITIALIZED' | 'RUNNING' | 'PAUSED' | 'STOPPED'
  config_locked: boolean
  net_value: number
  created_at: string
}

export interface PortfolioDetail extends Portfolio {
  initial_cash: number
  current_cash: number
  positions: Array<{
    code: string
    volume: number
    cost_price: number
    current_price: number
  }>
  // 组件列表
  strategies: StrategyComponent[]
  selectors: SelectorComponent[]
  sizers: SizerComponent[]
  risk_managers: RiskManagementComponent[]
  // Note: Analyzers 已移至 Engine 级别配置
  risk_alerts: Array<{
    uuid: string
    type: string
    level: string
    message: string
    triggered_at: string
    handled: boolean
  }>
}

export const portfolioApi = {
  /**
   * 获取Portfolio列表
   */
  list(params?: { mode?: string }): Promise<Portfolio[]> {
    return request.get('/portfolio', { params })
  },

  /**
   * 获取Portfolio详情
   */
  get(uuid: string): Promise<PortfolioDetail> {
    return request.get(`/portfolio/${uuid}`)
  },

  /**
   * 创建Portfolio
   */
  create(data: {
    name: string
    initial_cash: number
    risk_config?: Record<string, unknown>
  }): Promise<PortfolioDetail> {
    return request.post('/portfolio', data)
  },

  /**
   * 更新Portfolio
   */
  update(uuid: string, data: Partial<PortfolioDetail>): Promise<PortfolioDetail> {
    return request.put(`/portfolio/${uuid}`, data)
  },

  /**
   * 删除Portfolio
   */
  delete(uuid: string): Promise<void> {
    return request.delete(`/portfolio/${uuid}`)
  }
}
