import axios, { type AxiosInstance, type AxiosError, type InternalAxiosRequestConfig } from 'axios'
import { message as toast } from '@/utils/toast'

const baseURL = import.meta.env.VITE_API_BASE_URL || ''

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

// 响应拦截器 - 解包 {code, data} 信封
service.interceptors.response.use(
  (response) => {
    const data = response.data
    if (data && typeof data.code === 'number' && data.code !== 0) {
      const error = new Error(data.message || '操作失败')
      ;(error as Error & { code: number }).code = data.code
      return Promise.reject(error)
    }
    return data
  },
  (error: AxiosError) => {
    // 忽略取消的请求
    if (axios.isCancel(error) || error.code === 'ERR_CANCELED') {
      return Promise.reject({ name: 'AbortError', message: '请求已取消' })
    }

    const status = error.response?.status
    const responseData = error.response?.data as any

    // 401 未授权
    if (status === 401) {
      const isLoginRequest = error.config?.url?.includes('/auth/login')
      if (isLoginRequest) {
        const errorMsg = responseData?.message || '用户名或密码错误'
        return Promise.reject(new Error(errorMsg))
      }
      localStorage.removeItem('access_token')
      localStorage.removeItem('user_info')
      window.location.href = '/login'
      return Promise.reject(error)
    }

    // 其他错误 - 优先用新格式的 message
    const errorMsg = responseData?.message || error.message || '请求失败'
    toast.error(errorMsg)
    return Promise.reject(error)
  }
)

export default service
