import request from '../request'
import type { RequestOptions } from '@/types/api-request'

// ==================== 用户管理 ====================

export interface UserInfo {
  uuid: string
  username: string
  display_name: string
  email: string
  roles: string[]
  status: 'active' | 'disabled'
  created_at: string
}

export interface UserCreate {
  username: string
  password: string
  display_name: string
  email: string
  roles: string[]
  status?: 'active' | 'disabled'
}

export interface UserUpdate {
  display_name?: string
  email?: string
  roles?: string[]
  status?: 'active' | 'disabled'
}

export const usersApi = {
  /**
   * 获取用户列表
   * @param params 查询参数
   * @param options 请求选项（支持 signal 取消请求）
   */
  list(params?: { status?: string; search?: string }, options?: RequestOptions): Promise<UserInfo[]> {
    return request.get('/v1/settings/users', { params, signal: options?.signal })
  },

  /**
   * 创建用户
   * @param data 用户数据
   * @param options 请求选项（支持 signal 取消请求）
   */
  create(data: UserCreate, options?: RequestOptions): Promise<UserInfo> {
    return request.post('/v1/settings/users', data, { signal: options?.signal })
  },

  /**
   * 更新用户
   * @param uuid 用户 UUID
   * @param data 更新数据
   * @param options 请求选项（支持 signal 取消请求）
   */
  update(uuid: string, data: UserUpdate, options?: RequestOptions): Promise<{ message: string }> {
    return request.put(`/v1/settings/users/${uuid}`, data, { signal: options?.signal })
  },

  /**
   * 删除用户
   * @param uuid 用户 UUID
   * @param options 请求选项（支持 signal 取消请求）
   */
  delete(uuid: string, options?: RequestOptions): Promise<{ message: string }> {
    return request.delete(`/v1/settings/users/${uuid}`, { signal: options?.signal })
  },

  /**
   * 重置用户密码
   * @param uuid 用户 UUID
   * @param new_password 新密码
   * @param options 请求选项（支持 signal 取消请求）
   */
  resetPassword(uuid: string, new_password: string, options?: RequestOptions): Promise<{ message: string }> {
    return request.post(`/v1/settings/users/${uuid}/reset-password`, { new_password }, { signal: options?.signal })
  },

  /**
   * 获取用户联系方式列表
   * @param userUuid 用户 UUID
   * @param options 请求选项（支持 signal 取消请求）
   */
  listContacts(userUuid: string, options?: RequestOptions): Promise<UserContactInfo[]> {
    return request.get(`/v1/settings/users/${userUuid}/contacts`, { signal: options?.signal })
  },

  /**
   * 创建用户联系方式
   * @param userUuid 用户 UUID
   * @param data 联系方式数据
   * @param options 请求选项（支持 signal 取消请求）
   */
  createContact(userUuid: string, data: UserContactCreate, options?: RequestOptions): Promise<UserContactInfo> {
    return request.post(`/v1/settings/users/${userUuid}/contacts`, data, { signal: options?.signal })
  },

  /**
   * 更新用户联系方式
   * @param contactUuid 联系方式 UUID
   * @param data 更新数据
   * @param options 请求选项（支持 signal 取消请求）
   */
  updateContact(contactUuid: string, data: UserContactUpdate, options?: RequestOptions): Promise<{ message: string }> {
    return request.put(`/v1/settings/users/contacts/${contactUuid}`, data, { signal: options?.signal })
  },

  /**
   * 删除用户联系方式
   * @param contactUuid 联系方式 UUID
   * @param options 请求选项（支持 signal 取消请求）
   */
  deleteContact(contactUuid: string, options?: RequestOptions): Promise<{ message: string }> {
    return request.delete(`/v1/settings/users/contacts/${contactUuid}`, { signal: options?.signal })
  },

  /**
   * 测试用户联系方式
   * @param contactUuid 联系方式 UUID
   * @param data 测试数据
   * @param options 请求选项（支持 signal 取消请求）
   */
  testContact(contactUuid: string, data: { address: string; subject?: string; content?: string }, options?: RequestOptions): Promise<{ message: string; detail?: string }> {
    return request.post(`/v1/settings/users/contacts/${contactUuid}/test`, data, { signal: options?.signal })
  },

  /**
   * 设置为主联系方式
   * @param contactUuid 联系方式 UUID
   * @param options 请求选项（支持 signal 取消请求）
   */
  setPrimaryContact(contactUuid: string, options?: RequestOptions): Promise<{ message: string }> {
    return request.post(`/v1/settings/users/contacts/${contactUuid}/set-primary`, {}, { signal: options?.signal })
  }
}

// ==================== 用户组管理 ====================

// ==================== 用户联系方式 ====================

export interface UserContactInfo {
  uuid: string
  user_id: string
  contact_type: 'email' | 'webhook'
  address: string
  is_primary: boolean
  is_active: boolean
  created_at: string
}

export interface UserContactCreate {
  contact_type: 'email' | 'webhook'
  address: string
  is_primary?: boolean
}

export interface UserContactUpdate {
  contact_type?: 'email' | 'webhook'
  address?: string
  is_primary?: boolean
  is_active?: boolean
}

export interface UserGroupInfo {
  uuid: string
  name: string
  description?: string
  user_count: number
  permissions: string[]
}

export interface UserGroupCreate {
  name: string
  description?: string
  permissions: string[]
}

export interface GroupMember {
  uuid: string
  user_uuid: string
  username: string
  display_name: string
  email: string
}

export const userGroupsApi = {
  /**
   * 获取用户组列表
   */
  list(): Promise<UserGroupInfo[]> {
    return request.get('/v1/settings/user-groups')
  },

  /**
   * 创建用户组
   */
  create(data: UserGroupCreate): Promise<UserGroupInfo> {
    return request.post('/v1/settings/user-groups', data)
  },

  /**
   * 更新用户组
   */
  update(uuid: string, data: Partial<UserGroupCreate>): Promise<{ message: string }> {
    return request.put(`/v1/settings/user-groups/${uuid}`, data)
  },

  /**
   * 删除用户组
   */
  delete(uuid: string): Promise<{ message: string }> {
    return request.delete(`/v1/settings/user-groups/${uuid}`)
  },

  /**
   * 获取用户组成员列表
   */
  listMembers(groupUuid: string): Promise<GroupMember[]> {
    return request.get(`/v1/settings/user-groups/${groupUuid}/members`)
  },

  /**
   * 添加用户到用户组
   */
  addMember(groupUuid: string, userUuid: string): Promise<{ message: string; mapping_uuid: string }> {
    return request.post(`/v1/settings/user-groups/${groupUuid}/members`, { user_uuid: userUuid })
  },

  /**
   * 从用户组移除用户
   */
  removeMember(groupUuid: string, userUuid: string): Promise<{ message: string }> {
    return request.delete(`/v1/settings/user-groups/${groupUuid}/members/${userUuid}`)
  }
}

// ==================== 通知管理 ====================

export interface NotificationTemplate {
  uuid: string
  name: string
  type: 'email' | 'discord' | 'system'
  subject: string
  enabled: boolean
  updated_at: string
}

export interface NotificationHistory {
  uuid: string
  type: string
  subject: string
  recipient: string
  status: 'success' | 'failed'
  created_at: string
  error?: string
  content?: string
}

export interface NotificationUserInfo {
  uuid: string
  username: string
  display_name?: string
}

export interface NotificationUserGroupInfo {
  uuid: string
  name: string
}

export interface NotificationRecipient {
  uuid: string
  name: string
  recipient_type: 'USER' | 'USER_GROUP'
  user_id?: string
  user_group_id?: string
  user_info?: NotificationUserInfo
  user_group_info?: NotificationUserGroupInfo
  description?: string
  is_default: boolean
  created_at: string
}

export interface NotificationRecipientCreate {
  name: string
  recipient_type: 'USER' | 'USER_GROUP'
  user_id?: string
  user_group_id?: string
  is_default?: boolean
  description?: string
}

export interface NotificationRecipientUpdate {
  name?: string
  recipient_type?: 'USER' | 'USER_GROUP'
  user_id?: string
  user_group_id?: string
  is_default?: boolean
  description?: string
}

export const notificationsApi = {
  /**
   * 获取通知模板列表
   */
  listTemplates(): Promise<NotificationTemplate[]> {
    return request.get('/v1/settings/notifications/templates')
  },

  /**
   * 创建通知模板
   */
  createTemplate(data: Partial<NotificationTemplate>): Promise<NotificationTemplate> {
    return request.post('/v1/settings/notifications/templates', data)
  },

  /**
   * 更新通知模板
   */
  updateTemplate(uuid: string, data: Partial<NotificationTemplate>): Promise<{ message: string }> {
    return request.put(`/v1/settings/notifications/templates/${uuid}`, data)
  },

  /**
   * 删除通知模板
   */
  deleteTemplate(uuid: string): Promise<{ message: string }> {
    return request.delete(`/v1/settings/notifications/templates/${uuid}`)
  },

  /**
   * 切换模板启用状态
   */
  toggleTemplate(uuid: string, enabled: boolean): Promise<{ message: string }> {
    return request.patch(`/v1/settings/notifications/templates/${uuid}`, { enabled })
  },

  /**
   * 测试通知
   */
  testTemplate(uuid: string): Promise<{ message: string }> {
    return request.post(`/v1/settings/notifications/templates/${uuid}/test`)
  },

  /**
   * 获取通知历史
   */
  listHistory(params?: { type?: string; page?: number; page_size?: number }): Promise<NotificationHistory[]> {
    return request.get('/v1/settings/notifications/history', { params })
  },

  /**
   * 获取通知接收人列表
   */
  listRecipients(): Promise<NotificationRecipient[]> {
    return request.get('/v1/settings/notifications/recipients')
  },

  /**
   * 创建通知接收人
   */
  createRecipient(data: NotificationRecipientCreate): Promise<NotificationRecipient> {
    return request.post('/v1/settings/notifications/recipients', data)
  },

  /**
   * 更新通知接收人
   */
  updateRecipient(uuid: string, data: NotificationRecipientUpdate): Promise<{ message: string }> {
    return request.put(`/v1/settings/notifications/recipients/${uuid}`, data)
  },

  /**
   * 删除通知接收人
   */
  deleteRecipient(uuid: string): Promise<{ message: string }> {
    return request.delete(`/v1/settings/notifications/recipients/${uuid}`)
  },

  /**
   * 切换接收人启用状态
   */
  toggleRecipient(uuid: string): Promise<{ message: string; is_active: boolean }> {
    return request.patch(`/v1/settings/notifications/recipients/${uuid}/toggle`)
  },

  /**
   * 测试通知接收人 - 发送测试通知
   */
  testRecipient(uuid: string): Promise<{
    message: string
    details?: string[]
    recipient_name: string
    contact_count: number
    success_count: number
    failed_count: number
  }> {
    return request.post(`/v1/settings/notifications/recipients/${uuid}/test`)
  }
}

// ==================== API密钥管理 ====================

export interface APIKey {
  key_id: string
  name: string
  masked_key: string
  status: 'active' | 'disabled'
  expires_at?: string
  last_used?: string
}

export interface APIStats {
  today_calls: number
  month_calls: number
  success_rate: number
  avg_response_time: number
}

export const apiKeysApi = {
  /**
   * 获取API密钥列表
   */
  list(): Promise<APIKey[]> {
    return request.get('/v1/settings/api-keys')
  },

  /**
   * 创建API密钥
   */
  create(data: { name: string; expires_at?: string }): Promise<APIKey> {
    return request.post('/v1/settings/api-keys', data)
  },

  /**
   * 删除API密钥
   */
  delete(key_id: string): Promise<{ message: string }> {
    return request.delete(`/v1/settings/api-keys/${key_id}`)
  },

  /**
   * 获取API统计
   */
  getStats(): Promise<APIStats> {
    return request.get('/v1/settings/api-stats')
  }
}
