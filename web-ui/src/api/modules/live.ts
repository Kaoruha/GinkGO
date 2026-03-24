import request from '../request'
import type { APIResponse } from '@/types/api'

// 交易所类型
export type ExchangeType = 'okx' | 'binance'

// 环境类型
export type EnvironmentType = 'testnet' | 'production'

// 账号状态
export type AccountStatusType = 'disabled' | 'enabled' | 'connecting' | 'disconnected' | 'error'

// 实盘账号
export interface LiveAccount {
  uuid: string
  user_id: string
  exchange: ExchangeType
  environment: EnvironmentType
  name: string
  description?: string
  status: AccountStatusType
  validation_status?: string
  last_validated_at?: string
  created_at: string
  updated_at: string
  // 注意：敏感字段（api_key, api_secret, passphrase）不会在前端返回
}

// 创建账号请求
export interface CreateLiveAccountRequest {
  exchange: ExchangeType
  name: string
  api_key: string
  api_secret: string
  passphrase?: string
  environment: EnvironmentType
  description?: string
}

// 更新账号请求
export interface UpdateLiveAccountRequest {
  name?: string
  api_key?: string
  api_secret?: string
  passphrase?: string
  description?: string
}

// 验证响应
export interface ValidateAccountResponse {
  success: boolean
  valid: boolean
  message: string
  account_info?: {
    balance?: string
    environment?: string
    exchange?: string
  }
  error_code?: string
}

// 分页响应
export interface PaginationResponse<T> {
  accounts: T[]
  total: number
  page: number
  page_size: number
  total_pages: number
}

/**
 * 实盘账号 API
 */
export const liveAccountApi = {
  /**
   * 获取账号列表
   */
  getAccounts: (params?: {
    page?: number
    page_size?: number
    exchange?: ExchangeType
    environment?: EnvironmentType
    status?: AccountStatusType
  }) => {
    return request.get<APIResponse<PaginationResponse<LiveAccount>>>(
      '/api/v1/accounts',
      { params }
    )
  },

  /**
   * 获取账号详情
   */
  getAccount: (uuid: string) => {
    return request.get<APIResponse<LiveAccount>>(`/api/v1/accounts/${uuid}`)
  },

  /**
   * 创建账号
   */
  createAccount: (data: CreateLiveAccountRequest) => {
    return request.post<APIResponse<{ account_uuid: string }>>('/api/v1/accounts', data)
  },

  /**
   * 更新账号
   */
  updateAccount: (uuid: string, data: UpdateLiveAccountRequest) => {
    return request.put<APIResponse<LiveAccount>>(`/api/v1/accounts/${uuid}`, data)
  },

  /**
   * 删除账号
   */
  deleteAccount: (uuid: string) => {
    return request.delete<APIResponse<void>>(`/api/v1/accounts/${uuid}`)
  },

  /**
   * 验证账号
   */
  validateAccount: (uuid: string) => {
    return request.post<APIResponse<ValidateAccountResponse>>(`/api/v1/accounts/${uuid}/validate`)
  },

  /**
   * 更新账号状态
   */
  updateStatus: (uuid: string, status: AccountStatusType) => {
    return request.put<APIResponse<LiveAccount>>(`/api/v1/accounts/${uuid}/status`, { status })
  },

  /**
   * 获取账号余额
   */
  getBalance: (uuid: string) => {
    return request.get<APIResponse<{
      total_equity: string
      available_balance: string
      frozen_balance: string
      currency_balances: Array<{
        currency: string
        available: string
        frozen: string
        balance: string
      }>
    }>>(`/api/v1/accounts/${uuid}/balance`)
  },

  /**
   * 获取账号持仓
   */
  getPositions: (uuid: string) => {
    return request.get<APIResponse<{
      positions: Array<{
        symbol: string
        side: 'long' | 'short'
        size: string
        avg_price: string
        current_price: string
        unrealized_pnl: string
        unrealized_pnl_percentage: string
        margin: string
      }>
    }>>(`/api/v1/accounts/${uuid}/positions`)
  },

  /**
   * 获取完整账户信息（余额 + 持仓）
   */
  getAccountInfo: (uuid: string) => {
    return Promise.all([
      request.get<APIResponse<{
        total_equity: string
        available_balance: string
        frozen_balance: string
        currency_balances: Array<{
          currency: string
          available: string
          frozen: string
          balance: string
        }>
      }>>(`/api/v1/accounts/${uuid}/balance`),
      request.get<APIResponse<{
        positions: Array<{
          symbol: string
          side: 'long' | 'short'
          size: string
          avg_price: string
          current_price: string
          unrealized_pnl: string
          unrealized_pnl_percentage: string
          margin: string
        }>
      }>>(`/api/v1/accounts/${uuid}/positions`)
    ])
  },
}

export default liveAccountApi
