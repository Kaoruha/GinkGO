<template>
  <div class="min-h-screen flex items-center justify-center bg-gray-50">
    <div class="max-w-md w-full card">
      <div class="text-center mb-8">
        <h1 class="text-3xl font-bold text-primary mb-2">
          Ginkgo
        </h1>
        <p class="text-gray-600">
          量化交易系统
        </p>
      </div>

      <a-form
        :model="formState"
        name="login"
        layout="vertical"
        @finish="handleLogin"
      >
        <a-form-item
          label="用户名"
          name="username"
          :rules="[{ required: true, message: '请输入用户名' }]"
        >
          <a-input
            v-model:value="formState.username"
            placeholder="请输入用户名"
          />
        </a-form-item>

        <a-form-item
          label="密码"
          name="password"
          :rules="[{ required: true, message: '请输入密码' }]"
        >
          <a-input-password
            v-model:value="formState.password"
            placeholder="请输入密码"
          />
        </a-form-item>

        <a-form-item>
          <a-button
            type="primary"
            html-type="submit"
            block
            :loading="loading"
          >
            登录
          </a-button>
        </a-form-item>
      </a-form>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive } from 'vue'
import { useRouter } from 'vue-router'
import { message } from 'ant-design-vue'
import { authApi } from '@/api/modules/auth'

const router = useRouter()

const loading = ref(false)
const formState = reactive({
  username: '',
  password: ''
})

async function handleLogin() {
  loading.value = true
  try {
    const response = await authApi.login(formState)
    localStorage.setItem('access_token', response.token)
    message.success('登录成功')
    router.push('/')
  } catch (error) {
    message.error('登录失败，请检查用户名和密码')
  } finally {
    loading.value = false
  }
}
</script>
