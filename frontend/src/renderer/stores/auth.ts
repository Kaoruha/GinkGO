import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { authApi, saveAuth, clearAuth, getStoredUser } from '@/api'
import type { UserInfo, LoginRequest } from '@/api'
import { isElectron } from '@/utils/isElectron'
import { auth } from '@/composables/useAuth'

export const useAuthStore = defineStore('auth', () => {
  const user = ref<UserInfo | null>(getStoredUser())
  // Electron 形态:localStorage 无 token,启动时 init() 从 safeStorage 拉至内存 ref
  // 浏览器形态:直接从 localStorage 初始化
  const token = ref<string | null>(isElectron ? null : localStorage.getItem('access_token'))
  const loading = ref(false)

  const isLoggedIn = computed(() => !!token.value && !!user.value)
  const isAdmin = computed(() => user.value?.is_admin ?? false)
  const displayName = computed(() => user.value?.display_name || user.value?.username || '用户')

  // Electron 形态:启动时一次性从 safeStorage 拉取 token 至内存 ref
  // 浏览器形态:no-op(token ref 已从 localStorage 初始化)
  // 必须在 app.mount 前完成,否则首次路由守卫看到 token=null 误判未登录
  async function init() {
    if (isElectron) {
      token.value = await auth.getToken()
      // 401 时主进程 push auth:unauthorized → 清 Pinia 状态(UI 一致性)
      // 导航已由 request.ts 401 拦截器 window.location.hash = '#/login' 处理(双形态都跑),此处不重复
      // disposer 不调可接受:init 是 app 生命周期单例,从不卸载
      window.auth!.onUnauthorized(() => {
        token.value = null
        user.value = null
        localStorage.removeItem('user_info')
      })
    }
  }

  // 登录
  async function login(credentials: LoginRequest) {
    loading.value = true
    try {
      const response = await authApi.login(credentials)
      token.value = response.token
      user.value = response.user
      await saveAuth(response)
      return response
    } catch (error) {
      console.error('Login failed:', error)
      throw error
    } finally {
      loading.value = false
    }
  }

  // 登出
  async function logout() {
    loading.value = true
    try {
      await authApi.logout()
    } catch (error) {
      console.error('Logout API failed:', error)
    } finally {
      token.value = null
      user.value = null
      await clearAuth()
      loading.value = false
    }
  }

  // 验证 Token
  async function verifyToken() {
    if (!token.value) return false

    try {
      const result = await authApi.verifyToken()
      if (!result.valid) {
        token.value = null
        user.value = null
        await clearAuth()
        return false
      }
      return true
    } catch (error) {
      token.value = null
      user.value = null
      await clearAuth()
      return false
    }
  }

  // 获取当前用户信息
  async function fetchCurrentUser() {
    try {
      const result = await authApi.getCurrentUser()
      user.value = result
      // user_info 非敏感,双形态均写 localStorage
      localStorage.setItem('user_info', JSON.stringify(result))
      return result
    } catch (error) {
      console.error('Failed to fetch user:', error)
      return null
    }
  }

  return {
    user,
    token,
    loading,
    isLoggedIn,
    isAdmin,
    displayName,
    init,
    login,
    logout,
    verifyToken,
    fetchCurrentUser,
  }
})
