import axios, { type AxiosInstance, type AxiosError, type InternalAxiosRequestConfig } from 'axios'
import { message as toast } from '@/utils/toast'
import { isElectron } from '@/utils/isElectron'

// 双形态:Electron 形态优先 window.appConfig.apiBase,浏览器形态回退 VITE_API_BASE_URL
const baseURL = window.appConfig?.apiBase || import.meta.env.VITE_API_BASE_URL || ''

const service: AxiosInstance = axios.create({
  baseURL,
  timeout: 30000,
  headers: { 'Content-Type': 'application/json' }
})

// 请求拦截器 - 浏览器形态注入 JWT
// Electron 形态:由主进程 onBeforeSendHeaders 透明注入(见 src/main/auth.ts),
// 渲染层不持 token,跳过拦截器避免双重注入
service.interceptors.request.use(
  (config: InternalAxiosRequestConfig) => {
    if (isElectron) return config
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
      // Electron 形态:由主进程 onHeadersReceived 处理(清 safeStorage + 推 auth:unauthorized)
      // 浏览器形态:渲染层清 localStorage
      if (!isElectron) {
        localStorage.removeItem('access_token')
        localStorage.removeItem('user_info')
      }
      // hash 路由下用 hash 跳转,避免 href 丢 hash
      window.location.hash = '#/login'
      return Promise.reject(error)
    }

    // 其他错误 - 优先用新格式的 message
    const errorMsg = responseData?.message || error.message || '请求失败'
    toast.error(errorMsg)
    return Promise.reject(error)
  }
)

export default service
