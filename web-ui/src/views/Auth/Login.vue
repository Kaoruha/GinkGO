<template>
  <div class="login-container">
    <div class="login-card">
      <div class="login-header">
        <h1 class="login-title">Ginkgo</h1>
        <p class="login-subtitle">量化交易系统</p>
      </div>

      <form @submit.prevent="handleLogin" class="login-form">
        <div class="form-group">
          <label class="form-label">用户名</label>
          <input
            v-model="formState.username"
            type="text"
            placeholder="请输入用户名"
            class="form-input"
            required
            autocomplete="username"
          />
        </div>

        <div class="form-group">
          <label class="form-label">密码</label>
          <input
            v-model="formState.password"
            type="password"
            placeholder="请输入密码"
            class="form-input"
            required
            autocomplete="current-password"
          />
        </div>

        <button type="submit" class="btn-login" :disabled="loading">
          <span v-if="loading" class="loading-spinner"></span>
          {{ loading ? '登录中...' : '登录' }}
        </button>
      </form>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive } from 'vue'
import { useRouter } from 'vue-router'
import { authApi } from '@/api/modules/auth'

const router = useRouter()

const loading = ref(false)
const isSubmitting = ref(false)
const formState = reactive({
  username: '',
  password: ''
})

async function handleLogin() {
  if (isSubmitting.value) {
    console.log('⚠️ 登录请求已在处理中，忽略重复请求')
    return
  }

  isSubmitting.value = true
  loading.value = true
  try {
    const response = await authApi.login(formState)
    localStorage.setItem('access_token', response.token)
    console.log('登录成功')
    router.push('/')
  } catch (error) {
    console.error('登录失败，请检查用户名和密码')
  } finally {
    loading.value = false
    isSubmitting.value = false
  }
}
</script>

<style scoped>
.login-container {
  min-height: 100vh;
  display: flex;
  align-items: center;
  justify-content: center;
  background: #0f0f1a;
  padding: 20px;
}

.login-card {
  width: 100%;
  max-width: 400px;
  background: #1a1a2e;
  border: 1px solid #2a2a3e;
  border-radius: 12px;
  padding: 40px;
  box-shadow: 0 4px 24px rgba(0, 0, 0, 0.3);
}

.login-header {
  text-align: center;
  margin-bottom: 32px;
}

.login-title {
  font-size: 32px;
  font-weight: 700;
  color: #1890ff;
  margin: 0 0 8px 0;
}

.login-subtitle {
  font-size: 14px;
  color: #8a8a9a;
  margin: 0;
}

.login-form {
  display: flex;
  flex-direction: column;
  gap: 20px;
}

.form-group {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.form-label {
  font-size: 13px;
  color: #8a8a9a;
  font-weight: 500;
}

.form-input {
  width: 100%;
  padding: 12px 16px;
  background: #2a2a3e;
  border: 1px solid #3a3a4e;
  border-radius: 6px;
  color: #ffffff;
  font-size: 14px;
  transition: border-color 0.2s;
}

.form-input:focus {
  outline: none;
  border-color: #1890ff;
}

.form-input::placeholder {
  color: #5a5a6e;
}

.btn-login {
  width: 100%;
  padding: 12px;
  background: #1890ff;
  border: none;
  border-radius: 6px;
  color: #ffffff;
  font-size: 16px;
  font-weight: 500;
  cursor: pointer;
  transition: background 0.2s;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
}

.btn-login:hover:not(:disabled) {
  background: #40a9ff;
}

.btn-login:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.loading-spinner {
  display: inline-block;
  width: 16px;
  height: 16px;
  border: 2px solid rgba(255, 255, 255, 0.3);
  border-top-color: #ffffff;
  border-radius: 50%;
  animation: spin 0.6s linear infinite;
}

@keyframes spin {
  to { transform: rotate(360deg); }
}

@media (max-width: 480px) {
  .login-card {
    padding: 24px;
  }

  .login-title {
    font-size: 24px;
  }
}
</style>
