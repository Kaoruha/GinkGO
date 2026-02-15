<template>
  <div class="h-screen flex bg-gray-50">
    <!-- 左侧导航栏 -->
    <aside class="w-64 bg-white border-r border-gray-200 flex flex-col flex-shrink-0">
      <div class="h-14 flex items-center px-6 border-b border-gray-200">
        <h1 class="text-xl font-bold text-primary">
          Ginkgo
        </h1>
      </div>

      <nav class="flex-1 p-3 space-y-1 overflow-y-auto">
        <template
          v-for="item in menuItems"
          :key="item.path"
        >
          <!-- 有子菜单的项目 -->
          <div v-if="item.children">
            <div
              class="flex items-center justify-between px-4 py-2.5 rounded-lg cursor-pointer transition-colors text-sm"
              :class="isMenuActive(item) ? 'bg-primary/10 text-primary' : 'text-gray-700 hover:bg-gray-100'"
              @click="toggleMenu(item.path)"
            >
              <div class="flex items-center">
                <span class="text-lg mr-3">{{ item.icon }}</span>
                <span>{{ item.label }}</span>
              </div>
              <span
                class="text-xs transition-transform"
                :class="expandedMenus[item.path] ? 'rotate-90' : ''"
              >▶</span>
            </div>

            <!-- 子菜单 -->
            <div
              v-show="expandedMenus[item.path]"
              class="ml-6 mt-1 space-y-1"
            >
              <router-link
                v-for="child in item.children"
                :key="child.path"
                :to="child.path"
                class="flex items-center justify-between px-4 py-2 rounded-lg transition-colors text-sm"
                :class="isActive(child.path) ? 'bg-primary text-white' : 'text-gray-600 hover:bg-gray-100'"
              >
                <div class="flex items-center">
                  <span class="mr-3">{{ child.icon || '•' }}</span>
                  <span>{{ child.label }}</span>
                </div>
                <a-tag v-if="child.status" :color="getStatusColor(child.status)" size="small">
                  {{ getStatusLabel(child.status) }}
                </a-tag>
              </router-link>
            </div>
          </div>

          <!-- 没有子菜单的项目 -->
          <router-link
            v-else
            :to="item.path"
            class="flex items-center justify-between px-4 py-2.5 rounded-lg transition-colors text-sm"
            :class="isActive(item.path) ? 'bg-primary text-white' : 'text-gray-700 hover:bg-gray-100'"
          >
            <div class="flex items-center">
              <span class="text-lg mr-3">{{ item.icon }}</span>
              <span>{{ item.label }}</span>
            </div>
            <a-tag v-if="item.status" :color="getStatusColor(item.status)" size="small">
              {{ getStatusLabel(item.status) }}
            </a-tag>
          </router-link>
        </template>
      </nav>

      <div class="p-3 border-t border-gray-200">
        <div class="flex items-center px-1">
          <div class="w-8 h-8 bg-primary rounded-full flex items-center justify-center text-white text-sm">
            {{ userInitial }}
          </div>
          <div class="ml-3">
            <p class="text-sm font-medium text-gray-900">
              {{ username }}
            </p>
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
              <h2 class="text-lg font-semibold text-gray-900">
                {{ defaultPageTitle }}
              </h2>
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

// 功能状态类型
type MenuItemStatus = 'done' | 'pending-api' | 'todo'

// 菜单配置（含状态标记）- 仅后端API已实现的模块标记为完成
const menuItems = [
  { path: '/', label: '仪表盘', icon: '', status: 'pending-api' as MenuItemStatus },
  { path: '/portfolio', label: '投资组合', icon: '', status: 'done' as MenuItemStatus },
  {
    path: '/backtest',
    label: '回测任务',
    icon: '',
    children: [
      { path: '/backtest', label: '回测列表', icon: '', status: 'done' as MenuItemStatus },
      { path: '/backtest/compare', label: '回测对比', icon: '', status: 'done' as MenuItemStatus }
    ]
  },
  {
    path: '/research',
    label: '量化研究',
    icon: '',
    children: [
      { path: '/research', label: '因子查看', icon: '', status: 'pending-api' as MenuItemStatus },
      { path: '/research/ic-analysis', label: 'IC分析', icon: '', status: 'pending-api' as MenuItemStatus },
      { path: '/research/layering', label: '分层回测', icon: '', status: 'pending-api' as MenuItemStatus },
      { path: '/research/comparison', label: '因子对比', icon: '', status: 'pending-api' as MenuItemStatus },
      { path: '/research/orthogonalization', label: '因子正交化', icon: '', status: 'pending-api' as MenuItemStatus },
      { path: '/research/decay', label: '因子衰减', icon: '', status: 'pending-api' as MenuItemStatus },
      { path: '/research/turnover', label: '换手率分析', icon: '', status: 'pending-api' as MenuItemStatus },
      { path: '/research/portfolio-builder', label: '组合构建', icon: '', status: 'pending-api' as MenuItemStatus }
    ]
  },
  {
    path: '/trading',
    label: '交易管理',
    icon: '',
    children: [
      { path: '/trading/paper', label: '模拟盘', icon: '', status: 'pending-api' as MenuItemStatus },
      { path: '/trading/live', label: '实盘', icon: '', status: 'pending-api' as MenuItemStatus },
      { path: '/trading/orders', label: '订单管理', icon: '', status: 'pending-api' as MenuItemStatus }
    ]
  },
  {
    path: '/validation',
    label: '策略验证',
    icon: '',
    children: [
      { path: '/validation/optimizer', label: '参数优化', icon: '', status: 'pending-api' as MenuItemStatus },
      { path: '/validation/out-of-sample', label: '样本外测试', icon: '', status: 'pending-api' as MenuItemStatus },
      { path: '/validation/sensitivity', label: '敏感性分析', icon: '', status: 'pending-api' as MenuItemStatus },
      { path: '/validation/monte-carlo', label: '蒙特卡洛', icon: '', status: 'pending-api' as MenuItemStatus }
    ]
  },
  { path: '/components', label: '组件管理', icon: '', status: 'done' as MenuItemStatus },
  { path: '/data', label: '数据管理', icon: '', status: 'pending-api' as MenuItemStatus },
  { path: '/alert', label: '警报中心', icon: '', status: 'todo' as MenuItemStatus },
  {
    path: '/settings',
    label: '系统设置',
    icon: '',
    children: [
      { path: '/settings/users', label: '用户管理', icon: '', status: 'done' as MenuItemStatus },
      { path: '/settings/user-groups', label: '用户组管理', icon: '', status: 'done' as MenuItemStatus },
      { path: '/settings/notifications', label: '通知管理', icon: '', status: 'done' as MenuItemStatus },
      { path: '/settings/api', label: 'API接口设置', icon: '', status: 'done' as MenuItemStatus }
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

// 获取状态颜色
const getStatusColor = (status?: MenuItemStatus) => {
  switch (status) {
    case 'done':
      return 'green'  // 绿色 - 已完成
    case 'pending-api':
      return 'orange'  // 橙色 - 待API对接
    case 'todo':
      return 'default'   // 灰色 - 未实现
    default:
      return 'default'
  }
}

// 获取状态标签
const getStatusLabel = (status?: MenuItemStatus) => {
  switch (status) {
    case 'done':
      return '✓'
    case 'pending-api':
      return '待后端'
    case 'todo':
      return '未实现'
    default:
      return ''
  }
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
