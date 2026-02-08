import request from '../request'
import type { RequestOptions } from '@/types/api-request'

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
   * @param data 登录数据
   * @param options 请求选项（支持 signal 取消请求）
   */
  login(data: LoginRequest, options?: RequestOptions): Promise<LoginResponse> {
    return request.post('/v1/auth/login', data, { signal: options?.signal })
  },

  /**
   * 用户登出
   * @param options 请求选项（支持 signal 取消请求）
   */
  logout(options?: RequestOptions): Promise<void> {
    return request.post('/v1/auth/logout', {}, { signal: options?.signal })
  },

  /**
   * 验证Token
   * @param options 请求选项（支持 signal 取消请求）
   */
  verifyToken(options?: RequestOptions): Promise<{ valid: boolean }> {
    return request.get('/v1/auth/verify', { signal: options?.signal })
  }
}
