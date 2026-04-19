import request from '../request'
import type { APIResponse } from '@/types/api'

// 权限类型
export type PermissionType = 'read' | 'trade' | 'admin'

// API Key 状态
export type ApiKeyStatus = 'active' | 'inactive' | 'expired'

// API Key
export interface ApiKey {
  uuid: string
  name: string
  key_prefix: string
  permissions: string
  permissions_list: PermissionType[]
  is_active: boolean
  is_expired: boolean
  expires_at: string | null
  last_used_at: string | null
  description: string | null
  created_at: string
  user_id: string | null
}

// 创建 API Key 请求
export interface CreateApiKeyRequest {
  name: string
  permissions: PermissionType[]
  description?: string
  expires_days?: number
  auto_generate: boolean
}

// 创建 API Key 响应
export interface CreateApiKeyResponse {
  uuid: string
  name: string
  key_value: string  // 仅在创建时返回一次
  key_prefix: string
  permissions: string
  expires_at: string | null
  is_active: boolean
  user_id: string | null
}

// 更新 API Key 请求
export interface UpdateApiKeyRequest {
  name?: string
  permissions?: PermissionType[]
  is_active?: boolean
  description?: string
  expires_days?: number
}

// 验证 API Key 响应
export interface VerifyApiKeyResponse {
  uuid: string
  name: string
  key_prefix: string
  permissions: string
  user_id: string | null
}

/**
 * API Key API
 */
export const apiKeyApi = {
  /**
   * 获取 API Key 列表
   */
  listApiKeys: (params?: {
    user_id?: string
  }) => {
    return request.get<APIResponse<ApiKey[]>>(`/api/v1/api-keys/`, { params })
  },

  /**
   * 创建 API Key
   */
  createApiKey: (data: CreateApiKeyRequest) => {
    return request.post<APIResponse<CreateApiKeyResponse>>(
      `/api/v1/api-keys/`,
      data
    )
  },

  /**
   * 获取 API Key 详情
   */
  getApiKey: (uuid: string) => {
    return request.get<APIResponse<ApiKey>>(`/api/v1/api-keys/${uuid}`)
  },

  /**
   * 更新 API Key
   */
  updateApiKey: (uuid: string, data: UpdateApiKeyRequest) => {
    return request.put<APIResponse<{ uuid: string }>>(`/api/v1/api-keys/${uuid}`, data)
  },

  /**
   * 删除 API Key
   */
  deleteApiKey: (uuid: string) => {
    return request.delete<APIResponse<{ uuid: string }>>(`/api/v1/api-keys/${uuid}`)
  },

  /**
   * 获取完整 API Key（用于复制）
   */
  revealApiKey: (uuid: string) => {
    return request.post<APIResponse<{ uuid: string; name: string; key_value: string }>>(
      `/api/v1/api-keys/${uuid}/reveal`
    )
  },

  /**
   * 验证 API Key
   */
  verifyApiKey: (apiKey: string, requiredPermission?: string) => {
    return request.post<APIResponse<VerifyApiKeyResponse | null>>(
      `/api/v1/api-keys/verify?required_permission=${requiredPermission || ''}`,
      {},
      {
        headers: {
          'X-API-Key': apiKey
        }
      }
    )
  },

  /**
   * 检查权限
   */
  checkPermission: (apiKey: string, permission: string) => {
    return request.post<APIResponse<{ has_permission: boolean; permission: string }>>(
      `/api/v1/api-keys/check-permission?permission=${permission}`,
      {},
      {
        headers: {
          'X-API-Key': apiKey
        }
      }
    )
  }
}
