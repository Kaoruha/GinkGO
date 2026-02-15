import request from '../request'
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
}

export const backtestApi = {
  /**
   * 获取回测任务列表
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
  },

  /**
   * 创建回测任务
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
  },

  /**
   * 删除回测任务
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
}
