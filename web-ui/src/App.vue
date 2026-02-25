<template>
<<<<<<< HEAD
  <router-view />
</template>

<script setup lang="ts">
</script>

<style>
* {
  margin: 0;
  padding: 0;
  box-sizing: border-box;
}

body {
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;
  -webkit-font-smoothing: antialiased;
  -moz-osx-font-smoothing: grayscale;
}

#app {
  width: 100%;
  height: 100vh;
=======
  <a-config-provider :locale="zhCN">
    <!-- 登录页等全屏页面 -->
    <template v-if="isFullPage">
      <router-view />
    </template>

    <!-- 带布局的主页面（需要登录） -->
    <template v-else-if="authStore.isLoggedIn">
      <a-layout class="app-layout">
        <a-layout-sider
          v-model:collapsed="collapsed"
          :trigger="null"
          collapsible
          theme="light"
          width="220"
        >
          <div class="logo">
            <img src="/favicon.svg" alt="Ginkgo" />
            <span v-if="!collapsed">Ginkgo</span>
          </div>
          <a-menu
            v-model:selectedKeys="selectedKeys"
            v-model:openKeys="openKeys"
            mode="inline"
            :items="menuItems"
            @click="handleMenuClick"
          />
        </a-layout-sider>
        <a-layout>
          <a-layout-header class="header">
            <div class="header-left">
              <menu-unfold-outlined
                v-if="collapsed"
                class="trigger"
                @click="collapsed = !collapsed"
              />
              <menu-fold-outlined
                v-else
                class="trigger"
                @click="collapsed = !collapsed"
              />
              <a-breadcrumb class="breadcrumb">
                <a-breadcrumb-item v-for="item in breadcrumbs" :key="item.path">
                  {{ item.title }}
                </a-breadcrumb-item>
              </a-breadcrumb>
            </div>
            <div class="header-right">
              <a-badge :count="notificationCount" class="notification-badge">
                <bell-outlined @click="showNotifications" />
              </a-badge>
              <a-dropdown>
                <a-avatar style="background-color: #1890ff">
                  <template #icon><UserOutlined /></template>
                </a-avatar>
                <template #overlay>
                  <a-menu @click="handleUserMenuClick">
                    <a-menu-item key="profile">
                      <UserOutlined /> {{ authStore.displayName }}
                    </a-menu-item>
                    <a-menu-divider />
                    <a-menu-item key="settings">
                      <SettingOutlined /> 系统设置
                    </a-menu-item>
                    <a-menu-item key="logout">
                      <LogoutOutlined /> 退出登录
                    </a-menu-item>
                  </a-menu>
                </template>
              </a-dropdown>
            </div>
          </a-layout-header>
          <a-layout-content class="content" :class="{ 'content-fullscreen': isEditorPage }">
            <router-view />
          </a-layout-content>
        </a-layout>
      </a-layout>
    </template>

    <!-- Fallback - 让路由守卫处理重定向 -->
    <router-view v-else />
  </a-config-provider>
</template>

<script setup lang="ts">
import { ref, computed, h, watch } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import zhCN from 'ant-design-vue/es/locale/zh_CN'
import { message } from 'ant-design-vue'
import { useAuthStore } from '@/stores/auth'
import {
  MenuFoldOutlined,
  MenuUnfoldOutlined,
  UserOutlined,
  BellOutlined,
  SettingOutlined,
  LogoutOutlined,
  RocketOutlined,
  LineChartOutlined,
  ExperimentOutlined,
  ThunderboltOutlined,
  ToolOutlined,
  DatabaseOutlined,
  FunctionOutlined,
  BarChartOutlined,
  FileSearchOutlined,
  DashboardOutlined,
  WalletOutlined,
} from '@ant-design/icons-vue'
import type { MenuProps } from 'ant-design-vue'

const router = useRouter()
const route = useRoute()
const authStore = useAuthStore()

const collapsed = ref(false)
const selectedKeys = ref<string[]>(['dashboard'])
const openKeys = ref<string[]>([])
const notificationCount = ref(0)

// 全屏页面（不需要侧边栏布局）
const isFullPage = computed(() => {
  const fullPageRoutes = ['/login', '/404']
  return fullPageRoutes.includes(route.path) || route.meta?.fullPage === true
})

// 编辑器详情页（需要全屏 content）
const isEditorPage = computed(() => {
  // 组件管理详情页使用全屏布局
  return route.path.match(/\/components\/(strategies|risks|sizers|selectors|analyzers|handlers)\/[a-f0-9-]+/)
})

// 4阶段策略生命周期菜单
const menuItems = computed<MenuProps['items']>(() => [
  {
    key: 'dashboard',
    icon: () => h(DashboardOutlined),
    label: '概览',
    title: 'Dashboard',
  },
  {
    key: 'portfolio',
    icon: () => h(WalletOutlined),
    label: '投资组合',
    title: '投资组合管理',
  },
  {
    key: 'backtest',
    icon: () => h(RocketOutlined),
    label: '策略回测',
    title: '策略回测验证',
    children: [
      { key: 'backtest-list', label: '回测列表' },
      { key: 'backtest-compare', label: '回测对比' },
    ],
  },
  {
    key: 'validation',
    icon: () => h(ExperimentOutlined),
    label: '样本验证',
    title: '样本外验证',
    children: [
      { key: 'validation-walkforward', label: '走步验证' },
      { key: 'validation-montecarlo', label: '蒙特卡洛' },
      { key: 'validation-sensitivity', label: '敏感性分析' },
    ],
  },
  {
    key: 'paper',
    icon: () => h(LineChartOutlined),
    label: '模拟交易',
    title: 'Paper Trading',
    children: [
      { key: 'paper-trading', label: '模拟监控' },
      { key: 'paper-orders', label: '订单记录' },
    ],
  },
  {
    key: 'live',
    icon: () => h(ThunderboltOutlined),
    label: '实盘交易',
    title: '实盘交易',
    children: [
      { key: 'live-trading', label: '实盘监控' },
      { key: 'live-orders', label: '订单管理' },
      { key: 'live-positions', label: '持仓管理' },
    ],
  },
  {
    type: 'divider',
  },
  {
    key: 'research',
    icon: () => h(FileSearchOutlined),
    label: '因子研究',
    children: [
      { key: 'research-ic', label: 'IC 分析' },
      { key: 'research-layering', label: '因子分层' },
      { key: 'research-orthogonal', label: '因子正交化' },
      { key: 'research-comparison', label: '因子比较' },
      { key: 'research-decay', label: '因子衰减' },
    ],
  },
  {
    key: 'optimization',
    icon: () => h(BarChartOutlined),
    label: '参数优化',
    children: [
      { key: 'optimization-grid', label: '网格搜索' },
      { key: 'optimization-genetic', label: '遗传算法' },
      { key: 'optimization-bayesian', label: '贝叶斯优化' },
    ],
  },
  {
    type: 'divider',
  },
  {
    key: 'components',
    icon: () => h(FunctionOutlined),
    label: '组件管理',
    children: [
      { key: 'components-strategies', label: '策略组件' },
      { key: 'components-risks', label: '风控组件' },
      { key: 'components-sizers', label: '仓位组件' },
      { key: 'components-selectors', label: '选股器' },
      { key: 'components-analyzers', label: '分析器' },
      { key: 'components-handlers', label: '事件处理器' },
    ],
  },
  {
    key: 'data',
    icon: () => h(DatabaseOutlined),
    label: '数据管理',
    children: [
      { key: 'data-overview', label: '数据概览' },
      { key: 'data-stocks', label: '股票信息' },
      { key: 'data-bars', label: 'K线数据' },
      { key: 'data-sync', label: '数据同步' },
    ],
  },
  {
    key: 'system',
    icon: () => h(ToolOutlined),
    label: '系统管理',
    children: [
      { key: 'system-status', label: '系统状态' },
      { key: 'system-workers', label: 'Worker 管理' },
      { key: 'system-users', label: '用户管理' },
      { key: 'system-groups', label: '用户组管理' },
      { key: 'system-notifications', label: '通知管理' },
      { key: 'system-alerts', label: '告警中心' },
    ],
  },
])

// 路由路径到菜单 key 的映射
const routeToKeyMap: Record<string, string> = {
  '/dashboard': 'dashboard',
  '/portfolio': 'portfolio',
  '/portfolio/create': 'portfolio',
  '/stage1/backtest': 'backtest-list',
  '/stage1/backtest/create': 'backtest-list',
  '/stage1/backtest/compare': 'backtest-compare',
  '/stage2/walkforward': 'validation-walkforward',
  '/stage2/montecarlo': 'validation-montecarlo',
  '/stage2/sensitivity': 'validation-sensitivity',
  '/stage3/paper': 'paper-trading',
  '/stage3/paper/orders': 'paper-orders',
  '/stage4/live': 'live-trading',
  '/stage4/live/orders': 'live-orders',
  '/stage4/live/positions': 'live-positions',
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
  const key = routeToKeyMap[path]
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

const handleMenuClick: MenuProps['onClick'] = ({ key }) => {
  const keyPath = key as string
  // 将菜单 key 转换为路由路径
  const routeMap: Record<string, string> = {
    'dashboard': '/dashboard',
    'portfolio': '/portfolio',
    'backtest-list': '/stage1/backtest',
    'backtest-compare': '/stage1/backtest/compare',
    'validation-walkforward': '/stage2/walkforward',
    'validation-montecarlo': '/stage2/montecarlo',
    'validation-sensitivity': '/stage2/sensitivity',
    'paper-trading': '/stage3/paper',
    'paper-orders': '/stage3/paper/orders',
    'live-trading': '/stage4/live',
    'live-orders': '/stage4/live/orders',
    'live-positions': '/stage4/live/positions',
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
    'system-users': '/system/users',
    'system-groups': '/system/groups',
    'system-notifications': '/system/notifications',
    'system-alerts': '/system/alerts',
  }

  if (routeMap[keyPath]) {
    router.push(routeMap[keyPath])
  }
}

const showNotifications = () => {
  // TODO: 显示通知面板
}

const handleUserMenuClick = async ({ key }: { key: string }) => {
  if (key === 'logout') {
    await authStore.logout()
    message.success('已退出登录')
    router.push('/login')
  } else if (key === 'settings') {
    router.push('/system/status')
  }
}
</script>

<style lang="less" scoped>
.init-loading {
  min-height: 100vh;
  display: flex;
  align-items: center;
  justify-content: center;
  background: #f0f2f5;
}

.app-layout {
  height: 100vh;
  overflow: hidden;
  background: #f0f2f5;
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
  border-bottom: 1px solid #f0f0f0;

  img {
    width: 32px;
    height: 32px;
  }
}

.header {
  background: #fff;
  padding: 0 24px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  box-shadow: 0 1px 4px rgba(0, 21, 41, 0.08);

  .header-left {
    display: flex;
    align-items: center;
    gap: 16px;

    .trigger {
      font-size: 18px;
      cursor: pointer;
      transition: color 0.3s;

      &:hover {
        color: #1890ff;
      }
    }

    .breadcrumb {
      margin-left: 8px;
    }
  }

  .header-right {
    display: flex;
    align-items: center;
    gap: 24px;

    .notification-badge {
      cursor: pointer;

      :deep(.anticon) {
        font-size: 18px;
      }
    }

    .ant-avatar {
      cursor: pointer;
    }
  }
}

.content {
  padding: 24px;
  background: #fff;
  flex: 1;
  overflow-y: auto;
  overflow-x: hidden;
}

.content-fullscreen {
  padding: 0;
  background: #1e1e1e;
  border-radius: 8px;
  flex: 1;
}

:deep(.ant-menu) {
  border-right: none !important;
}

:deep(.ant-layout-sider) {
  box-shadow: 2px 0 8px rgba(0, 21, 41, 0.05);
  height: 100vh;
  overflow-y: auto;
}

:deep(.ant-layout) {
  height: 100%;
}

:deep(.ant-layout) {
  height: 100%;
>>>>>>> 011-quant-research
}
</style>
