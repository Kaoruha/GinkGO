<template>
  <!-- 登录页等全屏页面 -->
  <div v-if="isFullPage" class="full-page">
    <router-view />
  </div>

  <!-- 带布局的主页面（需要登录） -->
  <div v-else-if="authStore.isLoggedIn" class="app-layout">
    <!-- 侧边栏 -->
    <div class="sider" :class="{ collapsed }">
      <div class="logo">
        <img src="/favicon.svg" alt="Ginkgo" />
        <span v-if="!collapsed">Ginkgo</span>
      </div>
      <nav class="menu">
        <div
          v-for="item in menuItems"
          :key="item.key"
        >
          <router-link
            :to="getRouteForKey(item.key)"
            class="menu-item"
            :class="{ selected: selectedKeys.includes(item.key) }"
            :data-testid="`nav-${item.key}`"
            @click="selectedKeys = [item.key]"
          >
            <div class="menu-item-content">
              <component :is="item.icon" class="menu-icon" :size="16" v-if="item.icon" />
              <span class="menu-label">{{ item.label }}</span>
            </div>
          </router-link>
        </div>
      </nav>
    </div>

    <!-- 主内容区 -->
    <div class="main">
      <!-- 头部 -->
      <header class="header">
        <div class="header-left">
          <button
            class="trigger"
            @click="collapsed = !collapsed"
          >
            <svg v-if="collapsed" xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <rect x="3" y="3" width="18" height="18" rx="2" ry="2"></rect>
              <line x1="9" y1="3" x2="9" y2="21"></line>
            </svg>
            <svg v-else xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <rect x="3" y="3" width="18" height="18" rx="2" ry="2"></rect>
              <line x1="15" y1="3" x2="15" y2="21"></line>
            </svg>
          </button>
          <nav class="breadcrumb">
            <span v-for="item in breadcrumbs" :key="item.path" class="breadcrumb-item">
              {{ item.title }}
            </span>
          </nav>
        </div>
        <div class="header-right">
          <button
            class="notification-btn"
            @click="showNotifications"
          >
            <span class="notification-badge" :class="{ 'has-count': notificationCount > 0 }">
              <svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <path d="M18 8A6 6 0 0 0 6 8c0 7-3 9-3 9h18s-3-2-3-9"></path>
                <path d="M13.73 21a2 2 0 0 1-3.46 0"></path>
              </svg>
              <span v-if="notificationCount > 0" class="count">{{ notificationCount }}</span>
            </span>
          </button>
          <div class="user-dropdown">
            <button class="avatar-btn" data-testid="user-menu-btn" @click="toggleUserMenu">
              <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                  <path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2"></path>
                  <circle cx="12" cy="7" r="4"></circle>
              </svg>
            </button>
            <div class="dropdown-menu" :class="{ show: showUserMenu }">
              <div class="dropdown-item user-info">
                <svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                  <path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2"></path>
                  <circle cx="12" cy="7" r="4"></circle>
                </svg>
                {{ authStore.displayName || '用户' }}
              </div>
              <div class="dropdown-divider"></div>
              <button class="dropdown-item" @click="router.push('/admin'); showUserMenu = false">
                <svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                  <circle cx="12" cy="12" r="3"></circle>
                  <path d="M12 1v6m0 6v6"></path>
                  <path d="m19 21-7-5 7-5"></path>
                </svg>
                系统设置
              </button>
              <button class="dropdown-item text-danger" data-testid="logout-btn" @click="handleLogout">
                <svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                  <path d="M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4"></path>
                  <polyline points="16 17 21 12 16 7"></polyline>
                  <line x1="21" y1="12" x2="9" y2="12"></line>
                </svg>
                退出登录
              </button>
            </div>
          </div>
        </div>
      </header>

      <!-- 内容区 -->
      <main class="content" :class="{ 'content-fullscreen': isEditorPage }">
        <router-view />
      </main>
    </div>
  </div>

  <!-- Fallback - 让路由守卫处理重定向 -->
  <router-view v-else />
</template>

<script setup lang="ts">
import { ref, computed, watch, onMounted, onUnmounted, type Component } from 'vue'
import {
  LayoutDashboard, Wallet, TrendingUp,
  Wrench, Database, FileSearch, Puzzle,
} from 'lucide-vue-next'
import { useRouter, useRoute } from 'vue-router'
import { useAuthStore } from '@/stores/auth'

// 简化的通知函数
const showToast = (message: string, type: 'success' | 'error' | 'info' | 'warning' = 'success') => {
  console.log(`[${type.toUpperCase()}] ${message}`)
}

const router = useRouter()
const route = useRoute()
const authStore = useAuthStore()

const collapsed = ref(false)
const selectedKeys = ref<string[]>(['dashboard'])
const notificationCount = ref(0)
const showUserMenu = ref(false)  // 用户下拉菜单显示状态

// 切换用户菜单
const toggleUserMenu = () => {
  showUserMenu.value = !showUserMenu.value
}

// 点击外部关闭用户菜单
const handleClickOutside = (event: MouseEvent) => {
  const dropdown = document.querySelector('.user-dropdown')
  if (dropdown && !dropdown.contains(event.target as Node)) {
    showUserMenu.value = false
  }
}

// 监听点击外部
onMounted(() => {
  document.addEventListener('click', handleClickOutside)
})

onUnmounted(() => {
  document.removeEventListener('click', handleClickOutside)
})

// 图标组件映射
const icons: Record<string, Component> = {
  dashboard: LayoutDashboard,
  wallet: Wallet,
  filesearch: FileSearch,
  linechart: TrendingUp,
  database: Database,
  tool: Wrench,
  puzzle: Puzzle,
}

// 菜单定义
interface MenuItem {
  key: string
  label: string
  icon: Component | ''
}

const menuItems: MenuItem[] = [
  { key: 'dashboard', label: '工作台', icon: icons.dashboard },
  { key: 'portfolios', label: '组合', icon: icons.wallet },
  { key: 'backtests', label: '回测', icon: icons.linechart },
  { key: 'validation', label: '验证', icon: icons.filesearch },
  { key: 'components', label: '组件', icon: icons.puzzle },
  { key: 'research', label: '研究', icon: icons.filesearch },
  { key: 'trading', label: '交易', icon: icons.linechart },
  { key: 'data', label: '数据', icon: icons.database },
  { key: 'admin', label: '管理', icon: icons.tool },
]

// 全屏页面（不需要侧边栏布局）
const isFullPage = computed(() => {
  const fullPageRoutes = ['/login', '/404']
  return fullPageRoutes.includes(route.path) || route.meta?.fullPage === true
})

// 编辑器详情页（需要全屏 content）
const isEditorPage = computed(() => {
  return route.path.match(/\/components\/(strategies|risks|sizers|selectors|analyzers|handlers)\/[a-f0-9-]+/)
})

// 路由路径到菜单 key 的映射
const routeToKeyMap: Record<string, string> = {
  '/dashboard': 'dashboard',
  '/portfolios': 'portfolios',
  '/backtests': 'backtests',
  '/validation': 'validation',
  '/components': 'components',
  '/research': 'research',
  '/trading': 'trading',
  '/data': 'data',
  '/admin': 'admin',
}

// 监听路由变化，更新菜单选中状态
watch(() => route.path, (path) => {
  let key = routeToKeyMap[path]
  if (!key) {
    if (path.startsWith('/backtests')) {
      key = 'backtests'
    } else if (path.startsWith('/validation')) {
      key = 'validation'
    } else if (path.startsWith('/portfolios/')) {
      key = 'portfolios'
    } else if (path.startsWith('/components/')) {
      key = 'components'
    } else if (path.startsWith('/research/')) {
      key = 'research'
    } else if (path.startsWith('/trading/')) {
      key = 'trading'
    } else if (path.startsWith('/admin/')) {
      key = 'admin'
    }
  }
  if (key) {
    selectedKeys.value = [key]
  }
})

const breadcrumbs = computed(() => {
  const matched = route.matched.filter(r => r.meta?.title)
  return matched.map(r => ({
    path: r.path,
    title: r.meta?.title as string,
  }))
})

// 菜单 key 到路由的映射
const getRouteForKey = (key: string): string => {
  const routeMap: Record<string, string> = {
    'dashboard': '/dashboard',
    'portfolios': '/portfolios',
    'backtests': '/backtests',
    'validation': '/validation',
    'components': '/components',
    'research': '/research',
    'trading': '/trading',
    'data': '/data',
    'admin': '/admin',
  }
  return routeMap[key] || '/'
}

const showNotifications = () => {
  // TODO: 显示通知面板
}

const handleLogout = async () => {
  await authStore.logout()
  showToast('已退出登录')
  router.push('/login')
}
</script>

<style scoped>
.app-layout {
  height: 100vh;
  overflow: hidden;
  background: #0f0f1a;
  display: flex;
}

/* Sider */
.sider {
  width: 220px;
  background: #1a1a2e;
  border-right: 1px solid #2a2a3e;
  display: flex;
  flex-direction: column;
  transition: width 0.2s;
  flex-shrink: 0;
}

.sider.collapsed {
  width: 64px;
}

.logo {
  height: 64px;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  font-size: 18px;
  font-weight: bold;
  color: #1890ff;
  border-bottom: 1px solid #2a2a3e;
}

.logo img {
  width: 32px;
  height: 32px;
}

.logo span {
  white-space: nowrap;
}

.sider.collapsed .logo span {
  display: none;
}

/* Menu */
.menu {
  flex: 1;
  overflow-y: auto;
  padding: 8px 0;
}

.menu-item {
  display: flex;
  align-items: center;
  padding: 10px 16px;
  color: #8a8a9a;
  cursor: pointer;
  transition: all 0.2s;
  text-decoration: none;
  position: relative;
}

.menu-item:hover {
  background: #2a2a3e;
  color: #ffffff;
}

.menu-item.selected {
  background: rgba(24, 144, 255, 0.1);
  color: #1890ff;
}

.menu-item-content {
  display: flex;
  align-items: center;
  gap: 10px;
  flex: 1;
}

.menu-icon {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 16px;
  height: 16px;
  flex-shrink: 0;
}

.menu-icon :deep(svg) {
  width: 16px;
  height: 16px;
}

.menu-label {
  font-size: 14px;
  white-space: nowrap;
}

.sider.collapsed .menu-label {
  display: none;
}

/* Main */
.main {
  flex: 1;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

/* Header */
.header {
  height: 64px;
  background: #1a1a2e;
  border-bottom: 1px solid #2a2a3e;
  padding: 0 24px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  flex-shrink: 0;
}

.header-left {
  display: flex;
  align-items: center;
  gap: 16px;
}

.trigger {
  width: 36px;
  height: 36px;
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  color: #8a8a9a;
  border-radius: 4px;
  transition: all 0.2s;
}

.trigger:hover {
  background: #2a2a3e;
  color: #1890ff;
}

.breadcrumb {
  display: flex;
  gap: 8px;
  font-size: 14px;
  color: #8a8a9a;
}

.breadcrumb-item:not(:last-child)::after {
  content: '/';
  margin-left: 8px;
  color: #3a3a4e;
}

.header-right {
  display: flex;
  align-items: center;
  gap: 24px;
}

.notification-btn {
  background: none;
  border: none;
  padding: 0;
  cursor: pointer;
  color: #8a8a9a;
}

.notification-badge {
  position: relative;
  display: block;
}

.notification-badge .count {
  position: absolute;
  top: -4px;
  right: -4px;
  min-width: 16px;
  height: 16px;
  padding: 0 4px;
  background: #f5222d;
  color: #ffffff;
  font-size: 10px;
  line-height: 16px;
  text-align: center;
  border-radius: 8px;
}

.avatar-btn {
  width: 32px;
  height: 32px;
  background: #1890ff;
  border: none;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  color: #ffffff;
}

.user-dropdown {
  position: relative;
}

.dropdown-menu {
  position: absolute;
  top: 100%;
  right: 0;
  margin-top: 8px;
  background: #1a1a2e;
  border: 1px solid #2a2a3e;
  border-radius: 6px;
  min-width: 160px;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.3);
  display: none;
  z-index: 100;
}

.dropdown-menu.show {
  display: block;
}

.dropdown-item {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 10px 16px;
  color: #ffffff;
  font-size: 13px;
  background: none;
  border: none;
  width: 100%;
  text-align: left;
  cursor: pointer;
  transition: background 0.2s;
}

.dropdown-item:hover {
  background: #2a2a3e;
}

.dropdown-item.user-info {
  cursor: default;
}

.dropdown-item.text-danger {
  color: #f5222d;
}

.dropdown-divider {
  height: 1px;
  background: #2a2a3e;
  margin: 4px 0;
}

/* Content */
.content {
  padding: 24px;
  background: #0f0f1a;
  flex: 1;
  overflow-y: auto;
  overflow-x: hidden;
}

.content-fullscreen {
  padding: 0;
  overflow: hidden;
}
</style>
