import request from '../request'

// 分析器配置
export interface AnalyzerConfig {
  name: string
  type: string
  config?: Record<string, unknown>
}

export interface BacktestTask {
  uuid: string
  name: string
  portfolio_name: string
  state: 'PENDING' | 'RUNNING' | 'COMPLETED' | 'FAILED' | 'CANCELLED'
  progress: number
  created_at: string
  started_at?: string
  completed_at?: string
}

export interface BacktestTaskDetail extends BacktestTask {
  portfolio_uuid: string
  engine_uuid?: string | null
  config: BacktestConfig
  result?: {
    total_return: number
    annual_return: number
    sharpe_ratio: number
    max_drawdown: number
    win_rate: number
    [key: string]: any
  }
  worker_id?: string | null
  error?: string | null
}

/**
 * Engine 配置 - 对应 Engine 装配逻辑
 */
export interface EngineConfig {
  start_date: string
  end_date: string
  broker_type: 'backtest' | 'okx'  // Broker 类型
  initial_cash?: number  // 初始资金覆盖（可选，留空使用 Portfolio 自身资金）
  commission_rate: number
  slippage_rate: number
  broker_attitude: number
  commission_min?: number  // 最小手续费（某些 Broker 需要）
  // 分析器配置（Engine 级别）
  analyzers?: AnalyzerConfig[]  // 分析器列表
  // 来自 Engine 的基础信息
  engine_uuid?: string
  engine_name?: string
}

/**
 * 组件配置 - 对应 Portfolio 组件
 */
export interface ComponentConfig {
  max_position_ratio?: number
  stop_loss_ratio?: number
  take_profit_ratio?: number
  benchmark_return?: number
  frequency?: string
}

/**
 * 创建回测任务 - 按照 Engine 装配逻辑
 */
export interface BacktestCreate {
  name: string
  // 可选：选择现有 Engine 预填充配置
  engine_uuid?: string
  // Portfolio 选择（支持多个）
  portfolio_uuids: string[]
  // Engine 配置
  engine_config: EngineConfig
  // 组件配置（可选）
  component_config?: ComponentConfig
}

/**
 * Engine 信息（用于预填充配置）
 */
export interface Engine {
  uuid: string
  name: string
  is_live: boolean
  backtest_start_date?: string
  backtest_end_date?: string
  broker_attitude: number
  created_at: string
}

/**
 * 分析器类型信息
 */
export interface AnalyzerTypeInfo {
  type: string
  name: string
  description: string
  default_config: Record<string, unknown>
}

export const backtestApi = {
  /**
   * 获取回测任务列表
   */
  list(params?: { state?: string }): Promise<BacktestTask[]> {
    return request.get('/backtest', { params })
  },

  /**
   * 获取回测任务详情
   */
  get(uuid: string): Promise<BacktestTaskDetail> {
    return request.get(`/backtest/${uuid}`)
  },

  /**
   * 创建回测任务
   */
  create(data: BacktestCreate): Promise<BacktestTaskDetail> {
    return request.post('/backtest', data)
  },

  /**
   * 启动回测任务
   */
  start(uuid: string): Promise<{ message: string }> {
    return request.post(`/backtest/${uuid}/start`)
  },

  /**
   * 停止回测任务
   */
  stop(uuid: string): Promise<{ message: string }> {
    return request.post(`/backtest/${uuid}/stop`)
  },

  /**
   * 删除回测任务
   */
  delete(uuid: string): Promise<void> {
    return request.delete(`/backtest/${uuid}`)
  },

  /**
   * 获取可用的 Engine 列表（用于预填充配置）
   */
  getEngines(params?: { is_live?: boolean }): Promise<Engine[]> {
    return request.get('/backtest/engines', { params: { is_live: false, ...params } })
  },

  /**
   * 获取可用的分析器类型列表
   */
  getAnalyzers(): Promise<AnalyzerTypeInfo[]> {
    return request.get('/backtest/analyzers')
  }
}
