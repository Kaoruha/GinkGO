import request from '../request'

export interface LoginRequest {
  username: string
  password: string
}

export interface LoginResponse {
  token: string
  expires_at: string
  user: {
    uuid: string
    username: string
    display_name: string
    is_admin: boolean
  }
}

export interface UserInfo {
  uuid: string
  username: string
  display_name: string
  email?: string
  is_admin: boolean
  roles?: string[]
}

export const authApi = {
  /**
   * 用户登录
   */
  login(data: LoginRequest): Promise<LoginResponse> {
    return request.post('/v1/auth/login', data)
  },

  /**
   * 用户登出
   */
  logout(): Promise<void> {
    return request.post('/v1/auth/logout')
  },

  /**
   * 验证 Token
   */
  verifyToken(): Promise<{ valid: boolean; user?: UserInfo }> {
    return request.get('/v1/auth/verify')
  },

  /**
   * 获取当前用户信息
   */
  getCurrentUser(): Promise<UserInfo> {
    return request.get('/v1/auth/me')
  },

  /**
   * 修改密码
   */
  changePassword(data: { old_password: string; new_password: string }): Promise<void> {
    return request.post('/v1/auth/change-password', data)
  },
}

// 辅助函数 - 检查是否已登录
export const isAuthenticated = (): boolean => {
  return !!localStorage.getItem('access_token')
}

// 辅助函数 - 获取存储的用户信息
export const getStoredUser = (): UserInfo | null => {
  const userStr = localStorage.getItem('user_info')
  if (userStr) {
    try {
      return JSON.parse(userStr)
    } catch {
      return null
    }
  }
  return null
}

// 辅助函数 - 保存认证信息
export const saveAuth = (response: LoginResponse) => {
  localStorage.setItem('access_token', response.token)
  localStorage.setItem('user_info', JSON.stringify(response.user))
}

// 辅助函数 - 清除认证信息
export const clearAuth = () => {
  localStorage.removeItem('access_token')
  localStorage.removeItem('user_info')
}
