import axios, { type AxiosInstance, type AxiosError, type InternalAxiosRequestConfig } from 'axios'
import { message } from 'ant-design-vue'

// 创建axios实例
const baseURL = import.meta.env.VITE_API_BASE_URL || '/api'
console.log('🔧 Axios baseURL:', baseURL, 'VITE_API_BASE_URL:', import.meta.env.VITE_API_BASE_URL)

const service: AxiosInstance = axios.create({
  baseURL,
  timeout: 30000,
  headers: {
    'Content-Type': 'application/json'
  }
})

// 生成唯一请求ID用于追踪
let requestIdCounter = 0
function generateRequestId(): string {
  return `req_${Date.now()}_${++requestIdCounter}`
}

// 请求拦截器
service.interceptors.request.use(
  (config: InternalAxiosRequestConfig) => {
    const requestId = generateRequestId()
    ;(config as any).requestId = requestId

    const token = localStorage.getItem('access_token')
    if (token && config.headers) {
      config.headers['Authorization'] = `Bearer ${token}`
    }

    // 强制确保使用相对路径
    config.baseURL = '/api'

    // 如果 URL 是绝对路径，转换为相对路径
    if (config.url && (config.url.startsWith('http://') || config.url.startsWith('https://'))) {
      console.warn('⚠️ 检测到绝对路径 URL，转换为相对路径:', config.url)
      const url = new URL(config.url)
      config.url = url.pathname + url.search
    }

    // 调试：打印请求配置和数据
    console.log(`🚀 [${requestId}] Request:`, {
      url: config.url,
      baseURL: config.baseURL,
      fullURL: `${config.baseURL || ''}${config.url}`,
      method: config.method,
      data: config.data,
      hasToken: !!token
    })

    return config
  },
  (error) => {
    return Promise.reject(error)
  }
)

// AbortController 已被 Axios 原生支持
// 只需在请求时传入 signal 参数即可
// Axios 会自动处理取消逻辑

// 响应拦截器
service.interceptors.response.use(
  (response) => {
    const requestId = (response.config as any)?.requestId || 'unknown'
    console.log(`✅ [${requestId}] Response Success:`, {
      url: response.config?.url,
      status: response.status,
      data: response.data
    })

    // 检查业务错误（响应体中的 success 字段）
    if (response.data?.success === false) {
      const error: any = new Error(response.data?.message || '操作失败')
      error.code = response.data?.error || 'BUSINESS_ERROR'
      error.details = response.data?.details
      return Promise.reject(error)
    }

    return response.data
  },
  (error: AxiosError) => {
    const requestId = (error.config as any)?.requestId || 'unknown'

    // 忽略 AbortError（主动取消的请求）
    if (axios.isCancel(error) || error.code === 'ERR_CANCELED' || error.message === 'canceled') {
      console.log(`⚠️ [${requestId}] Request Cancelled:`, error.config?.url)
      return Promise.reject({ name: 'AbortError', message: '请求已取消', ...error })
    }

    console.error(`❌ [${requestId}] Response Error:`, {
      url: error.config?.url,
      status: error.response?.status,
      statusText: error.response?.statusText,
      errorData: error.response?.data
    })

    // 为错误对象添加标准化的 code 和 message
    if (error.response?.data?.error) {
      // 业务错误码
      error.code = error.response.data.error
      error.message = error.response.data.message
    } else if (error.response?.status) {
      // HTTP 状态码转错误码
      error.code = `HTTP_${error.response.status}`
      error.message = (error.response.data as any)?.message
    }

    // 不在这里显示错误消息，让组件通过 handleApiError 统一处理
    // 这样可以更灵活地控制错误提示时机和方式
    return Promise.reject(error)
  }
)

export default service
