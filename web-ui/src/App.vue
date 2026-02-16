<template>
  <a-config-provider :locale="zhCN">
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
                <a-menu>
                  <a-menu-item key="settings">
                    <SettingOutlined /> 系统设置
                  </a-menu-item>
                  <a-menu-divider />
                  <a-menu-item key="logout">
                    <LogoutOutlined /> 退出登录
                  </a-menu-item>
                </a-menu>
              </template>
            </a-dropdown>
          </div>
        </a-layout-header>
        <a-layout-content class="content">
          <router-view />
        </a-layout-content>
      </a-layout>
    </a-layout>
  </a-config-provider>
</template>

<script setup lang="ts">
import { ref, computed, h } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import zhCN from 'ant-design-vue/es/locale/zh_CN'
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
} from '@ant-design/icons-vue'
import type { MenuProps } from 'ant-design-vue'

const router = useRouter()
const route = useRoute()

const collapsed = ref(false)
const selectedKeys = ref<string[]>(['backtest'])
const notificationCount = ref(0)

// 4阶段策略生命周期菜单
const menuItems = computed<MenuProps['items']>(() => [
  {
    key: 'backtest',
    icon: () => h(RocketOutlined),
    label: '第一阶段：回测',
    title: '策略回测验证',
    children: [
      { key: 'backtest-list', label: '回测列表' },
      { key: 'backtest-create', label: '创建回测' },
      { key: 'backtest-compare', label: '回测对比' },
    ],
  },
  {
    key: 'validation',
    icon: () => h(ExperimentOutlined),
    label: '第二阶段：验证',
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
    label: '第三阶段：模拟',
    title: 'Paper Trading',
    children: [
      { key: 'paper-trading', label: '模拟交易' },
      { key: 'paper-config', label: '配置管理' },
      { key: 'paper-orders', label: '订单记录' },
    ],
  },
  {
    key: 'live',
    icon: () => h(ThunderboltOutlined),
    label: '第四阶段：实盘',
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
    ],
  },
  {
    key: 'data',
    icon: () => h(DatabaseOutlined),
    label: '数据管理',
    children: [
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
      { key: 'system-alerts', label: '告警中心' },
    ],
  },
])

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
    'backtest-list': '/stage1/backtest',
    'backtest-create': '/stage1/backtest/create',
    'backtest-compare': '/stage1/backtest/compare',
    'validation-walkforward': '/stage2/walkforward',
    'validation-montecarlo': '/stage2/montecarlo',
    'validation-sensitivity': '/stage2/sensitivity',
    'paper-trading': '/stage3/paper',
    'paper-config': '/stage3/paper/config',
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
    'data-stocks': '/data/stocks',
    'data-bars': '/data/bars',
    'data-sync': '/data/sync',
    'system-status': '/system/status',
    'system-workers': '/system/workers',
    'system-alerts': '/system/alerts',
  }

  if (routeMap[keyPath]) {
    router.push(routeMap[keyPath])
  }
}

const showNotifications = () => {
  // TODO: 显示通知面板
}
</script>

<style lang="less" scoped>
.app-layout {
  min-height: 100vh;
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
  margin: 24px;
  padding: 24px;
  background: #fff;
  border-radius: 8px;
  min-height: calc(100vh - 112px);
  overflow: auto;
}

:deep(.ant-menu) {
  border-right: none !important;
}

:deep(.ant-layout-sider) {
  box-shadow: 2px 0 8px rgba(0, 21, 41, 0.05);
}
</style>
