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
