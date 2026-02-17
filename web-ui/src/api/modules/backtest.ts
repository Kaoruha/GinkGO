import request from '../request'

export interface BacktestTask {
  uuid: string
  task_id: string
  engine_id: string
  portfolio_id: string
  status: 'running' | 'completed' | 'failed' | 'stopped'
  start_time: string
  end_time?: string
  duration_seconds?: number
  error_message?: string
  total_orders: number
  total_signals: number
  total_positions: number
  total_events: number
  final_portfolio_value: string
  total_pnl: string
  max_drawdown: string
  sharpe_ratio: string
  annual_return: string
  win_rate: string
  config_snapshot?: string
  created_at: string
  update_at: string
}

export interface BacktestCreateRequest {
  task_id: string
  engine_id?: string
  portfolio_id?: string
  config_snapshot?: Record<string, any>
}

export interface BacktestListParams {
  engine_id?: string
  portfolio_id?: string
  status?: string
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

export const backtestApi = {
  /**
   * 获取回测任务列表
   */
  list(params?: BacktestListParams): Promise<BacktestListResponse> {
    return request.get('/v1/backtest', { params })
  },

  /**
   * 获取单个回测任务
   */
  get(uuid: string): Promise<BacktestTask> {
    return request.get(`/v1/backtest/${uuid}`)
  },

  /**
   * 创建回测任务
   */
  create(data: BacktestCreateRequest): Promise<BacktestTask> {
    return request.post('/v1/backtest', data)
  },

  /**
   * 删除回测任务
   */
  delete(uuid: string): Promise<{ success: boolean; message: string }> {
    return request.delete(`/v1/backtest/${uuid}`)
  },

  /**
   * 获取回测净值数据
   */
  getNetValue(uuid: string): Promise<BacktestNetValue> {
    return request.get(`/v1/backtest/${uuid}/netvalue`)
  },

  /**
   * 对比多个回测
   */
  compare(ids: string[]): Promise<{ data: Record<string, any> }> {
    return request.get('/v1/backtest/compare', { params: { ids: ids.join(',') } })
  },

  /**
   * 获取回测任务的分析器列表
   */
  getAnalyzers(uuid: string): Promise<BacktestAnalyzersResponse> {
    return request.get(`/v1/backtest/${uuid}/analyzers`)
  },
}
