import request from '../request'
<<<<<<< HEAD
import type { APIResponse, PaginatedResponse } from '@/types/api'
import type { RequestOptions } from '@/types/api-request'

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
=======

export interface BacktestTask {
  uuid: string
  run_id: string
  name: string
  engine_id: string
  portfolio_id: string
  status: 'created' | 'pending' | 'running' | 'completed' | 'failed' | 'stopped'
  start_time: string | null
  end_time?: string
  duration_seconds?: number
  error_message?: string
  progress?: string
  current_stage?: string
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
  name?: string
  engine_id?: string
  portfolio_id?: string
  start_date?: string
  end_date?: string
  config_snapshot?: Record<string, any>
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
  run_id: string
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
>>>>>>> 011-quant-research
}

export const backtestApi = {
  /**
   * 获取回测任务列表
<<<<<<< HEAD
   * @param params 查询参数
   * @param options 请求选项（支持 signal 取消请求）
   */
  list(params?: { state?: string; page?: number; page_size?: number }, options?: RequestOptions): Promise<PaginatedResponse<BacktestTask>> {
    return request.get('/v1/backtests/', { params, signal: options?.signal })
  },

  /**
   * 获取回测任务详情
   * @param uuid 回测任务 UUID
   * @param options 请求选项（支持 signal 取消请求）
   */
  get(uuid: string, options?: RequestOptions): Promise<APIResponse<BacktestTaskDetail>> {
    return request.get(`/v1/backtests/${uuid}`, { signal: options?.signal })
=======
   */
  list(params?: BacktestListParams): Promise<BacktestListResponse> {
    return request.get('/v1/backtest', { params })
  },

  /**
   * 获取单个回测任务
   */
  get(uuid: string): Promise<BacktestTask> {
    return request.get(`/v1/backtest/${uuid}`)
>>>>>>> 011-quant-research
  },

  /**
   * 创建回测任务
<<<<<<< HEAD
   * @param data 回测配置
   * @param options 请求选项（支持 signal 取消请求）
   */
  create(data: BacktestCreate, options?: RequestOptions): Promise<APIResponse<BacktestTaskDetail>> {
    return request.post('/v1/backtests/', data, { signal: options?.signal })
  },

  /**
   * 启动回测任务
   * @param uuid 回测任务 UUID
   * @param options 请求选项（支持 signal 取消请求）
   */
  start(uuid: string, options?: RequestOptions): Promise<APIResponse<{ uuid: string; state: string }>> {
    return request.post(`/v1/backtests/${uuid}/start`, {}, { signal: options?.signal })
  },

  /**
   * 停止回测任务
   * @param uuid 回测任务 UUID
   * @param options 请求选项（支持 signal 取消请求）
   */
  stop(uuid: string, options?: RequestOptions): Promise<APIResponse<{ uuid: string; state: string }>> {
    return request.post(`/v1/backtests/${uuid}/stop`, {}, { signal: options?.signal })
=======
   */
  create(data: BacktestCreateRequest): Promise<BacktestTask> {
    return request.post('/v1/backtest', data)
>>>>>>> 011-quant-research
  },

  /**
   * 删除回测任务
<<<<<<< HEAD
   * @param uuid 回测任务 UUID
   * @param options 请求选项（支持 signal 取消请求）
   */
  delete(uuid: string, options?: RequestOptions): Promise<void> {
    return request.delete(`/v1/backtests/${uuid}`, { signal: options?.signal })
  },

  /**
   * 获取可用的 Engine 列表（用于预填充配置）
   * @param params 查询参数
   * @param options 请求选项（支持 signal 取消请求）
   */
  getEngines(params?: { is_live?: boolean }, options?: RequestOptions): Promise<APIResponse<Engine[]>> {
    return request.get('/v1/backtests/engines', { params: { is_live: false, ...params }, signal: options?.signal })
  },

  /**
   * 获取可用的分析器类型列表
   * @param options 请求选项（支持 signal 取消请求）
   */
  getAnalyzers(options?: RequestOptions): Promise<APIResponse<AnalyzerTypeInfo[]>> {
    return request.get('/v1/backtests/analyzers', { signal: options?.signal })
  },

  /**
   * 创建 SSE 连接监听回测进度
   * @param uuid 回测任务 UUID
   * @param onProgress 进度回调函数
   * @param onComplete 完成回调函数
   * @param onError 错误回调函数
   * @returns EventSource 实例，用于关闭连接
   */
  subscribeProgress(
    uuid: string,
    onProgress: (data: BacktestProgress) => void,
    onComplete?: (data: BacktestProgress) => void,
    onError?: (error: string) => void
  ): EventSource {
    const eventSource = new EventSource(`/api/v1/backtests/${uuid}/events`)

    // 监听普通消息事件
    eventSource.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data) as BacktestProgress
        onProgress(data)
      } catch (error) {
        console.error('Failed to parse SSE data:', error)
      }
    }

    // 监听完成事件
    if (onComplete) {
      eventSource.addEventListener('complete', (event) => {
        try {
          const data = JSON.parse((event as MessageEvent).data) as BacktestProgress
          onComplete(data)
        } catch (error) {
          console.error('Failed to parse complete event:', error)
        }
      })
    }

    // 监听错误事件
    if (onError) {
      eventSource.addEventListener('error', (event) => {
        try {
          const data = JSON.parse((event as MessageEvent).data) as BacktestProgress
          onError(data.error || 'Unknown error')
        } catch (error) {
          onError('Connection error')
        }
      })
    }

    // 监听连接错误
    eventSource.onerror = (error) => {
      console.error('SSE connection error:', error)
      onError?.('Connection lost')
    }

    return eventSource
  }
}

/**
 * 回测进度数据（来自 SSE）
 */
export interface BacktestProgress {
  progress: number
  state?: string
  current_date?: string
  result?: Record<string, any>
  error?: string
  updated_at: string
}

// ========== 新增：回测报告、对比、模板相关 ==========

/**
 * 回测报告详情
 */
export interface BacktestReport {
  task_uuid: string
  task_name: string
  // 基础指标
  metrics: {
    total_return: number
    annual_return: number
    sharpe_ratio: number
    sortino_ratio: number
    max_drawdown: number
    win_rate: number
    profit_loss_ratio: number
    volatility: number
  }
  // 净值曲线数据
  net_value: Array<{
    date: string
    value: number
  }>
  // 回撤数据
  drawdown: Array<{
    date: string
    value: number
  }>
  // 持仓变化
  positions: Array<{
    date: string
    positions: Array<{
      code: string
      weight: number
    }>
  }>
  // 交易记录
  trades: Array<{
    uuid: string
    code: string
    direction: 'LONG' | 'SHORT'
    volume: number
    price: number
    timestamp: string
    profit?: number
  }>
}

/**
 * 回测对比数据
 */
export interface BacktestComparison {
  task_uuid: string
  task_name: string
  metrics: BacktestReport['metrics']
  net_value: Array<{ date: string; value: number }>
}

/**
 * 回测对比结果
 */
export interface ComparisonResult {
  tasks: BacktestComparison[]
  comparison_table: Array<{
    metric: string
    values: Record<string, number>  // { task_uuid1: value1, task_uuid2: value2 }
    best_task_uuid?: string
  }>
}

/**
 * 回测模板
 */
export interface BacktestTemplate {
  uuid: string
  name: string
  description?: string
  config: BacktestCreate
  created_at: string
  updated_at: string
}

// 扩展 backtestApi
export const backtestApiExtended = {
  ...backtestApi,

  /**
   * 获取回测报告
   */
  getReport(uuid: string, options?: RequestOptions): Promise<APIResponse<BacktestReport>> {
    return request.get(`/v1/backtests/${uuid}/report`, { signal: options?.signal })
  },

  /**
   * 回测对比
   */
  compare(taskUuids: string[], options?: RequestOptions): Promise<APIResponse<ComparisonResult>> {
    return request.post('/v1/backtests/compare', { task_uuids: taskUuids }, { signal: options?.signal })
  },

  /**
   * 获取回测日志流（SSE）
   */
  subscribeLogs(uuid: string, onMessage: (message: string) => void): EventSource {
    const eventSource = new EventSource(`/api/v1/backtests/${uuid}/logs`)
    eventSource.onmessage = (event) => {
      onMessage(event.data)
    }
    return eventSource
  },

  /**
   * 获取模板列表
   */
  listTemplates(options?: RequestOptions): Promise<APIResponse<BacktestTemplate[]>> {
    return request.get('/v1/backtests/templates', { signal: options?.signal })
  },

  /**
   * 获取模板详情
   */
  getTemplate(uuid: string, options?: RequestOptions): Promise<APIResponse<BacktestTemplate>> {
    return request.get(`/v1/backtests/templates/${uuid}`, { signal: options?.signal })
  },

  /**
   * 创建模板
   */
  createTemplate(data: { name: string; description?: string; config: BacktestCreate }, options?: RequestOptions): Promise<APIResponse<BacktestTemplate>> {
    return request.post('/v1/backtests/templates', data, { signal: options?.signal })
  },

  /**
   * 更新模板
   */
  updateTemplate(uuid: string, data: Partial<BacktestTemplate>, options?: RequestOptions): Promise<APIResponse<BacktestTemplate>> {
    return request.put(`/v1/backtests/templates/${uuid}`, data, { signal: options?.signal })
  },

  /**
   * 删除模板
   */
  deleteTemplate(uuid: string, options?: RequestOptions): Promise<void> {
    return request.delete(`/v1/backtests/templates/${uuid}`, { signal: options?.signal })
  },

  /**
   * 从模板创建回测
   */
  createFromTemplate(templateUuid: string, name: string, options?: RequestOptions): Promise<APIResponse<BacktestTaskDetail>> {
    return request.post('/v1/backtests/templates/{templateUuid}/create', { name }, { signal: options?.signal })
  }
=======
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

  /**
   * 启动回测任务
   */
  start(uuid: string, data?: BacktestStartRequest): Promise<{ success: boolean; run_id: string; message: string }> {
    return request.post(`/v1/backtest/${uuid}/start`, data || {})
  },

  /**
   * 停止回测任务
   */
  stop(uuid: string): Promise<{ success: boolean; run_id: string; message: string }> {
    return request.post(`/v1/backtest/${uuid}/stop`)
  },

  /**
   * 获取分析器时序数据
   */
  getAnalyzerData(uuid: string, analyzerName: string): Promise<AnalyzerTimeseriesResponse> {
    return request.get(`/v1/backtest/${uuid}/analyzer/${analyzerName}`)
  },

  /**
   * 获取回测信号记录
   */
  getSignals(uuid: string, page: number = 0, size: number = 100): Promise<{ data: SignalRecord[]; total: number; page: number; size: number }> {
    return request.get(`/v1/backtest/${uuid}/signals`, { params: { page, size } })
  },

  /**
   * 获取回测订单记录
   */
  getOrders(uuid: string): Promise<{ data: OrderRecord[]; total: number }> {
    return request.get(`/v1/backtest/${uuid}/orders`)
  },

  /**
   * 获取回测持仓记录
   */
  getPositions(uuid: string): Promise<{ data: PositionRecord[]; total: number }> {
    return request.get(`/v1/backtest/${uuid}/positions`)
  },
>>>>>>> 011-quant-research
}
