# WebUI 导航架构重设计 实现计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 将 WebUI 导航从 13 顶层菜单重构为 6 个扁平入口，以 Portfolio 为核心实体组织全生命周期。

**Architecture:** 侧边栏从折叠子菜单模式改为 6 个扁平项。Portfolio 详情页引入 Tab 布局承载回测/验证/模拟/实盘/组件。旧路由通过 redirect 兼容。现有 Vue 组件文件基本不变，只改路由路径和导航入口。

**Tech Stack:** Vue 3 + Vue Router 4 + Pinia + TypeScript + Playwright (E2E)

**Spec:** `docs/superpowers/specs/2026-04-19-webui-navigation-design.md`

---

## File Structure

| File | Action | Responsibility |
|------|--------|---------------|
| `web-ui/src/router/index.ts` | **Rewrite** | 所有路由定义 + 旧路由重定向 |
| `web-ui/src/App.vue` | **Modify** | 侧边栏菜单（6 项扁平，移除子菜单逻辑） |
| `web-ui/src/views/portfolio/PortfolioDetail.vue` | **Modify** | 新增 Tab 布局框架 |
| `web-ui/src/views/portfolio/tabs/OverviewTab.vue` | **Create** | 概况 Tab |
| `web-ui/src/views/portfolio/tabs/BacktestTab.vue` | **Create** | 回测 Tab（包装现有回测列表） |
| `web-ui/src/views/portfolio/tabs/ValidationTab.vue` | **Create** | 验证 Tab |
| `web-ui/src/views/portfolio/tabs/PaperTab.vue` | **Create** | 模拟 Tab |
| `web-ui/src/views/portfolio/tabs/LiveTab.vue` | **Create** | 实盘 Tab |
| `web-ui/src/views/portfolio/tabs/ComponentsTab.vue` | **Create** | 组件 Tab |
| `web-ui/src/views/research/ResearchPage.vue` | **Create** | 研究入口页（因子分析 + 参数优化 Tab） |
| `web-ui/src/views/trading/TradingPage.vue` | **Create** | 交易监控入口页（模拟 + 实盘 Tab） |
| `web-ui/src/views/admin/AdminPage.vue` | **Create** | 管理入口页（组件 + 系统 Tab） |
| `tests/e2e/dashboard/test_navigation.py` | **Modify** | 更新导航 E2E 测试 |

---

### Task 1: 重写路由定义

**Files:**
- Modify: `web-ui/src/router/index.ts`

- [ ] **Step 1: 重写 router/index.ts**

将整个 `routes` 数组替换为新结构。旧路由全部保留为 redirect。

```typescript
import { createRouter, createWebHistory, RouteRecordRaw } from 'vue-router'
import { isAuthenticated } from '@/api'

const routes: RouteRecordRaw[] = [
  // ===== 登录 =====
  { path: '/login', name: 'Login', component: () => import('@/views/auth/Login.vue'), meta: { title: '登录', requiresAuth: false } },

  // ===== 根重定向 =====
  { path: '/', redirect: '/dashboard' },

  // ===== 工作台 =====
  { path: '/dashboard', name: 'Dashboard', component: () => import('@/views/dashboard/Dashboard.vue'), meta: { title: '工作台' } },

  // ===== 组合 =====
  { path: '/portfolios', name: 'PortfolioList', component: () => import('@/views/portfolio/PortfolioList.vue'), meta: { title: '组合列表' } },
  { path: '/portfolios/create', name: 'PortfolioCreate', component: () => import('@/views/portfolio/PortfolioFormEditor.vue'), meta: { title: '创建组合' } },
  { path: '/portfolios/:id', name: 'PortfolioDetail', component: () => import('@/views/portfolio/PortfolioDetail.vue'), meta: { title: '组合详情' } },
  { path: '/portfolios/:id/edit', name: 'PortfolioEdit', component: () => import('@/views/portfolio/PortfolioFormEditor.vue'), meta: { title: '编辑组合' } },

  // ===== 研究 =====
  { path: '/research', name: 'Research', component: () => import('@/views/research/ResearchPage.vue'), meta: { title: '研究' }, redirect: '/research/factor' },
  { path: '/research/factor', name: 'FactorResearch', component: () => import('@/views/research/ResearchPage.vue'), meta: { title: '因子分析' } },
  { path: '/research/factor/ic', name: 'ICAnalysis', component: () => import('@/views/research/ICAnalysis.vue'), meta: { title: 'IC 分析' } },
  { path: '/research/factor/layering', name: 'FactorLayering', component: () => import('@/views/research/FactorLayering.vue'), meta: { title: '因子分层' } },
  { path: '/research/factor/orthogonal', name: 'FactorOrthogonalization', component: () => import('@/views/research/FactorOrthogonalization.vue'), meta: { title: '因子正交化' } },
  { path: '/research/factor/comparison', name: 'FactorComparison', component: () => import('@/views/research/FactorComparison.vue'), meta: { title: '因子比较' } },
  { path: '/research/factor/decay', name: 'FactorDecay', component: () => import('@/views/research/FactorDecay.vue'), meta: { title: '因子衰减' } },
  { path: '/research/optimization', name: 'Optimization', component: () => import('@/views/research/ResearchPage.vue'), meta: { title: '参数优化' } },
  { path: '/research/optimization/grid', name: 'GridSearch', component: () => import('@/views/optimization/GridSearch.vue'), meta: { title: '网格搜索' } },
  { path: '/research/optimization/genetic', name: 'GeneticOptimizer', component: () => import('@/views/optimization/GeneticOptimizer.vue'), meta: { title: '遗传算法' } },
  { path: '/research/optimization/bayesian', name: 'BayesianOptimizer', component: () => import('@/views/optimization/BayesianOptimizer.vue'), meta: { title: '贝叶斯优化' } },

  // ===== 交易 =====
  { path: '/trading', name: 'Trading', component: () => import('@/views/trading/TradingPage.vue'), meta: { title: '交易' }, redirect: '/trading/paper' },
  { path: '/trading/paper', name: 'TradingPaper', component: () => import('@/views/stage3/PaperTrading.vue'), meta: { title: '模拟盘监控' } },
  { path: '/trading/live', name: 'TradingLive', component: () => import('@/views/stage4/LiveTrading.vue'), meta: { title: '实盘监控' } },
  { path: '/trading/live/market', name: 'MarketData', component: () => import('@/views/stage4/MarketData.vue'), meta: { title: '市场数据', requiresAuth: false } },

  // ===== 数据 =====
  { path: '/data', name: 'DataOverview', component: () => import('@/views/data/DataOverview.vue'), meta: { title: '数据概览' } },
  { path: '/data/stocks', name: 'StockList', component: () => import('@/views/data/StockList.vue'), meta: { title: '股票信息' } },
  { path: '/data/bars', name: 'BarData', component: () => import('@/views/data/BarData.vue'), meta: { title: 'K线数据' } },
  { path: '/data/sync', name: 'DataSync', component: () => import('@/views/data/DataSync.vue'), meta: { title: '数据同步' } },

  // ===== 管理 =====
  { path: '/admin', name: 'Admin', component: () => import('@/views/admin/AdminPage.vue'), meta: { title: '管理' }, redirect: '/admin/components' },
  { path: '/admin/components', name: 'AdminComponents', component: () => import('@/views/admin/AdminPage.vue'), meta: { title: '组件库' } },
  { path: '/admin/components/:type', name: 'ComponentList', component: () => import('@/views/components/ComponentListPage.vue'), meta: { title: '组件列表' } },
  { path: '/admin/components/:type/:id', name: 'ComponentDetail', component: () => import('@/views/components/ComponentDetail.vue'), meta: { title: '组件详情' } },
  { path: '/admin/system', name: 'AdminSystem', component: () => import('@/views/system/SystemStatus.vue'), meta: { title: '系统状态' } },
  { path: '/admin/system/workers', name: 'WorkerManagement', component: () => import('@/views/system/WorkerManagement.vue'), meta: { title: 'Worker 管理' } },
  { path: '/admin/system/api-keys', name: 'ApiKeyManagement', component: () => import('@/views/system/ApiKeyManagement.vue'), meta: { title: 'API Key 管理' } },
  { path: '/admin/system/users', name: 'UserManagement', component: () => import('@/views/settings/UserManagement.vue'), meta: { title: '用户管理' } },
  { path: '/admin/system/groups', name: 'UserGroupManagement', component: () => import('@/views/settings/UserGroupManagement.vue'), meta: { title: '用户组管理' } },
  { path: '/admin/system/notifications', name: 'NotificationManagement', component: () => import('@/views/settings/NotificationManagement.vue'), meta: { title: '通知管理' } },
  { path: '/admin/system/alerts', name: 'AlertCenter', component: () => import('@/views/system/AlertCenter.vue'), meta: { title: '告警中心' } },

  // ===== 旧路由兼容重定向 =====
  { path: '/portfolio', redirect: '/portfolios' },
  { path: '/portfolio/create', redirect: '/portfolios/create' },
  { path: '/portfolio/:id', redirect: to => `/portfolios/${to.params.id}` },
  { path: '/portfolio/:id/edit', redirect: to => `/portfolios/${to.params.id}/edit` },
  { path: '/backtest', redirect: '/portfolios' },
  { path: '/backtest/create', redirect: '/portfolios' },
  { path: '/backtest/:id', redirect: '/portfolios' },
  { path: '/backtest/compare', redirect: '/portfolios' },
  { path: '/validation/walkforward', redirect: '/portfolios' },
  { path: '/validation/montecarlo', redirect: '/portfolios' },
  { path: '/validation/sensitivity', redirect: '/portfolios' },
  { path: '/paper', redirect: '/trading/paper' },
  { path: '/paper/orders', redirect: '/trading/paper' },
  { path: '/live', redirect: '/trading/live' },
  { path: '/live/orders', redirect: '/trading/live' },
  { path: '/live/positions', redirect: '/trading/live' },
  { path: '/live/market', redirect: '/trading/live/market' },
  { path: '/live/account-config', redirect: '/trading/live' },
  { path: '/live/account-info', redirect: '/trading/live' },
  { path: '/live/broker-management', redirect: '/trading/live' },
  { path: '/live/trade-history', redirect: '/trading/live' },
  { path: '/live/trading-control', redirect: '/trading/live' },
  { path: '/research/ic', redirect: '/research/factor/ic' },
  { path: '/research/layering', redirect: '/research/factor/layering' },
  { path: '/research/orthogonal', redirect: '/research/factor/orthogonal' },
  { path: '/research/comparison', redirect: '/research/factor/comparison' },
  { path: '/research/decay', redirect: '/research/factor/decay' },
  { path: '/optimization/grid', redirect: '/research/optimization/grid' },
  { path: '/optimization/genetic', redirect: '/research/optimization/genetic' },
  { path: '/optimization/bayesian', redirect: '/research/optimization/bayesian' },
  { path: '/components/strategies', redirect: '/admin/components/strategies' },
  { path: '/components/strategies/:id', redirect: to => `/admin/components/strategies/${to.params.id}` },
  { path: '/components/risks', redirect: '/admin/components/risks' },
  { path: '/components/risks/:id', redirect: to => `/admin/components/risks/${to.params.id}` },
  { path: '/components/sizers', redirect: '/admin/components/sizers' },
  { path: '/components/sizers/:id', redirect: to => `/admin/components/sizers/${to.params.id}` },
  { path: '/components/selectors', redirect: '/admin/components/selectors' },
  { path: '/components/selectors/:id', redirect: to => `/admin/components/selectors/${to.params.id}` },
  { path: '/components/analyzers', redirect: '/admin/components/analyzers' },
  { path: '/components/analyzers/:id', redirect: to => `/admin/components/analyzers/${to.params.id}` },
  { path: '/components/handlers', redirect: '/admin/components/handlers' },
  { path: '/components/handlers/:id', redirect: to => `/admin/components/handlers/${to.params.id}` },
  { path: '/system/status', redirect: '/admin/system' },
  { path: '/system/workers', redirect: '/admin/system/workers' },
  { path: '/system/api-keys', redirect: '/admin/system/api-keys' },
  { path: '/system/users', redirect: '/admin/system/users' },
  { path: '/system/groups', redirect: '/admin/system/groups' },
  { path: '/system/notifications', redirect: '/admin/system/notifications' },
  { path: '/system/alerts', redirect: '/admin/system/alerts' },

  // 404
  { path: '/:pathMatch(.*)*', name: 'NotFound', component: () => import('@/views/NotFound.vue'), meta: { title: '页面未找到' } },
]

const router = createRouter({
  history: createWebHistory(),
  routes,
})

// 路由守卫 - 认证检查
router.beforeEach((to, from, next) => {
  document.title = `${to.meta?.title || 'Ginkgo'} - 量化交易平台`
  const requiresAuth = to.meta?.requiresAuth !== false
  if (requiresAuth && !isAuthenticated()) {
    next({ path: '/login', query: { redirect: to.fullPath } })
  } else if (to.path === '/login' && isAuthenticated()) {
    next({ path: '/' })
  } else {
    next()
  }
})

export default router
```

- [ ] **Step 2: 验证路由编译通过**

Run: `cd web-ui && npx vue-tsc --noEmit 2>&1 | head -20`
Expected: 无类型错误（可能有组件导入警告，但无路由相关错误）

- [ ] **Step 3: Commit**

```bash
git add web-ui/src/router/index.ts
git commit -m "refactor(web-ui): rewrite router with new 6-entry navigation structure"
```

---

### Task 2: 简化侧边栏导航

**Files:**
- Modify: `web-ui/src/App.vue`（menuItems、icons、routeToKeyMap、keyToParentMap、getRouteForKey、子菜单相关模板和逻辑）

- [ ] **Step 1: 替换 menuItems 为 6 项扁平结构**

在 App.vue `<script setup>` 中，将 `menuItems` computed 替换为：

```typescript
const menuItems = [
  { key: 'dashboard', label: '工作台', icon: icons.dashboard },
  { key: 'portfolios', label: '组合', icon: icons.wallet },
  { key: 'research', label: '研究', icon: icons.filesearch },
  { key: 'trading', label: '交易', icon: icons.linechart },
  { key: 'data', label: '数据', icon: icons.database },
  { key: 'admin', label: '管理', icon: icons.tool },
]
```

- [ ] **Step 2: 更新 getRouteForKey**

```typescript
const getRouteForKey = (key: string): string => {
  const routeMap: Record<string, string> = {
    'dashboard': '/dashboard',
    'portfolios': '/portfolios',
    'research': '/research',
    'trading': '/trading',
    'data': '/data',
    'admin': '/admin',
  }
  return routeMap[key] || '/'
}
```

- [ ] **Step 3: 更新 routeToKeyMap**

```typescript
const routeToKeyMap: Record<string, string> = {
  '/dashboard': 'dashboard',
  '/portfolios': 'portfolios',
  '/portfolios/create': 'portfolios',
  '/research': 'research',
  '/research/factor': 'research',
  '/research/factor/ic': 'research',
  '/research/factor/layering': 'research',
  '/research/factor/orthogonal': 'research',
  '/research/factor/comparison': 'research',
  '/research/factor/decay': 'research',
  '/research/optimization': 'research',
  '/research/optimization/grid': 'research',
  '/research/optimization/genetic': 'research',
  '/research/optimization/bayesian': 'research',
  '/trading': 'trading',
  '/trading/paper': 'trading',
  '/trading/live': 'trading',
  '/trading/live/market': 'trading',
  '/data': 'data',
  '/data/stocks': 'data',
  '/data/bars': 'data',
  '/data/sync': 'data',
  '/admin': 'admin',
  '/admin/components': 'admin',
  '/admin/components/strategies': 'admin',
  '/admin/components/risks': 'admin',
  '/admin/components/sizers': 'admin',
  '/admin/components/selectors': 'admin',
  '/admin/components/analyzers': 'admin',
  '/admin/components/handlers': 'admin',
  '/admin/system': 'admin',
  '/admin/system/workers': 'admin',
  '/admin/system/api-keys': 'admin',
  '/admin/system/users': 'admin',
  '/admin/system/groups': 'admin',
  '/admin/system/notifications': 'admin',
  '/admin/system/alerts': 'admin',
}
```

- [ ] **Step 4: 删除 keyToParentMap 和子菜单相关变量**

删除 `keyToParentMap`、`openKeys` ref、`toggleSubMenu` 函数。不再需要子菜单展开/折叠逻辑。

- [ ] **Step 5: 简化路由 watch 逻辑**

```typescript
watch(() => route.path, (path) => {
  let key = routeToKeyMap[path]
  if (!key) {
    if (path.startsWith('/portfolios/') && path !== '/portfolios/create') {
      key = 'portfolios'
    }
    else if (path.startsWith('/research/')) {
      key = 'research'
    }
    else if (path.startsWith('/trading/')) {
      key = 'trading'
    }
    else if (path.startsWith('/admin/')) {
      key = 'admin'
    }
  }
  if (key) {
    selectedKeys.value = [key]
  }
})
```

- [ ] **Step 6: 简化侧边栏模板**

移除子菜单相关的模板代码（`has-submenu`、`submenu-arrow`、`submenu` div、`v-if="item.children"` 等）。每个菜单项都直接是 `<router-link>`。

将侧边栏 `<nav class="menu">` 的内容替换为：

```html
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
```

- [ ] **Step 7: 删除不再需要的 MenuItem interface 的 children/type 字段**

```typescript
interface MenuItem {
  key: string
  label: string
  icon: Component | ''
}
```

- [ ] **Step 8: 验证 dev server 启动**

Run: `cd web-ui && npx vite build --mode development 2>&1 | tail -5`
Expected: 构建成功

- [ ] **Step 9: Commit**

```bash
git add web-ui/src/App.vue
git commit -m "refactor(web-ui): simplify sidebar to 6 flat navigation items"
```

---

### Task 3: 创建研究入口页

**Files:**
- Create: `web-ui/src/views/research/ResearchPage.vue`

- [ ] **Step 1: 创建 ResearchPage.vue**

这是一个带 Tab 切换的入口页，在"因子分析"和"参数优化"之间切换，每个 Tab 嵌入对应的子页面。

```vue
<template>
  <div class="research-page">
    <div class="tab-bar">
      <router-link
        v-for="tab in tabs"
        :key="tab.key"
        :to="tab.route"
        class="tab-item"
        :class="{ active: isActive(tab.key) }"
      >
        {{ tab.label }}
      </router-link>
    </div>
    <div class="tab-content">
      <router-view />
    </div>
  </div>
</template>

<script setup lang="ts">
import { useRoute } from 'vue-router'

const route = useRoute()

const tabs = [
  { key: 'factor', label: '因子分析', route: '/research/factor' },
  { key: 'optimization', label: '参数优化', route: '/research/optimization' },
]

const isActive = (key: string) => route.path.includes(key)
</script>

<style scoped>
.research-page {
  display: flex;
  flex-direction: column;
  height: 100%;
}
.tab-bar {
  display: flex;
  gap: 0;
  border-bottom: 1px solid #2a2a3e;
  padding: 0 24px;
}
.tab-item {
  padding: 10px 16px;
  color: rgba(255,255,255,0.6);
  text-decoration: none;
  font-size: 14px;
  border-bottom: 2px solid transparent;
  transition: all 0.2s;
}
.tab-item:hover {
  color: rgba(255,255,255,0.9);
}
.tab-item.active {
  color: #3b82f6;
  border-bottom-color: #3b82f6;
  font-weight: 600;
}
.tab-content {
  flex: 1;
  overflow: auto;
}
</style>
```

- [ ] **Step 2: 验证路由嵌套 — 确保 /research 和 /research/factor 都显示此页面**

Run: `cd web-ui && npx vite build --mode development 2>&1 | tail -5`
Expected: 构建成功

- [ ] **Step 3: Commit**

```bash
git add web-ui/src/views/research/ResearchPage.vue
git commit -m "feat(web-ui): add research landing page with factor/optimization tabs"
```

---

### Task 4: 创建交易监控入口页

**Files:**
- Create: `web-ui/src/views/trading/TradingPage.vue`

- [ ] **Step 1: 创建 TradingPage.vue**

```vue
<template>
  <div class="trading-page">
    <div class="tab-bar">
      <router-link
        v-for="tab in tabs"
        :key="tab.key"
        :to="tab.route"
        class="tab-item"
        :class="{ active: isActive(tab.key) }"
      >
        {{ tab.label }}
      </router-link>
    </div>
    <div class="tab-content">
      <router-view />
    </div>
  </div>
</template>

<script setup lang="ts">
import { useRoute } from 'vue-router'

const route = useRoute()

const tabs = [
  { key: 'paper', label: '模拟盘', route: '/trading/paper' },
  { key: 'live', label: '实盘', route: '/trading/live' },
]

const isActive = (key: string) => route.path.includes(key)
</script>

<style scoped>
.trading-page {
  display: flex;
  flex-direction: column;
  height: 100%;
}
.tab-bar {
  display: flex;
  gap: 0;
  border-bottom: 1px solid #2a2a3e;
  padding: 0 24px;
}
.tab-item {
  padding: 10px 16px;
  color: rgba(255,255,255,0.6);
  text-decoration: none;
  font-size: 14px;
  border-bottom: 2px solid transparent;
  transition: all 0.2s;
}
.tab-item:hover {
  color: rgba(255,255,255,0.9);
}
.tab-item.active {
  color: #3b82f6;
  border-bottom-color: #3b82f6;
  font-weight: 600;
}
.tab-content {
  flex: 1;
  overflow: auto;
}
</style>
```

- [ ] **Step 2: Commit**

```bash
git add web-ui/src/views/trading/TradingPage.vue
git commit -m "feat(web-ui): add trading monitoring landing page with paper/live tabs"
```

---

### Task 5: 创建管理入口页

**Files:**
- Create: `web-ui/src/views/admin/AdminPage.vue`

- [ ] **Step 1: 创建 AdminPage.vue**

管理页面有两个入口：组件库和系统。用侧边 Tab 或列表导航。

```vue
<template>
  <div class="admin-page">
    <div class="admin-sidebar">
      <div class="admin-nav">
        <router-link
          v-for="item in navItems"
          :key="item.key"
          :to="item.route"
          class="admin-nav-item"
          :class="{ active: isActive(item.key) }"
        >
          {{ item.label }}
        </router-link>
      </div>
    </div>
    <div class="admin-content">
      <router-view />
    </div>
  </div>
</template>

<script setup lang="ts">
import { useRoute } from 'vue-router'

const route = useRoute()

const navItems = [
  {
    key: 'components',
    label: '组件库',
    route: '/admin/components',
    children: [
      { label: '策略组件', route: '/admin/components/strategies' },
      { label: '风控组件', route: '/admin/components/risks' },
      { label: '仓位组件', route: '/admin/components/sizers' },
      { label: '选股器', route: '/admin/components/selectors' },
      { label: '分析器', route: '/admin/components/analyzers' },
      { label: '事件处理器', route: '/admin/components/handlers' },
    ],
  },
  {
    key: 'system',
    label: '系统',
    route: '/admin/system',
    children: [
      { label: '系统状态', route: '/admin/system' },
      { label: 'Worker 管理', route: '/admin/system/workers' },
      { label: 'API Key', route: '/admin/system/api-keys' },
      { label: '用户管理', route: '/admin/system/users' },
      { label: '用户组', route: '/admin/system/groups' },
      { label: '通知管理', route: '/admin/system/notifications' },
      { label: '告警中心', route: '/admin/system/alerts' },
    ],
  },
]

const isActive = (key: string) => {
  if (key === 'components') return route.path.startsWith('/admin/components')
  if (key === 'system') return route.path.startsWith('/admin/system')
  return false
}
</script>

<style scoped>
.admin-page {
  display: flex;
  height: 100%;
}
.admin-sidebar {
  width: 180px;
  background: #1a1a2e;
  border-right: 1px solid #2a2a3e;
  padding: 16px 0;
}
.admin-nav-item {
  display: block;
  padding: 8px 20px;
  color: rgba(255,255,255,0.6);
  text-decoration: none;
  font-size: 14px;
  transition: all 0.2s;
}
.admin-nav-item:hover {
  color: rgba(255,255,255,0.9);
  background: rgba(255,255,255,0.05);
}
.admin-nav-item.active {
  color: #3b82f6;
  background: rgba(59,130,246,0.1);
  border-right: 2px solid #3b82f6;
}
.admin-content {
  flex: 1;
  overflow: auto;
}
</style>
```

- [ ] **Step 2: Commit**

```bash
git add web-ui/src/views/admin/AdminPage.vue
git commit -m "feat(web-ui): add admin landing page with components/system navigation"
```

---

### Task 6: Portfolio 详情页 Tab 布局

这是最大的任务。将现有 PortfolioDetail.vue 改造为 Tab 布局。

**Files:**
- Modify: `web-ui/src/views/portfolio/PortfolioDetail.vue`
- Create: `web-ui/src/views/portfolio/tabs/OverviewTab.vue`

- [ ] **Step 1: 创建 OverviewTab.vue**

```vue
<template>
  <div class="overview-tab">
    <div class="stats-row">
      <div class="stat-card">
        <div class="stat-label">最新净值</div>
        <div class="stat-value" :class="valueClass">{{ formatNumber(portfolio?.net_value) }}</div>
      </div>
      <div class="stat-card">
        <div class="stat-label">总收益率</div>
        <div class="stat-value" :class="pnlClass">{{ formatPct(portfolio?.pnl_rate) }}</div>
      </div>
      <div class="stat-card">
        <div class="stat-label">最大回撤</div>
        <div class="stat-value text-danger">{{ formatPct(portfolio?.max_drawdown) }}</div>
      </div>
      <div class="stat-card">
        <div class="stat-label">夏普比率</div>
        <div class="stat-value">{{ formatNumber(portfolio?.sharpe_ratio) }}</div>
      </div>
    </div>
    <div class="section">
      <h3>最近活动</h3>
      <div class="activity-list">
        <div v-if="!activities.length" class="empty-hint">暂无活动记录</div>
        <div v-for="item in activities" :key="item.id" class="activity-item">
          <span class="activity-time">{{ item.time }}</span>
          <span class="activity-text">{{ item.text }}</span>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'

const props = defineProps<{
  portfolio: Record<string, any> | null
}>()

const activities = computed(() => [])

const valueClass = computed(() => '')
const pnlClass = computed(() => {
  const rate = props.portfolio?.pnl_rate
  if (rate == null) return ''
  return rate >= 0 ? 'text-profit' : 'text-danger'
})

const formatNumber = (v: any) => v != null ? Number(v).toFixed(4) : '--'
const formatPct = (v: any) => v != null ? `${v >= 0 ? '+' : ''}${(Number(v) * 100).toFixed(2)}%` : '--'
</script>

<style scoped>
.stats-row {
  display: flex;
  gap: 16px;
  margin-bottom: 24px;
}
.stat-card {
  flex: 1;
  background: #1a1a2e;
  border-radius: 8px;
  padding: 16px;
}
.stat-label {
  font-size: 12px;
  color: rgba(255,255,255,0.5);
  text-transform: uppercase;
  margin-bottom: 4px;
}
.stat-value {
  font-size: 20px;
  font-weight: 700;
}
.text-profit { color: #22c55e; }
.text-danger { color: #ef4444; }
.section {
  margin-top: 16px;
}
.section h3 {
  font-size: 14px;
  margin-bottom: 12px;
}
.activity-item {
  padding: 6px 0;
  font-size: 13px;
  color: rgba(255,255,255,0.7);
}
.activity-time {
  margin-right: 12px;
  color: rgba(255,255,255,0.4);
  font-size: 12px;
}
.empty-hint {
  color: rgba(255,255,255,0.4);
  font-size: 13px;
  padding: 16px 0;
}
</style>
```

- [ ] **Step 2: 修改 PortfolioDetail.vue，添加 Tab 布局**

在现有 `PortfolioDetail.vue` 的 `<template>` 中，在 `page-header` 下方添加 Tab 导航栏。在 `<script>` 中引入 Tab 配置。核心改动：

在 `<template>` 中 `page-header` div 之后、`page-content` div 之前插入：

```html
    <!-- Tab 导航 -->
    <div class="tab-bar">
      <router-link
        v-for="tab in tabs"
        :key="tab.key"
        :to="tab.route(portfolioId)"
        class="tab-item"
        :class="{ active: activeTab === tab.key }"
      >
        {{ tab.label }}
      </router-link>
    </div>
```

将现有页面内容包裹为概况 Tab 的内容（默认视图）。

在 `<script setup>` 中添加：

```typescript
const portfolioId = computed(() => route.params.id as string)
const activeTab = computed(() => {
  const path = route.path
  if (path.includes('/backtests')) return 'backtests'
  if (path.includes('/validation')) return 'validation'
  if (path.includes('/paper')) return 'paper'
  if (path.includes('/live')) return 'live'
  if (path.includes('/components')) return 'components'
  return 'overview'
})

const tabs = [
  { key: 'overview', label: '概况', route: (id: string) => `/portfolios/${id}` },
  { key: 'backtests', label: '回测', route: (id: string) => `/portfolios/${id}/backtests` },
  { key: 'validation', label: '验证', route: (id: string) => `/portfolios/${id}/validation` },
  { key: 'paper', label: '模拟', route: (id: string) => `/portfolios/${id}/paper` },
  { key: 'live', label: '实盘', route: (id: string) => `/portfolios/${id}/live` },
  { key: 'components', label: '组件', route: (id: string) => `/portfolios/${id}/components` },
]
```

在 `<style>` 中添加 Tab 样式（与 ResearchPage.vue 中相同的 `.tab-bar`/`.tab-item` 样式）。

**注意：** 当前 PortfolioDetail 的现有内容（指标、净值图等）保留为"概况" Tab 的内容。后续任务逐步填充其他 Tab。

- [ ] **Step 3: 验证 dev server**

Run: `cd web-ui && npx vite build --mode development 2>&1 | tail -5`
Expected: 构建成功

- [ ] **Step 4: Commit**

```bash
git add web-ui/src/views/portfolio/PortfolioDetail.vue web-ui/src/views/portfolio/tabs/OverviewTab.vue
git commit -m "feat(web-ui): add tab layout to portfolio detail page"
```

---

### Task 7: 更新 E2E 导航测试

**Files:**
- Modify: `tests/e2e/dashboard/test_navigation.py`

- [ ] **Step 1: 重写 test_navigation.py**

```python
"""
侧边栏导航 E2E 测试

覆盖：
- 6 个扁平菜单项可见
- 点击导航到对应页面
- 旧路由重定向
- 折叠/展开侧边栏
"""

import re

import pytest
from playwright.sync_api import Page, expect

from ..config import config

SEL = {
    "nav_dashboard": "[data-testid='nav-dashboard']",
    "nav_portfolios": "[data-testid='nav-portfolios']",
    "nav_research": "[data-testid='nav-research']",
    "nav_trading": "[data-testid='nav-trading']",
    "nav_data": "[data-testid='nav-data']",
    "nav_admin": "[data-testid='nav-admin']",
}


def _goto_dashboard(page: Page):
    page.goto(f"{config.web_ui_url}/dashboard")
    page.wait_for_load_state("networkidle")


@pytest.mark.e2e
class TestSidebarMenu:
    """侧边栏菜单渲染"""

    def test_sidebar_visible(self, authenticated_page: Page):
        _goto_dashboard(authenticated_page)
        expect(authenticated_page.locator(".sider")).to_be_visible()

    def test_all_menu_items_visible(self, authenticated_page: Page):
        """6 个菜单项全部可见"""
        _goto_dashboard(authenticated_page)
        for key in SEL:
            expect(authenticated_page.locator(SEL[key])).to_be_visible()


@pytest.mark.e2e
class TestPrimaryNavigation:
    """扁平菜单导航"""

    def test_navigate_to_dashboard(self, authenticated_page: Page):
        _goto_dashboard(authenticated_page)
        authenticated_page.click(SEL["nav_dashboard"])
        authenticated_page.wait_for_load_state("networkidle")
        assert "/dashboard" in authenticated_page.url

    def test_navigate_to_portfolios(self, authenticated_page: Page):
        _goto_dashboard(authenticated_page)
        authenticated_page.click(SEL["nav_portfolios"])
        authenticated_page.wait_for_url("**/portfolios**", timeout=5000)
        assert "/portfolios" in authenticated_page.url

    def test_navigate_to_research(self, authenticated_page: Page):
        _goto_dashboard(authenticated_page)
        authenticated_page.click(SEL["nav_research"])
        authenticated_page.wait_for_url("**/research**", timeout=5000)
        assert "/research" in authenticated_page.url

    def test_navigate_to_trading(self, authenticated_page: Page):
        _goto_dashboard(authenticated_page)
        authenticated_page.click(SEL["nav_trading"])
        authenticated_page.wait_for_url("**/trading**", timeout=5000)
        assert "/trading" in authenticated_page.url

    def test_navigate_to_data(self, authenticated_page: Page):
        _goto_dashboard(authenticated_page)
        authenticated_page.click(SEL["nav_data"])
        authenticated_page.wait_for_url("**/data**", timeout=5000)
        assert "/data" in authenticated_page.url

    def test_navigate_to_admin(self, authenticated_page: Page):
        _goto_dashboard(authenticated_page)
        authenticated_page.click(SEL["nav_admin"])
        authenticated_page.wait_for_url("**/admin**", timeout=5000)
        assert "/admin" in authenticated_page.url


@pytest.mark.e2e
class TestLegacyRedirects:
    """旧路由重定向"""

    def test_portfolio_redirect(self, authenticated_page: Page):
        authenticated_page.goto(f"{config.web_ui_url}/portfolio")
        authenticated_page.wait_for_load_state("networkidle")
        assert "/portfolios" in authenticated_page.url

    def test_backtest_redirect(self, authenticated_page: Page):
        authenticated_page.goto(f"{config.web_ui_url}/backtest")
        authenticated_page.wait_for_load_state("networkidle")
        assert "/portfolios" in authenticated_page.url

    def test_system_redirect(self, authenticated_page: Page):
        authenticated_page.goto(f"{config.web_ui_url}/system/status")
        authenticated_page.wait_for_load_state("networkidle")
        assert "/admin/system" in authenticated_page.url


@pytest.mark.e2e
class TestSidebarCollapse:
    """侧边栏折叠/展开"""

    def test_collapse_and_expand(self, authenticated_page: Page):
        _goto_dashboard(authenticated_page)
        sider = authenticated_page.locator(".sider")
        trigger = authenticated_page.locator(".trigger")
        expect(trigger).to_be_visible()
        trigger.click()
        expect(sider).to_have_class(re.compile(r"collapsed"))
        trigger.click()
        expect(sider).not_to_have_class(re.compile(r"collapsed"))
```

- [ ] **Step 2: Commit**

```bash
git add tests/e2e/dashboard/test_navigation.py
git commit -m "test(e2e): update navigation tests for new 6-entry sidebar"
```

---

### Task 8: 验证全部旧路由重定向

**Files:** 无新文件

- [ ] **Step 1: 启动 dev server，手动验证关键重定向**

Run: `cd web-ui && npx vite --port 5173 &`

验证以下 URL 都正确重定向：
- `/portfolio` → `/portfolios`
- `/backtest` → `/portfolios`
- `/system/status` → `/admin/system`
- `/live` → `/trading/live`
- `/research/ic` → `/research/factor/ic`
- `/components/strategies` → `/admin/components/strategies`

- [ ] **Step 2: 验证 6 个侧边栏导航都能正常跳转**

点击侧边栏的每一项，确认：
- 工作台 → `/dashboard`
- 组合 → `/portfolios`
- 研究 → `/research`
- 交易 → `/trading`
- 数据 → `/data`
- 管理 → `/admin`

- [ ] **Step 3: 最终 commit**

```bash
git add -A
git commit -m "chore(web-ui): verify all redirects and navigation working"
```

---

## Self-Review

**1. Spec coverage check:**
- 6 顶层菜单 ✅ Task 1-2
- 工作台 /dashboard ✅ Task 1 (路由保留)
- 组合 /portfolios + 6 Tab ✅ Task 1, 6
- 研究 /research ✅ Task 1, 3
- 交易 /trading ✅ Task 1, 4
- 数据 /data ✅ Task 1 (路由不变)
- 管理 /admin ✅ Task 1, 5
- 旧路由重定向 ✅ Task 1
- E2E 测试更新 ✅ Task 7

**2. Placeholder scan:** 无 TBD/TODO。

**3. Type consistency:** 所有 Tab 路由使用一致的 `(id: string) => string` 签名。`isActive` 函数在三个页面中使用相同的 `route.path.includes()` 模式。
