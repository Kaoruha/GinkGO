import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { authApi, saveAuth, clearAuth, getStoredUser, isAuthenticated } from '@/api'
import type { UserInfo, LoginRequest } from '@/api'

export const useAuthStore = defineStore('auth', () => {
  const user = ref<UserInfo | null>(getStoredUser())
  const token = ref<string | null>(localStorage.getItem('access_token'))
  const loading = ref(false)

  const isLoggedIn = computed(() => !!token.value && !!user.value)
  const isAdmin = computed(() => user.value?.is_admin ?? false)
  const displayName = computed(() => user.value?.display_name || user.value?.username || '用户')

  // 登录
  async function login(credentials: LoginRequest) {
    loading.value = true
    try {
      const response = await authApi.login(credentials)
      const payload = response.data
      token.value = payload.token
      user.value = payload.user
      saveAuth(payload)
      return payload
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
      clearAuth()
      loading.value = false
    }
  }

  // 验证 Token
  async function verifyToken() {
    if (!token.value) return false

    try {
      const result = await authApi.verifyToken()
      if (!result.data.valid) {
        token.value = null
        user.value = null
        clearAuth()
        return false
      }
      return true
    } catch (error) {
      token.value = null
      user.value = null
      clearAuth()
      return false
    }
  }

  // 获取当前用户信息
  async function fetchCurrentUser() {
    try {
      const result = await authApi.getCurrentUser()
      const payload = result.data
      user.value = payload
      localStorage.setItem('user_info', JSON.stringify(payload))
      return payload
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
    login,
    logout,
    verifyToken,
    fetchCurrentUser,
  }
})
