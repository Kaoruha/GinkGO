import request from '../request'
// 交易所/环境类型与 market.ts 单一来源(曾逐字重复两份,改一处漏一处)
import type { ExchangeType, EnvironmentType } from './market'
export type { ExchangeType, EnvironmentType }

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
  valid: boolean
  message: string
  account_info?: {
    balance?: string
    environment?: string
    exchange?: string
  }
  error_code?: string
}

// 分页响应(注意:这不是通用 PaginatedData)——后端 /accounts 的 data 是对象而非数组,
// request.ts 拦截器只重组"data 为数组 + meta.total"的端点,对象 data 原样直通,
// 故运行时形状就是 {accounts, total, ...},勿"统一"改成 items 字段(会与运行时不符)
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
  }): Promise<PaginationResponse<LiveAccount>> => {
    return request.get(
      '/api/v1/accounts',
      { params }
    )
  },

  /**
   * 获取账号详情
   */
  getAccount: (uuid: string): Promise<LiveAccount> => {
    return request.get(`/api/v1/accounts/${uuid}`)
  },

  /**
   * 创建账号
   */
  createAccount: (data: CreateLiveAccountRequest): Promise<{ account_uuid: string }> => {
    return request.post('/api/v1/accounts', data)
  },

  /**
   * 更新账号
   */
  updateAccount: (uuid: string, data: UpdateLiveAccountRequest): Promise<LiveAccount> => {
    return request.put(`/api/v1/accounts/${uuid}`, data)
  },

  /**
   * 删除账号
   */
  deleteAccount: (uuid: string): Promise<void> => {
    return request.delete(`/api/v1/accounts/${uuid}`)
  },

  /**
   * 验证账号
   */
  validateAccount: (uuid: string): Promise<ValidateAccountResponse> => {
    return request.post(`/api/v1/accounts/${uuid}/validate`)
  },

  /**
   * 更新账号状态
   */
  updateStatus: (uuid: string, status: AccountStatusType): Promise<LiveAccount> => {
    return request.put(`/api/v1/accounts/${uuid}/status`, { status })
  },

  /**
   * 获取账号余额
   */
  getBalance: (uuid: string): Promise<{
    total_equity: string
    available_balance: string
    frozen_balance: string
    currency_balances: Array<{
      currency: string
      available: string
      frozen: string
      balance: string
    }>
  }> => {
    return request.get(`/api/v1/accounts/${uuid}/balance`)
  },

  /**
   * 获取账号持仓
   */
  getPositions: (uuid: string): Promise<{
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
  }> => {
    return request.get(`/api/v1/accounts/${uuid}/positions`)
  },

  /**
   * 获取完整账户信息（余额 + 持仓）
   */
  getAccountInfo: (uuid: string): Promise<[{
    total_equity: string
    available_balance: string
    frozen_balance: string
    currency_balances: Array<{
      currency: string
      available: string
      frozen: string
      balance: string
    }>
  }, {
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
  }]> => {
    return Promise.all([
      request.get(`/api/v1/accounts/${uuid}/balance`),
      request.get(`/api/v1/accounts/${uuid}/positions`)
    ]) as unknown as Promise<[{
      total_equity: string
      available_balance: string
      frozen_balance: string
      currency_balances: Array<{
        currency: string
        available: string
        frozen: string
        balance: string
      }>
    }, {
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
    }]>
  },
}

export default liveAccountApi
