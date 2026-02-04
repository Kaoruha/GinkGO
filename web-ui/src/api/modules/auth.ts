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

export const authApi = {
  /**
   * 用户登录
   */
  login(data: LoginRequest): Promise<LoginResponse> {
    return request.post('/auth/login', data)
  },

  /**
   * 用户登出
   */
  logout(): Promise<void> {
    return request.post('/auth/logout')
  },

  /**
   * 验证Token
   */
  verifyToken(): Promise<{ valid: boolean }> {
    return request.get('/auth/verify')
  }
}
