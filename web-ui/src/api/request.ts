import axios, { type AxiosInstance, type AxiosError, type InternalAxiosRequestConfig } from 'axios'
import { message } from 'ant-design-vue'

// 创建axios实例
const service: AxiosInstance = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL || '/api',
  timeout: 30000,
  headers: {
    'Content-Type': 'application/json'
  }
})

// 请求拦截器
service.interceptors.request.use(
  (config: InternalAxiosRequestConfig) => {
    const token = localStorage.getItem('access_token')
    if (token && config.headers) {
      config.headers['Authorization'] = `Bearer ${token}`
    }
    return config
  },
  (error) => {
    return Promise.reject(error)
  }
)

// 响应拦截器
service.interceptors.response.use(
  (response) => {
    console.log('API响应成功:', response.config?.url, response.data)
    return response.data
  },
  (error: AxiosError) => {
    console.error('API请求失败:', error.config?.url, error)
    const { response } = error

    if (response) {
      switch (response.status) {
        case 401:
          message.error('认证失败，请重新登录')
          localStorage.removeItem('access_token')
          window.location.href = '/login'
          break
        case 403:
          message.error('没有权限访问此资源')
          break
        case 404:
          message.error('请求的资源不存在')
          break
        case 500:
          message.error('服务器错误，请稍后重试')
          break
        default:
          message.error((response.data as any)?.message || '请求失败')
      }
    } else {
      message.error('网络连接失败，请检查网络设置')
    }

    return Promise.reject(error)
  }
)

export default service
