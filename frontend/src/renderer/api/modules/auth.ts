import request from '../request'
import { auth } from '@/composables/useAuth'

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
    return request.post('/api/v1/auth/login', data)
  },

  /**
   * 用户登出
   */
  logout(): Promise<void> {
    return request.post('/api/v1/auth/logout')
  },

  /**
   * 验证 Token
   */
  verifyToken(): Promise<{ valid: boolean; user?: UserInfo }> {
    return request.get('/api/v1/auth/verify')
  },

  /**
   * 获取当前用户信息
   */
  getCurrentUser(): Promise<UserInfo> {
    return request.get('/api/v1/auth/me')
  },

  /**
   * 修改密码
   */
  changePassword(data: { old_password: string; new_password: string }): Promise<void> {
    return request.post('/api/v1/auth/change-password', data)
  },
}

// 辅助函数 - 检查是否已登录(异步化:Electron 形态需走 IPC 查 safeStorage)
// 调用方(路由守卫)须 await
export const isAuthenticated = (): Promise<boolean> => {
  return auth.isAuthenticated()
}

// 辅助函数 - 获取存储的用户信息(非敏感,双形态均 localStorage)
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

// 辅助函数 - 保存认证信息(写瓶颈)
// token 经 useAuth 收口(Electron→safeStorage / 浏览器→localStorage)
// user_info 非敏感,双形态均 localStorage
export const saveAuth = async (response: LoginResponse): Promise<void> => {
  await auth.login(response.token)
  localStorage.setItem('user_info', JSON.stringify(response.user))
}

// 辅助函数 - 清除认证信息(写瓶颈)
export const clearAuth = async (): Promise<void> => {
  await auth.logout()
  localStorage.removeItem('user_info')
}
