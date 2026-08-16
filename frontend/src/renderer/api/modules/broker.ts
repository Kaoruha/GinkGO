import request from '../request'

/** Broker 实例状态 */
export type BrokerState = 'uninitialized' | 'initializing' | 'running' | 'paused' | 'stopped' | 'error' | 'recovering'

/** Broker 实例 */
export interface BrokerInstance {
  uuid: string
  portfolio_id: string
  live_account_id: string
  state: BrokerState
  process_id: number | null
  heartbeat_at: string | null
  error_message: string | null
  error_count: number
  total_submitted: number
  total_filled: number
  total_cancelled: number
  total_rejected: number
  last_order_at: string | null
  live_account?: {
    uuid: string
    name: string
    exchange: string
    environment: string
  }
}

/**
 * Broker 管理 API
 */
export const brokerApi = {
  /** 获取 Broker 实例列表 */
  list: (): Promise<BrokerInstance[]> =>
    request.get('/api/v1/accounts/brokers'),

  /** 启动 Broker */
  start: (uuid: string): Promise<void> =>
    request.post(`/api/v1/accounts/brokers/${uuid}/start`),

  /** 暂停 Broker */
  pause: (uuid: string): Promise<void> =>
    request.post(`/api/v1/accounts/brokers/${uuid}/pause`),

  /** 恢复 Broker */
  resume: (uuid: string): Promise<void> =>
    request.post(`/api/v1/accounts/brokers/${uuid}/resume`),

  /** 停止 Broker */
  stop: (uuid: string): Promise<void> =>
    request.post(`/api/v1/accounts/brokers/${uuid}/stop`),

  /** 紧急停止全部 */
  emergencyStop: (): Promise<void> =>
    request.post('/api/v1/accounts/brokers/emergency-stop'),
}

export default brokerApi
