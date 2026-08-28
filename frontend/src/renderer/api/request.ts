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

// 响应拦截器 - 解信封为业务 payload (deep module)
// 不变量: 成功时返回值 = 业务数据本身, 调用方不再 .data 二次解包。
//   - 非信封(无 code 字段): 原样透传(非标准端点)
//   - code !== 0: 业务错误, reject(Error + .code)
//   - code === 0 + data 为数组 + meta.total: 分页端点, 重组为 PaginatedData<T>
//   - code === 0 其他(单实体/裸数组): 返 data 本身
service.interceptors.response.use(
  (response) => {
    const body = response.data
    if (!body || typeof body.code !== 'number') return body
    if (body.code !== 0) {
      const error = new Error(body.message || '操作失败')
      ;(error as Error & { code: number }).code = body.code
      return Promise.reject(error)
    }
    const meta = body.meta
    if (Array.isArray(body.data) && meta && typeof meta.total === 'number') {
      return {
        items: body.data,
        total: meta.total,
        page: meta.page,
        page_size: meta.page_size,
        total_pages: meta.total_pages,
      }
    }
    return body.data
  },
  async (error: AxiosError) => {
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
      // 浏览器形态:走 clearAuth() 收口(清 token+user_info),不再裸 localStorage 绕过 auth
      // 动态 import 避开与 auth.ts 的顶层循环依赖(auth.ts 顶层 import request)
      if (!isElectron) {
        const { clearAuth } = await import('./modules/auth')
        await clearAuth()
      }
      // hash 路由下用 hash 跳转,避免 href 丢 hash
      window.location.hash = '#/login'
      return Promise.reject(error)
    }

    // 429 限流:后端滑动窗口 100 req/60s/IP;dev 下所有浏览器流量经 vite 代理
    // 共享 127.0.0.1 一个桶,轮询+快速操作易触顶。给明确文案而非 axios 原始信息
    if (status === 429) {
      if (!(error.config as any)?.skipErrorToast) {
        toast.error('请求过于频繁，请稍候一分钟后再试')
      }
      return Promise.reject(error)
    }

    // 其他错误 - 优先用新格式的 message
    // skipErrorToast: 轮询类/已知后端缺口接口 opt-out 全局 toast,由调用方自持降级态(避免切页 toast 刷屏)
    if (!(error.config as any)?.skipErrorToast) {
      const errorMsg = responseData?.message || error.message || '请求失败'
      toast.error(errorMsg)
    }
    return Promise.reject(error)
  }
)

export default service
