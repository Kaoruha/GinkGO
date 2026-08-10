import request from '../request'

export interface BacktestTask {
  uuid: string
  task_id: string
  name: string
  engine_id: string
  portfolio_id: string
  status: 'created' | 'pending' | 'running' | 'completed' | 'failed' | 'stopped'
  start_time: string | null
  end_time?: string
  duration_seconds?: number
  error_message?: string
  progress?: number
  current_stage?: string
  total_orders: number
  total_signals: number
  total_positions: number
  total_events: number
  final_portfolio_value: number
  total_pnl: number
  max_drawdown: number
  sharpe_ratio: number
  annual_return: number
  win_rate: number
  config_snapshot?: string
  backtest_start_date?: string
  backtest_end_date?: string
  created_at: string
  update_at: string
  updated_at?: string
}

export interface BacktestCreateRequest {
  name: string
  engine_uuid?: string
  portfolio_uuids: string[]
  engine_config: {
    start_date: string
    end_date: string
    broker_type?: string
    initial_cash?: number
    commission_rate?: number
    slippage_rate?: number
    broker_attitude?: number
    commission_min?: number
    analyzers?: any[]
  }
  component_config?: Record<string, any>
}

export interface BacktestStartRequest {
  portfolio_uuid?: string
  name?: string
  start_date?: string
  end_date?: string
  initial_cash?: number
  analyzers?: string[]
}

export interface BacktestListParams {
  engine_id?: string
  portfolio_id?: string
  status?: string
  keyword?: string
  page?: number
  size?: number
}

export interface NetValueData {
  time: string
  value: number
}

export interface BacktestNetValue {
  strategy: NetValueData[]
  benchmark: NetValueData[]
}

export interface BacktestListResponse {
  data: BacktestTask[]
  total: number
  page: number
  size: number
  meta?: {
    total: number
    page: number
    size: number
  }
}

export interface AnalyzerInfo {
  name: string
  latest_value: number | null
  record_count: number
  stats: {
    analyzer_name: string
    count: number
    min: number
    max: number
    avg: number
    latest: number | null
    first: number | null
    change: number
  } | null
}

export interface BacktestAnalyzersResponse {
  task_id: string
  portfolio_id: string
  analyzers: AnalyzerInfo[]
  total_count: number
}

export interface AnalyzerTimeseriesResponse {
  analyzer_name: string
  data: Array<{ time: string; value: number | null }>
  stats: {
    analyzer_name: string
    count: number
    min: number
    max: number
    avg: number
    latest: number | null
    first: number | null
    change: number
  } | null
  count: number
}

export interface SignalRecord {
  uuid: string
  code: string
  direction: string
  reason: string
  volume: number
  weight: number
  strength: number
  confidence: number
  portfolio_id: string
  timestamp: string | null
  business_timestamp: string | null
}

export interface OrderRecord {
  uuid: string
  code: string
  direction: string
  order_type: string
  status: string
  volume: number
  limit_price: number
  transaction_price: number
  transaction_volume: number
  fee: number
  timestamp: string | null
}

export interface PositionRecord {
  uuid: string
  code: string
  volume: number
  cost: number
  market_value: number
  profit: number
  profit_pct: number
  timestamp: string | null
}

export const backtestApi = {
  /**
   * 获取回测任务列表
   */
  list(params?: BacktestListParams): Promise<BacktestListResponse> {
    return request.get('/api/v1/backtests/', { params })
  },

  /**
   * 获取单个回测任务
   */
  get(uuid: string): Promise<BacktestTask> {
    return request.get(`/api/v1/backtests/${uuid}`)
  },

  /**
   * 创建回测任务
   */
  create(data: BacktestCreateRequest): Promise<BacktestTask> {
    return request.post('/api/v1/backtests/', data)
  },

  /**
   * 删除回测任务
   */
  delete(uuid: string): Promise<void> {
    return request.delete(`/api/v1/backtests/${uuid}`)
  },

  /**
   * 获取回测净值数据
   */
  getNetValue(uuid: string): Promise<BacktestNetValue> {
    return request.get(`/api/v1/backtests/${uuid}/netvalue`)
  },

  /**
   * 对比多个回测
   */
  compare(ids: string[]): Promise<{ data: Record<string, any> }> {
    return request.get('/api/v1/backtests/compare', { params: { ids: ids.join(',') } })
  },

  /**
   * 获取回测任务的分析器列表
   */
  getAnalyzers(uuid: string): Promise<BacktestAnalyzersResponse> {
    return request.get(`/api/v1/backtests/${uuid}/analyzers`)
  },

  /**
   * 启动回测任务
   */
  start(uuid: string, data?: BacktestStartRequest): Promise<{ task_id: string }> {
    return request.post(`/api/v1/backtests/${uuid}/start`, data || {})
  },

  /**
   * 停止回测任务
   */
  stop(uuid: string): Promise<{ task_id: string }> {
    return request.post(`/api/v1/backtests/${uuid}/stop`)
  },

  /**
   * 取消回测任务
   */
  cancel(uuid: string): Promise<{ task_id: string }> {
    return request.post(`/api/v1/backtests/${uuid}/cancel`)
  },

  /**
   * 获取分析器时序数据
   */
  getAnalyzerData(uuid: string, analyzerName: string): Promise<AnalyzerTimeseriesResponse> {
    return request.get(`/api/v1/backtests/${uuid}/analyzer/${analyzerName}`)
  },

  /**
   * 获取回测信号记录
   */
  getSignals(uuid: string, page: number = 1, size: number = 100): Promise<{ data: SignalRecord[]; total: number; page: number; size: number }> {
    return request.get(`/api/v1/backtests/${uuid}/signals`, { params: { page, size } })
  },

  /**
   * 获取回测订单记录
   */
  getOrders(uuid: string): Promise<{ data: OrderRecord[]; total: number }> {
    return request.get(`/api/v1/backtests/${uuid}/orders`)
  },

  /**
   * 获取回测持仓记录
   */
  getPositions(uuid: string): Promise<{ data: PositionRecord[]; total: number }> {
    return request.get(`/api/v1/backtests/${uuid}/positions`)
  },

  /**
   * 获取回测日志
   */
  getLogs(uuid: string, params?: { level?: string; event_type?: string; start_time?: string; end_time?: string; limit?: number; offset?: number }): Promise<{ data: { logs: any[]; total: number; limit: number; offset: number } }> {
    return request.get(`/api/v1/backtests/${uuid}/logs`, { params })
  },

}

