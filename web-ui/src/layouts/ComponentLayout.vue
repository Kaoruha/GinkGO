<template>
  <div class="h-screen flex bg-gray-50">
    <!-- 左侧导航栏 -->
    <aside class="w-64 bg-white border-r border-gray-200 flex flex-col flex-shrink-0">
      <div class="h-14 flex items-center px-6 border-b border-gray-200">
        <h1 class="text-xl font-bold text-primary">Ginkgo</h1>
      </div>

      <nav class="flex-1 p-3 space-y-1 overflow-y-auto">
        <template v-for="item in menuItems" :key="item.path">
          <!-- 有子菜单的项目 -->
          <div v-if="item.children">
            <div
              @click="toggleMenu(item.path)"
              class="flex items-center justify-between px-4 py-2.5 rounded-lg cursor-pointer transition-colors text-sm"
              :class="isMenuActive(item) ? 'bg-primary/10 text-primary' : 'text-gray-700 hover:bg-gray-100'"
            >
              <div class="flex items-center">
                <span class="text-lg mr-3">{{ item.icon }}</span>
                <span>{{ item.label }}</span>
              </div>
              <span class="text-xs transition-transform" :class="expandedMenus[item.path] ? 'rotate-90' : ''">▶</span>
            </div>

            <!-- 子菜单 -->
            <div v-show="expandedMenus[item.path]" class="ml-6 mt-1 space-y-1">
              <router-link
                v-for="child in item.children"
                :key="child.path"
                :to="child.path"
                class="flex items-center px-4 py-2 rounded-lg transition-colors text-sm"
                :class="isActive(child.path) ? 'bg-primary text-white' : 'text-gray-600 hover:bg-gray-100'"
              >
                <span class="mr-3">{{ child.icon || '•' }}</span>
                <span>{{ child.label }}</span>
              </router-link>
            </div>
          </div>

          <!-- 没有子菜单的项目 -->
          <router-link
            v-else
            :to="item.path"
            class="flex items-center px-4 py-2.5 rounded-lg transition-colors text-sm"
            :class="isActive(item.path) ? 'bg-primary text-white' : 'text-gray-700 hover:bg-gray-100'"
          >
            <span class="text-lg mr-3">{{ item.icon }}</span>
            <span>{{ item.label }}</span>
          </router-link>
        </template>
      </nav>

      <div class="p-3 border-t border-gray-200">
        <div class="flex items-center px-1">
          <div class="w-8 h-8 bg-primary rounded-full flex items-center justify-center text-white text-sm">{{ userInitial }}</div>
          <div class="ml-3">
            <p class="text-sm font-medium text-gray-900">{{ username }}</p>
          </div>
        </div>
      </div>
    </aside>

    <!-- 右侧主体区 -->
    <div class="flex-1 flex flex-col min-w-0">
      <!-- 页面标题区（固定） - 使用命名视图 -->
      <header class="bg-white border-b border-gray-200 px-6 py-4 flex-shrink-0 min-h-[60px] flex items-center">
        <router-view name="header">
          <!-- 默认 header 内容（当路由没有提供 header 组件时显示） -->
          <template #default>
            <div class="flex items-center justify-between w-full">
              <h2 class="text-lg font-semibold text-gray-900">{{ defaultPageTitle }}</h2>
              <div class="flex items-center space-x-4">
                <span class="text-sm text-gray-500">{{ currentTime }}</span>
              </div>
            </div>
          </template>
        </router-view>
      </header>

      <!-- 页面内容区（可滚动） -->
      <main class="flex-1 overflow-auto">
        <router-view />
      </main>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, ref, onMounted, onUnmounted, watch } from 'vue'
import { useRoute } from 'vue-router'

const route = useRoute()

const username = ref('Admin')
const currentTime = ref('')

// 展开的菜单
const expandedMenus = ref<Record<string, boolean>>({
  '/settings': false
})

// 菜单配置
const menuItems = [
  { path: '/', label: '仪表盘', icon: '' },
  { path: '/portfolio', label: '投资组合', icon: '' },
  { path: '/backtest', label: '回测任务', icon: '' },
  { path: '/components', label: '组件管理', icon: '' },
  { path: '/data', label: '数据管理', icon: '' },
  { path: '/alert', label: '警报中心', icon: '' },
  {
    path: '/settings',
    label: '系统设置',
    icon: '',
    children: [
      { path: '/settings/users', label: '用户管理', icon: '' },
      { path: '/settings/user-groups', label: '用户组管理', icon: '' },
      { path: '/settings/notifications', label: '通知管理', icon: '' },
      { path: '/settings/api', label: 'API接口设置', icon: '' }
    ]
  }
]

const userInitial = computed(() => username.value.charAt(0).toUpperCase())

// 判断菜单是否激活（自身或子菜单激活）
const isMenuActive = (item: any) => {
  if (item.children) {
    return item.children.some((child: any) => route.path.startsWith(child.path))
  }
  return route.path.startsWith(item.path)
}

// 判断路径是否激活
const isActive = (path: string) => {
  return route.path === path || route.path.startsWith(path + '/')
}

// 获取默认页面标题（当路由没有提供 header 组件时）
const defaultPageTitle = computed(() => {
  for (const item of menuItems) {
    if (item.children) {
      for (const child of item.children) {
        if (route.path.startsWith(child.path)) {
          return child.label
        }
      }
    } else if (route.path.startsWith(item.path)) {
      return item.label
    }
  }
  return 'Ginkgo'
})

// 切换菜单展开/折叠
const toggleMenu = (path: string) => {
  expandedMenus.value[path] = !expandedMenus.value[path]
}

// 当路由变化时，自动展开包含当前路由的菜单
const autoExpandMenu = () => {
  for (const item of menuItems) {
    if (item.children) {
      const hasActiveChild = item.children.some((child: any) => route.path.startsWith(child.path))
      if (hasActiveChild) {
        expandedMenus.value[item.path] = true
      }
    }
  }
}

const updateTime = () => {
  currentTime.value = new Date().toLocaleString('zh-CN')
}

let timer: ReturnType<typeof setInterval>

onMounted(() => {
  updateTime()
  timer = setInterval(updateTime, 1000)
  autoExpandMenu()
})

onUnmounted(() => {
  clearInterval(timer)
})

// 监听路由变化，自动展开菜单
watch(() => route.path, () => {
  autoExpandMenu()
}, { immediate: true })
</script>
