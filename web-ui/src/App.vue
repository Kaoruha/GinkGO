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
          class="menu-group"
        >
          <div
            v-if="item.type === 'divider'"
            class="menu-divider"
          ></div>
          <template v-else>
            <div
              v-if="item.children && item.children.length > 0"
              class="menu-item has-submenu"
              :class="{ active: openKeys.includes(item.key), selected: selectedKeys.includes(item.key) }"
              :data-testid="`nav-${item.key}`"
              @click="toggleSubMenu(item.key)"
            >
              <div class="menu-item-content">
                <component :is="item.icon" class="menu-icon" :size="16" v-if="item.icon" />
                <span class="menu-label">{{ item.label }}</span>
                <span class="submenu-arrow">{{ openKeys.includes(item.key) ? '▼' : '▶' }}</span>
              </div>
            </div>
            <router-link
              v-else
              :to="getRouteForKey(item.key)"
              class="menu-item"
              :class="{ selected: selectedKeys.includes(item.key) }"
              :data-testid="`nav-${item.key}`"
              @click="handleMenuClick(item.key)"
            >
              <div class="menu-item-content">
                <component :is="item.icon" class="menu-icon" :size="16" v-if="item.icon" />
                <span class="menu-label">{{ item.label }}</span>
              </div>
            </router-link>
            <div
              v-if="item.children && openKeys.includes(item.key)"
              class="submenu"
            >
              <router-link
                v-for="child in item.children"
                :key="child.key"
                :to="getRouteForKey(child.key)"
                class="submenu-item"
                :class="{ selected: selectedKeys.includes(child.key) }"
                :data-testid="`nav-${child.key}`"
                @click="handleMenuClick(child.key)"
              >
                {{ child.label }}
              </router-link>
            </div>
          </template>
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
            <span v-for="(item, index) in breadcrumbs" :key="item.path" class="breadcrumb-item">
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
                {{ authStore.displayName || authStore.username || '用户' }}
              </div>
              <div class="dropdown-divider"></div>
              <button class="dropdown-item" @click="router.push('/system/status'); showUserMenu = false">
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
  LayoutDashboard, Wallet, Rocket, FlaskConical, TrendingUp,
  Zap, Wrench, Database, Code2, BarChart3, FileSearch,
  Bell, User, Settings, LogOut, ChevronDown, ChevronRight,
  type LucideIcon
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
const openKeys = ref<string[]>([])
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
  rocket: Rocket,
  experiment: FlaskConical,
  linechart: TrendingUp,
  lightning: Zap,
  tool: Wrench,
  database: Database,
  function: Code2,
  barchart: BarChart3,
  filesearch: FileSearch,
}

// 菜单定义
interface MenuItem {
  key: string
  label: string
  icon: Component | ''
  type?: 'divider'
  children?: MenuItem[]
}

const menuItems = computed<MenuItem[]>(() => [
  { key: 'dashboard', label: '概览', icon: icons.dashboard },
  { key: 'portfolio', label: '投资组合', icon: icons.wallet },
  {
    key: 'backtest',
    label: '策略回测',
    icon: icons.rocket,
    children: [
      { key: 'backtest-list', label: '回测列表', icon: '' },
      { key: 'backtest-compare', label: '回测对比', icon: '' },
    ],
  },
  {
    key: 'validation',
    label: '样本验证',
    icon: icons.experiment,
    children: [
      { key: 'validation-walkforward', label: '走步验证', icon: '' },
      { key: 'validation-montecarlo', label: '蒙特卡洛', icon: '' },
      { key: 'validation-sensitivity', label: '敏感性分析', icon: '' },
    ],
  },
  {
    key: 'paper',
    label: '模拟交易',
    icon: icons.linechart,
    children: [
      { key: 'paper-trading', label: '模拟监控', icon: '' },
      { key: 'paper-orders', label: '订单记录', icon: '' },
    ],
  },
  {
    key: 'live',
    label: '实盘交易',
    icon: icons.lightning,
    children: [
      { key: 'live-trading', label: '实盘监控', icon: '' },
      { key: 'live-orders', label: '订单管理', icon: '' },
      { key: 'live-positions', label: '持仓管理', icon: '' },
      { key: 'live-market', label: '市场数据', icon: '' },
      { key: 'live-account-config', label: '账号配置', icon: '' },
      { key: 'live-account-info', label: '账户信息', icon: '' },
      { key: 'live-broker-mgmt', label: 'Broker 管理', icon: '' },
      { key: 'live-trade-history', label: '交易历史', icon: '' },
      { key: 'live-trading-control', label: '交易控制', icon: '' },
    ],
  },
  { type: 'divider', key: 'divider1', label: '', icon: '' },
  {
    key: 'research',
    label: '因子研究',
    icon: icons.filesearch,
    children: [
      { key: 'research-ic', label: 'IC 分析', icon: '' },
      { key: 'research-layering', label: '因子分层', icon: '' },
      { key: 'research-orthogonal', label: '因子正交化', icon: '' },
      { key: 'research-comparison', label: '因子比较', icon: '' },
      { key: 'research-decay', label: '因子衰减', icon: '' },
    ],
  },
  {
    key: 'optimization',
    label: '参数优化',
    icon: icons.barchart,
    children: [
      { key: 'optimization-grid', label: '网格搜索', icon: '' },
      { key: 'optimization-genetic', label: '遗传算法', icon: '' },
      { key: 'optimization-bayesian', label: '贝叶斯优化', icon: '' },
    ],
  },
  { type: 'divider', key: 'divider2', label: '', icon: '' },
  {
    key: 'components',
    label: '组件管理',
    icon: icons.function,
    children: [
      { key: 'components-strategies', label: '策略组件', icon: '' },
      { key: 'components-risks', label: '风控组件', icon: '' },
      { key: 'components-sizers', label: '仓位组件', icon: '' },
      { key: 'components-selectors', label: '选股器', icon: '' },
      { key: 'components-analyzers', label: '分析器', icon: '' },
      { key: 'components-handlers', label: '事件处理器', icon: '' },
    ],
  },
  {
    key: 'data',
    label: '数据管理',
    icon: icons.database,
    children: [
      { key: 'data-overview', label: '数据概览', icon: '' },
      { key: 'data-stocks', label: '股票信息', icon: '' },
      { key: 'data-bars', label: 'K线数据', icon: '' },
      { key: 'data-sync', label: '数据同步', icon: '' },
    ],
  },
  {
    key: 'system',
    label: '系统管理',
    icon: icons.tool,
    children: [
      { key: 'system-status', label: '系统状态', icon: '' },
      { key: 'system-workers', label: 'Worker 管理', icon: '' },
      { key: 'system-api-keys', label: 'API Key 管理', icon: '' },
      { key: 'system-users', label: '用户管理', icon: '' },
      { key: 'system-groups', label: '用户组管理', icon: '' },
      { key: 'system-notifications', label: '通知管理', icon: '' },
      { key: 'system-alerts', label: '告警中心', icon: '' },
    ],
  },
])

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
  '/portfolio': 'portfolio',
  '/portfolio/create': 'portfolio',
  '/backtest': 'backtest-list',
  '/backtest/create': 'backtest-list',
  '/backtest/compare': 'backtest-compare',
  '/validation/walkforward': 'validation-walkforward',
  '/validation/montecarlo': 'validation-montecarlo',
  '/validation/sensitivity': 'validation-sensitivity',
  '/paper': 'paper-trading',
  '/paper/orders': 'paper-orders',
  '/live': 'live-trading',
  '/live/orders': 'live-orders',
  '/live/positions': 'live-positions',
  '/live/account-config': 'live-account-config',
  '/live/account-info': 'live-account-info',
  '/live/broker-management': 'live-broker-mgmt',
  '/live/trade-history': 'live-trade-history',
  '/live/trading-control': 'live-trading-control',
  '/live/market': 'live-market',
  '/research/ic': 'research-ic',
  '/research/layering': 'research-layering',
  '/research/orthogonal': 'research-orthogonal',
  '/research/comparison': 'research-comparison',
  '/research/decay': 'research-decay',
  '/optimization/grid': 'optimization-grid',
  '/optimization/genetic': 'optimization-genetic',
  '/optimization/bayesian': 'optimization-bayesian',
  '/components/strategies': 'components-strategies',
  '/components/risks': 'components-risks',
  '/components/sizers': 'components-sizers',
  '/components/selectors': 'components-selectors',
  '/components/analyzers': 'components-analyzers',
  '/components/handlers': 'components-handlers',
  '/data': 'data-overview',
  '/data/stocks': 'data-stocks',
  '/data/bars': 'data-bars',
  '/data/sync': 'data-sync',
  '/system/status': 'system-status',
  '/system/workers': 'system-workers',
  '/system/api-keys': 'system-api-keys',
  '/system/users': 'system-users',
  '/system/groups': 'system-groups',
  '/system/notifications': 'system-notifications',
  '/system/alerts': 'system-alerts',
}

// 子菜单 key 到父菜单 key 的映射
const keyToParentMap: Record<string, string> = {
  'backtest-list': 'backtest',
  'backtest-compare': 'backtest',
  'validation-walkforward': 'validation',
  'validation-montecarlo': 'validation',
  'validation-sensitivity': 'validation',
  'paper-trading': 'paper',
  'paper-orders': 'paper',
  'live-trading': 'live',
  'live-orders': 'live',
  'live-positions': 'live',
  'live-account-config': 'live',
  'live-account-info': 'live',
  'live-broker-mgmt': 'live',
  'live-trade-history': 'live',
  'live-trading-control': 'live',
  'research-ic': 'research',
  'research-layering': 'research',
  'research-orthogonal': 'research',
  'research-comparison': 'research',
  'research-decay': 'research',
  'optimization-grid': 'optimization',
  'optimization-genetic': 'optimization',
  'optimization-bayesian': 'optimization',
  'components-strategies': 'components',
  'components-risks': 'components',
  'components-sizers': 'components',
  'components-selectors': 'components',
  'components-analyzers': 'components',
  'components-handlers': 'components',
  'data-overview': 'data',
  'data-stocks': 'data',
  'data-bars': 'data',
  'data-sync': 'data',
  'system-status': 'system',
  'system-workers': 'system',
  'system-users': 'system',
  'system-groups': 'system',
  'system-notifications': 'system',
  'system-alerts': 'system',
}

// 监听路由变化，更新菜单选中状态
watch(() => route.path, (path) => {
  // 精确匹配
  let key = routeToKeyMap[path]

  // 如果没有精确匹配，尝试模式匹配（处理动态路由如 /portfolio/:id）
  if (!key) {
    // Portfolio 相关路由
    if (path.startsWith('/portfolio/') && path !== '/portfolio/create') {
      key = 'portfolio'
    }
    // Backtest 详情路由
    else if (path.match(/^\/backtest\/[^/]+$/) && path !== '/backtest/create' && path !== '/backtest/compare') {
      key = 'backtest-list'
    }
    // 组件详情路由 (如 /components/strategies/abc123)
    else if (path.match(/^\/components\/(strategies|risks|sizers|selectors|analyzers|handlers)\/[^/]+$/)) {
      const segments = path.split('/')
      const type = segments[2] || ''  // 'strategies'
      key = `components-${type.slice(0, -1)}` // strategies -> components-strategies
    }
  }

  if (key) {
    selectedKeys.value = [key]
    // 同时展开父菜单
    const parentKey = keyToParentMap[key]
    if (parentKey && !openKeys.value.includes(parentKey)) {
      openKeys.value = [...openKeys.value, parentKey]
    }
  }
}, { immediate: true })

const breadcrumbs = computed(() => {
  const matched = route.matched.filter(r => r.meta?.title)
  return matched.map(r => ({
    path: r.path,
    title: r.meta?.title as string,
  }))
})

// 切换子菜单展开/收起
const toggleSubMenu = (key: string) => {
  const index = openKeys.value.indexOf(key)
  if (index > -1) {
    openKeys.value = openKeys.value.filter(k => k !== key)
  } else {
    openKeys.value = [...openKeys.value, key]
  }
}

// 菜单 key 到路由的映射
const getRouteForKey = (key: string): string => {
  const routeMap: Record<string, string> = {
    'dashboard': '/dashboard',
    'portfolio': '/portfolio',
    'backtest-list': '/backtest',
    'backtest-compare': '/backtest/compare',
    'validation-walkforward': '/validation/walkforward',
    'validation-montecarlo': '/validation/montecarlo',
    'validation-sensitivity': '/validation/sensitivity',
    'paper-trading': '/paper',
    'paper-orders': '/paper/orders',
    'live-trading': '/live',
    'live-orders': '/live/orders',
    'live-positions': '/live/positions',
    'live-market': '/live/market',
    'live-api-keys': '/system/api-keys',
    'live-account-config': '/live/account-config',
    'live-account-info': '/live/account-info',
    'live-broker-mgmt': '/live/broker-management',
    'live-trade-history': '/live/trade-history',
    'live-trading-control': '/live/trading-control',
    'research-ic': '/research/ic',
    'research-layering': '/research/layering',
    'research-orthogonal': '/research/orthogonal',
    'research-comparison': '/research/comparison',
    'research-decay': '/research/decay',
    'optimization-grid': '/optimization/grid',
    'optimization-genetic': '/optimization/genetic',
    'optimization-bayesian': '/optimization/bayesian',
    'components-strategies': '/components/strategies',
    'components-risks': '/components/risks',
    'components-sizers': '/components/sizers',
    'components-selectors': '/components/selectors',
    'components-analyzers': '/components/analyzers',
    'components-handlers': '/components/handlers',
    'data-overview': '/data',
    'data-stocks': '/data/stocks',
    'data-bars': '/data/bars',
    'data-sync': '/data/sync',
    'system-status': '/system/status',
    'system-workers': '/system/workers',
    'system-api-keys': '/system/api-keys',
    'system-users': '/system/users',
    'system-groups': '/system/groups',
    'system-notifications': '/system/notifications',
    'system-alerts': '/system/alerts',
  }
  return routeMap[key] || '/'
}

const handleMenuClick = (key: string) => {
  const routePath = getRouteForKey(key)
  if (routePath && routePath !== route.path) {
    router.push(routePath)
  }
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

.menu-group {
  margin-bottom: 4px;
}

.menu-divider {
  height: 1px;
  background: #2a2a3e;
  margin: 8px 12px;
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

.sider.collapsed .menu-label,
.sider.collapsed .submenu-arrow {
  display: none;
}

.submenu-arrow {
  margin-left: auto;
  font-size: 10px;
  transition: transform 0.2s;
}

.menu-item.active .submenu-arrow {
  transform: rotate(90deg);
}

.submenu {
  background: #141422;
}

.submenu-item {
  display: block;
  padding: 8px 16px 8px 42px;
  color: #8a8a9a;
  font-size: 13px;
  cursor: pointer;
  transition: all 0.2s;
  text-decoration: none;
}

.submenu-item:hover {
  background: #2a2a3e;
  color: #ffffff;
}

.submenu-item.selected {
  background: rgba(24, 144, 255, 0.1);
  color: #1890ff;
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
