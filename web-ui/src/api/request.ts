import axios, { type AxiosInstance, type AxiosError, type InternalAxiosRequestConfig } from 'axios'
import { message } from 'ant-design-vue'

const baseURL = import.meta.env.VITE_API_BASE_URL || '/api'

const service: AxiosInstance = axios.create({
  baseURL,
  timeout: 30000,
  headers: { 'Content-Type': 'application/json' }
})

// 请求拦截器 - 自动注入 JWT Token
service.interceptors.request.use(
  (config: InternalAxiosRequestConfig) => {
    const token = localStorage.getItem('access_token')
    if (token && config.headers) {
      config.headers['Authorization'] = `Bearer ${token}`
    }
    return config
  },
  (error) => Promise.reject(error)
)

// 响应拦截器 - 处理错误和 Token 过期
service.interceptors.response.use(
  (response) => {
    // 检查业务错误
    if (response.data?.success === false) {
      const error: any = new Error(response.data?.message || '操作失败')
      error.code = response.data?.error || 'BUSINESS_ERROR'
      return Promise.reject(error)
    }
    return response.data
  },
  (error: AxiosError) => {
    // 忽略取消的请求
    if (axios.isCancel(error) || error.code === 'ERR_CANCELED') {
      return Promise.reject({ name: 'AbortError', message: '请求已取消' })
    }

    const status = error.response?.status

    // 401 未授权
    if (status === 401) {
      // 如果是登录请求失败，不跳转，由 Login.vue 处理错误提示
      const isLoginRequest = error.config?.url?.includes('/auth/login')
      if (isLoginRequest) {
        const backendMsg = (error.response?.data as any)?.detail || (error.response?.data as any)?.error
        const errorMsg = backendMsg || '用户名或密码错误'
        return Promise.reject(new Error(errorMsg))
      }
      // 其他401错误，清除登录状态并跳转
      localStorage.removeItem('access_token')
      localStorage.removeItem('user_info')
      window.location.href = '/login'
      return Promise.reject(error)
    }

    // 403 禁止访问
    if (status === 403) {
      message.error('没有权限执行此操作')
      return Promise.reject(error)
    }

    // 其他错误
    const errorMsg = (error.response?.data as any)?.message || error.message || '请求失败'
    message.error(errorMsg)
    return Promise.reject(error)
  }
)

export default service
