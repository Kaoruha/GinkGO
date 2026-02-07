<template>
  <div class="min-h-screen bg-gray-50 flex">
    <!-- 侧边栏 -->
    <aside class="w-64 bg-white border-r border-gray-200 flex flex-col">
      <div class="h-16 flex items-center px-6 border-b border-gray-200">
        <h1 class="text-xl font-bold text-primary">
          Ginkgo
        </h1>
      </div>

      <nav class="flex-1 p-4 space-y-1 overflow-y-auto">
        <!-- 返回首页 -->
        <div class="mb-4">
          <router-link
            to="/"
            class="flex items-center px-4 py-3 rounded-lg transition-colors text-gray-700 hover:bg-gray-100"
          >
            <span class="mr-3">←</span>
            <span>返回首页</span>
          </router-link>
        </div>

        <!-- 设置子菜单 -->
        <div class="mb-4">
          <div class="px-4 mb-2 text-xs font-semibold text-gray-500 uppercase">
            系统设置
          </div>
          <router-link
            v-for="item in settingsMenuItems"
            :key="item.path"
            :to="item.path"
            class="flex items-center px-4 py-2 rounded-lg transition-colors text-sm"
            :class="isActive(item.path) ? 'bg-primary text-white' : 'text-gray-600 hover:bg-gray-100'"
          >
            <span class="mr-3">{{ item.icon }}</span>
            <span>{{ item.label }}</span>
          </router-link>
        </div>
      </nav>

      <div class="p-4 border-t border-gray-200">
        <div class="flex items-center">
          <div class="w-8 h-8 bg-primary rounded-full flex items-center justify-center text-white">
            A
          </div>
          <div class="ml-3">
            <p class="text-sm font-medium text-gray-900">
              Admin
            </p>
          </div>
        </div>
      </div>
    </aside>

    <!-- 主内容区 -->
    <div class="flex-1 flex flex-col">
      <header class="h-16 bg-white border-b border-gray-200 flex items-center justify-between px-6">
        <div class="flex items-center space-x-4">
          <h2 class="text-lg font-semibold text-gray-900">
            {{ pageTitle }}
          </h2>
        </div>
        <div class="flex items-center space-x-4">
          <span class="text-sm text-gray-500">{{ currentTime }}</span>
        </div>
      </header>

      <main class="flex-1 overflow-auto p-6">
        <router-view />
      </main>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, ref, onMounted, onUnmounted } from 'vue'
import { useRoute } from 'vue-router'

const route = useRoute()

const mainMenuItems = [
  { path: '/', label: '仪表盘', icon: '' },
  { path: '/portfolio', label: '投资组合', icon: '' },
  { path: '/backtest', label: '回测任务', icon: '' },
  { path: '/components', label: '组件管理', icon: '' },
  { path: '/data', label: '数据管理', icon: '' },
  { path: '/alert', label: '警报中心', icon: '' },
  { path: '/settings', label: '系统设置', icon: '' }
]

const settingsMenuItems = [
  { path: '/settings/users', label: '用户管理', icon: '' },
  { path: '/settings/user-groups', label: '用户组管理', icon: '' },
  { path: '/settings/notifications', label: '通知管理', icon: '' },
  { path: '/settings/api', label: 'API接口设置', icon: '' }
]

const username = ref('Admin')
const currentTime = ref('')

const userInitial = computed(() => username.value.charAt(0).toUpperCase())

const isSettingsRoute = computed(() => route.path.startsWith('/settings'))

const pageTitle = computed(() => {
  if (isSettingsRoute.value) {
    const item = settingsMenuItems.find(item => route.path.startsWith(item.path))
    return item?.label || '系统设置'
  }
  const item = mainMenuItems.find(item => route.path.startsWith(item.path) || (item.path === '/settings' && route.path.startsWith('/settings')))
  return item?.label || 'Ginkgo'
})

const isActive = (path: string) => {
  return route.path === path || route.path.startsWith(path + '/')
}

const updateTime = () => {
  currentTime.value = new Date().toLocaleString('zh-CN')
}

let timer: ReturnType<typeof setInterval>

onMounted(() => {
  updateTime()
  timer = setInterval(updateTime, 1000)
})

onUnmounted(() => {
  clearInterval(timer)
})
</script>
