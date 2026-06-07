import request from '../request'
import type { APIResponse } from '@/types/api'

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

/** Broker 状态映射 */
export const BROKER_STATE_LABELS: Record<BrokerState, { label: string; color: 'success' | 'info' | 'warning' | 'default' | 'destructive' | 'outline' | 'secondary' }> = {
  uninitialized: { label: '未初始化', color: 'secondary' },
  initializing: { label: '初始化中', color: 'warning' },
  running: { label: '运行中', color: 'success' },
  paused: { label: '已暂停', color: 'warning' },
  stopped: { label: '已停止', color: 'secondary' },
  error: { label: '错误', color: 'destructive' },
  recovering: { label: '恢复中', color: 'warning' },
}

/**
 * Broker 管理 API
 */
export const brokerApi = {
  /** 获取 Broker 实例列表 */
  list: () =>
    request.get<APIResponse<BrokerInstance[]>>('/api/v1/accounts/brokers'),

  /** 启动 Broker */
  start: (uuid: string) =>
    request.post<APIResponse<void>>(`/api/v1/accounts/brokers/${uuid}/start`),

  /** 暂停 Broker */
  pause: (uuid: string) =>
    request.post<APIResponse<void>>(`/api/v1/accounts/brokers/${uuid}/pause`),

  /** 恢复 Broker */
  resume: (uuid: string) =>
    request.post<APIResponse<void>>(`/api/v1/accounts/brokers/${uuid}/resume`),

  /** 停止 Broker */
  stop: (uuid: string) =>
    request.post<APIResponse<void>>(`/api/v1/accounts/brokers/${uuid}/stop`),

  /** 紧急停止全部 */
  emergencyStop: () =>
    request.post<APIResponse<void>>('/api/v1/accounts/brokers/emergency-stop'),
}

export default brokerApi
