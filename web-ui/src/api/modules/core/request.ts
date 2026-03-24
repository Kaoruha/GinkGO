import axios, { type AxiosRequestConfig, type AxiosError, type InternalAxiosRequestConfig } from 'axios'
import { message } from '@/utils/toast'

/**
 * 核心请求封装 - 统一 axios 配置和拦截器
 */

// 请求配置
const config: AxiosRequestConfig = {
  baseURL: import.meta.env.VITE_API_BASE_URL || '/api',
  timeout: 30000,
  headers: {
    'Content-Type': 'application/json'
  }
}

// 创建 axios 实例
const service = axios.create(config)

// 请求ID计数器
let requestId = 0

function generateRequestId(): string {
  return `req_${Date.now()}_${++requestId}`
}

// 获取 token
function getToken(): string | null {
  return localStorage.getItem('access_token')
}

// 请求拦截器
service.interceptors.request.use(
  (config: InternalAxiosRequestConfig) => {
    const requestId = generateRequestId()
    config.headers = {
      ...config.headers,
      'X-Request-ID': requestId
    }

    // 添加 token
    const token = getToken()
    if (token) {
      config.headers!['Authorization'] = `Bearer ${token}`
    }

    // 调试日志
    if (import.meta.env.DEV) {
      console.log(`🚀 [${requestId}] Request:`, {
        url: config.url,
        method: config.method,
        data: config.data
      })
    }

    return config
  },
  (error: AxiosError) => {
    console.error('请求拦截器错误:', error)
    return Promise.reject(error)
  }
)

// 响应拦截器
service.interceptors.response.use(
  (response) => {
    const requestId = response.config.headers?.['X-Request-ID'] as string

    // 调试日志
    if (import.meta.env.DEV) {
      console.log(`✅ [${requestId}] Response:`, {
        status: response.status,
        data: response.data
      })
    }

    return response.data
  },
  (error: AxiosError) => {
    const requestId = error.config?.headers?.['X-Request-ID'] as string

    if (error.response) {
      const status = error.response.status
      const data = error.response.data

      // 处理业务错误
      if (status === 401) {
        message.error('登录已过期，请重新登录')
        // 跳转到登录页
        window.location.href = '/login'
      } else if (status === 403) {
        message.error('没有权限访问此资源')
      } else if (status === 404) {
        message.error('请求的资源不存在')
      } else if (status >= 500) {
        message.error('服务器错误，请稍后重试')
      }

      if (import.meta.env.DEV) {
        console.error(`❌ [${requestId}] Error:`, { status, data })
      }
    } else {
      // 网络错误
      message.error('网络连接失败，请检查网络')
    }

    return Promise.reject(error)
  }
)

export default service
