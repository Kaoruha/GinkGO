import request from '../request'

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
   */
  list(params?: { status?: string; search?: string }): Promise<UserInfo[]> {
    return request.get('/settings/users', { params })
  },

  /**
   * 创建用户
   */
  create(data: UserCreate): Promise<UserInfo> {
    return request.post('/settings/users', data)
  },

  /**
   * 更新用户
   */
  update(uuid: string, data: UserUpdate): Promise<{ message: string }> {
    return request.put(`/settings/users/${uuid}`, data)
  },

  /**
   * 删除用户
   */
  delete(uuid: string): Promise<{ message: string }> {
    return request.delete(`/settings/users/${uuid}`)
  },

  /**
   * 重置用户密码
   */
  resetPassword(uuid: string, new_password: string): Promise<{ message: string }> {
    return request.post(`/settings/users/${uuid}/reset-password`, { new_password })
  },

  /**
   * 获取用户联系方式列表
   */
  listContacts(userUuid: string): Promise<UserContactInfo[]> {
    return request.get(`/settings/users/${userUuid}/contacts`)
  },

  /**
   * 创建用户联系方式
   */
  createContact(userUuid: string, data: UserContactCreate): Promise<UserContactInfo> {
    return request.post(`/settings/users/${userUuid}/contacts`, data)
  },

  /**
   * 更新用户联系方式
   */
  updateContact(contactUuid: string, data: UserContactUpdate): Promise<{ message: string }> {
    return request.put(`/settings/users/contacts/${contactUuid}`, data)
  },

  /**
   * 删除用户联系方式
   */
  deleteContact(contactUuid: string): Promise<{ message: string }> {
    return request.delete(`/settings/users/contacts/${contactUuid}`)
  },

  /**
   * 测试用户联系方式
   */
  testContact(contactUuid: string, data: { address: string; subject?: string; content?: string }): Promise<{ message: string; detail?: string }> {
    return request.post(`/settings/users/contacts/${contactUuid}/test`, data)
  },

  /**
   * 设置为主联系方式
   */
  setPrimaryContact(contactUuid: string): Promise<{ message: string }> {
    return request.post(`/settings/users/contacts/${contactUuid}/set-primary`)
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
    return request.get('/settings/user-groups')
  },

  /**
   * 创建用户组
   */
  create(data: UserGroupCreate): Promise<UserGroupInfo> {
    return request.post('/settings/user-groups', data)
  },

  /**
   * 更新用户组
   */
  update(uuid: string, data: Partial<UserGroupCreate>): Promise<{ message: string }> {
    return request.put(`/settings/user-groups/${uuid}`, data)
  },

  /**
   * 删除用户组
   */
  delete(uuid: string): Promise<{ message: string }> {
    return request.delete(`/settings/user-groups/${uuid}`)
  },

  /**
   * 获取用户组成员列表
   */
  listMembers(groupUuid: string): Promise<GroupMember[]> {
    return request.get(`/settings/user-groups/${groupUuid}/members`)
  },

  /**
   * 添加用户到用户组
   */
  addMember(groupUuid: string, userUuid: string): Promise<{ message: string; mapping_uuid: string }> {
    return request.post(`/settings/user-groups/${groupUuid}/members`, { user_uuid: userUuid })
  },

  /**
   * 从用户组移除用户
   */
  removeMember(groupUuid: string, userUuid: string): Promise<{ message: string }> {
    return request.delete(`/settings/user-groups/${groupUuid}/members/${userUuid}`)
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
    return request.get('/settings/notifications/templates')
  },

  /**
   * 创建通知模板
   */
  createTemplate(data: Partial<NotificationTemplate>): Promise<NotificationTemplate> {
    return request.post('/settings/notifications/templates', data)
  },

  /**
   * 更新通知模板
   */
  updateTemplate(uuid: string, data: Partial<NotificationTemplate>): Promise<{ message: string }> {
    return request.put(`/settings/notifications/templates/${uuid}`, data)
  },

  /**
   * 删除通知模板
   */
  deleteTemplate(uuid: string): Promise<{ message: string }> {
    return request.delete(`/settings/notifications/templates/${uuid}`)
  },

  /**
   * 切换模板启用状态
   */
  toggleTemplate(uuid: string, enabled: boolean): Promise<{ message: string }> {
    return request.patch(`/settings/notifications/templates/${uuid}`, { enabled })
  },

  /**
   * 测试通知
   */
  testTemplate(uuid: string): Promise<{ message: string }> {
    return request.post(`/settings/notifications/templates/${uuid}/test`)
  },

  /**
   * 获取通知历史
   */
  listHistory(params?: { type?: string; page?: number; page_size?: number }): Promise<NotificationHistory[]> {
    return request.get('/settings/notifications/history', { params })
  },

  /**
   * 获取通知接收人列表
   */
  listRecipients(): Promise<NotificationRecipient[]> {
    return request.get('/settings/notifications/recipients')
  },

  /**
   * 创建通知接收人
   */
  createRecipient(data: NotificationRecipientCreate): Promise<NotificationRecipient> {
    return request.post('/settings/notifications/recipients', data)
  },

  /**
   * 更新通知接收人
   */
  updateRecipient(uuid: string, data: NotificationRecipientUpdate): Promise<{ message: string }> {
    return request.put(`/settings/notifications/recipients/${uuid}`, data)
  },

  /**
   * 删除通知接收人
   */
  deleteRecipient(uuid: string): Promise<{ message: string }> {
    return request.delete(`/settings/notifications/recipients/${uuid}`)
  },

  /**
   * 切换接收人启用状态
   */
  toggleRecipient(uuid: string): Promise<{ message: string; is_active: boolean }> {
    return request.patch(`/settings/notifications/recipients/${uuid}/toggle`)
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
    return request.post(`/settings/notifications/recipients/${uuid}/test`)
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
    return request.get('/settings/api-keys')
  },

  /**
   * 创建API密钥
   */
  create(data: { name: string; expires_at?: string }): Promise<APIKey> {
    return request.post('/settings/api-keys', data)
  },

  /**
   * 删除API密钥
   */
  delete(key_id: string): Promise<{ message: string }> {
    return request.delete(`/settings/api-keys/${key_id}`)
  },

  /**
   * 获取API统计
   */
  getStats(): Promise<APIStats> {
    return request.get('/settings/api-stats')
  }
}
