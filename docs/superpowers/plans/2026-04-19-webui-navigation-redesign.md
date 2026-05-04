# WebUI 导航重设计 — Phase 1: 路由和导航

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 将侧边栏从 6 项扩展为 7 项（新增组件独立入口），重组路由结构（组件从 /admin/components 提升到 /components，admin 路由扁平化）。

**Architecture:** 仅改路由路径和导航入口，不改任何视图组件内容。组件库视图文件保持不变，只是路由路径变了。旧路径全部保留 redirect 兼容。

**Tech Stack:** Vue 3 + Vue Router 4 + lucide-vue-next

**Spec:** `docs/superpowers/specs/2026-04-19-webui-navigation-design.md`

**Scope:** Phase 1 only。Phase 2（Portfolio 详情 Tab）、Phase 3（页面迁移）、Phase 4（Dashboard 重写）为后续独立计划。

---

## File Structure

| File | Action | Responsibility |
|------|--------|---------------|
| `web-ui/src/App.vue` | **Modify** | 侧边栏加第 7 项（组件），更新路由映射，修复 header 链接 |
| `web-ui/src/router/index.ts` | **Modify** | 组件路由提升，admin 路由扁平化，更新重定向 |

---

### Task 1: 更新 App.vue 侧边栏

**Files:**
- Modify: `web-ui/src/App.vue`

当前 App.vue 有 6 个菜单项。需要新增第 7 项"组件"（位于"组合"和"研究"之间），并修复 header 中的"系统设置"链接。

- [ ] **Step 1: 添加 Puzzle 图标导入**

在 `App.vue` 第 123-126 行的 lucide 导入中添加 `Puzzle`：

```typescript
import {
  LayoutDashboard, Wallet, TrendingUp,
  Wrench, Database, FileSearch, Puzzle,
} from 'lucide-vue-next'
```

- [ ] **Step 2: 在 icons 映射中添加 puzzle**

在第 167-174 行的 icons 对象中添加：

```typescript
const icons: Record<string, Component> = {
  dashboard: LayoutDashboard,
  wallet: Wallet,
  filesearch: FileSearch,
  linechart: TrendingUp,
  database: Database,
  tool: Wrench,
  puzzle: Puzzle,
}
```

- [ ] **Step 3: 在 menuItems 中添加组件项**

在第 183-190 行的 menuItems 数组中，在 portfolios 和 research 之间插入：

```typescript
const menuItems: MenuItem[] = [
  { key: 'dashboard', label: '工作台', icon: icons.dashboard },
  { key: 'portfolios', label: '组合', icon: icons.wallet },
  { key: 'components', label: '组件', icon: icons.puzzle },
  { key: 'research', label: '研究', icon: icons.filesearch },
  { key: 'trading', label: '交易', icon: icons.linechart },
  { key: 'data', label: '数据', icon: icons.database },
  { key: 'admin', label: '管理', icon: icons.tool },
]
```

- [ ] **Step 4: 更新 routeToKeyMap**

在第 204-211 行添加 components 映射：

```typescript
const routeToKeyMap: Record<string, string> = {
  '/dashboard': 'dashboard',
  '/portfolios': 'portfolios',
  '/components': 'components',
  '/research': 'research',
  '/trading': 'trading',
  '/data': 'data',
  '/admin': 'admin',
}
```

- [ ] **Step 5: 更新路由 watch，添加 components 路径匹配**

在第 214-230 行的 watch 回调中，在 portfolios 分支之后添加 components 分支：

```typescript
watch(() => route.path, (path) => {
  let key = routeToKeyMap[path]
  if (!key) {
    if (path.startsWith('/portfolios/')) {
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
```

- [ ] **Step 6: 更新 getRouteForKey**

在第 241-251 行的 routeMap 中添加 components：

```typescript
const getRouteForKey = (key: string): string => {
  const routeMap: Record<string, string> = {
    'dashboard': '/dashboard',
    'portfolios': '/portfolios',
    'components': '/components',
    'research': '/research',
    'trading': '/trading',
    'data': '/data',
    'admin': '/admin',
  }
  return routeMap[key] || '/'
}
```

- [ ] **Step 7: 修复 header "系统设置"链接**

在第 89 行，将 `/system/status` 改为 `/admin`：

```html
<button class="dropdown-item" @click="router.push('/admin'); showUserMenu = false">
```

- [ ] **Step 8: 验证编译通过**

Run: `cd /home/kaoru/Ginkgo/web-ui && npx vue-tsc --noEmit 2>&1 | head -20`
Expected: 无类型错误

- [ ] **Step 9: Commit**

```bash
git add web-ui/src/App.vue
git commit -m "feat(web-ui): add components as 7th top-level nav entry"
```

---

### Task 2: 重组路由结构

**Files:**
- Modify: `web-ui/src/router/index.ts`

三大改动：
1. 组件路由从 `/admin/components/*` 提升到 `/components/*`
2. Admin 路由从 `/admin/system/*` 扁平化到 `/admin/*`
3. 旧路径全部保留 redirect

- [ ] **Step 1: 重写路由定义**

替换整个 `routes` 数组内容（第 4-111 行）。保留 import、router 创建和守卫不变：

```typescript
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

  // ===== 组件（独立顶层入口）=====
  { path: '/components', name: 'Components', component: () => import('@/views/admin/AdminPage.vue'), meta: { title: '组件库' } },
  { path: '/components/:type', name: 'ComponentList', component: () => import('@/views/components/ComponentListPage.vue'), meta: { title: '组件列表' } },
  { path: '/components/:type/:id', name: 'ComponentDetail', component: () => import('@/views/components/ComponentDetail.vue'), meta: { title: '组件详情' } },

  // ===== 研究 =====
  { path: '/research', name: 'Research', redirect: '/research/factor', meta: { title: '研究' } },
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
  { path: '/trading', name: 'Trading', redirect: '/trading/paper', meta: { title: '交易' } },
  { path: '/trading/paper', name: 'TradingPaper', component: () => import('@/views/stage3/PaperTrading.vue'), meta: { title: '模拟盘监控' } },
  { path: '/trading/live', name: 'TradingLive', component: () => import('@/views/stage4/LiveTrading.vue'), meta: { title: '实盘监控' } },
  { path: '/trading/live/market', name: 'MarketData', component: () => import('@/views/stage4/MarketData.vue'), meta: { title: '市场数据', requiresAuth: false } },

  // ===== 数据 =====
  { path: '/data', name: 'DataOverview', component: () => import('@/views/data/DataOverview.vue'), meta: { title: '数据概览' } },
  { path: '/data/stocks', name: 'StockList', component: () => import('@/views/data/StockList.vue'), meta: { title: '股票信息' } },
  { path: '/data/bars', name: 'BarData', component: () => import('@/views/data/BarData.vue'), meta: { title: 'K线数据' } },
  { path: '/data/sync', name: 'DataSync', component: () => import('@/views/data/DataSync.vue'), meta: { title: '数据同步' } },

  // ===== 管理（仅系统级功能）=====
  { path: '/admin', name: 'Admin', component: () => import('@/views/system/SystemStatus.vue'), meta: { title: '系统状态' } },
  { path: '/admin/workers', name: 'WorkerManagement', component: () => import('@/views/system/WorkerManagement.vue'), meta: { title: 'Worker 管理' } },
  { path: '/admin/api-keys', name: 'ApiKeyManagement', component: () => import('@/views/system/ApiKeyManagement.vue'), meta: { title: 'API Key 管理' } },
  { path: '/admin/users', name: 'UserManagement', component: () => import('@/views/settings/UserManagement.vue'), meta: { title: '用户管理' } },
  { path: '/admin/groups', name: 'UserGroupManagement', component: () => import('@/views/settings/UserGroupManagement.vue'), meta: { title: '用户组管理' } },
  { path: '/admin/notifications', name: 'NotificationManagement', component: () => import('@/views/settings/NotificationManagement.vue'), meta: { title: '通知管理' } },
  { path: '/admin/alerts', name: 'AlertCenter', component: () => import('@/views/system/AlertCenter.vue'), meta: { title: '告警中心' } },

  // ===== 旧路由兼容重定向 =====

  // 单数 → 复数（portfolio → portfolios）
  { path: '/portfolio', redirect: '/portfolios' },
  { path: '/portfolio/create', redirect: '/portfolios/create' },
  { path: '/portfolio/:id', redirect: to => `/portfolios/${to.params.id}` },
  { path: '/portfolio/:id/edit', redirect: to => `/portfolios/${to.params.id}/edit` },

  // 回测 → 组合（回测已移入 Portfolio 详情）
  { path: '/backtest', redirect: '/portfolios' },
  { path: '/backtest/create', redirect: '/portfolios' },
  { path: '/backtest/:id', redirect: '/portfolios' },
  { path: '/backtest/compare', redirect: '/portfolios' },

  // 验证 → 组合（验证已移入 Portfolio 详情）
  { path: '/validation/walkforward', redirect: '/portfolios' },
  { path: '/validation/montecarlo', redirect: '/portfolios' },
  { path: '/validation/sensitivity', redirect: '/portfolios' },

  // 模拟盘 → 交易
  { path: '/paper', redirect: '/trading/paper' },
  { path: '/paper/orders', redirect: '/trading/paper' },

  // 实盘 → 交易
  { path: '/live', redirect: '/trading/live' },
  { path: '/live/orders', redirect: '/trading/live' },
  { path: '/live/positions', redirect: '/trading/live' },
  { path: '/live/market', redirect: '/trading/live/market' },
  { path: '/live/account-config', redirect: '/trading/live' },
  { path: '/live/account-info', redirect: '/trading/live' },
  { path: '/live/broker-management', redirect: '/trading/live' },
  { path: '/live/trade-history', redirect: '/trading/live' },
  { path: '/live/trading-control', redirect: '/trading/live' },

  // 研究旧路径
  { path: '/research/ic', redirect: '/research/factor/ic' },
  { path: '/research/layering', redirect: '/research/factor/layering' },
  { path: '/research/orthogonal', redirect: '/research/factor/orthogonal' },
  { path: '/research/comparison', redirect: '/research/factor/comparison' },
  { path: '/research/decay', redirect: '/research/factor/decay' },

  // 优化旧路径
  { path: '/optimization/grid', redirect: '/research/optimization/grid' },
  { path: '/optimization/genetic', redirect: '/research/optimization/genetic' },
  { path: '/optimization/bayesian', redirect: '/research/optimization/bayesian' },

  // 组件旧路径（/admin/components → /components）
  { path: '/admin/components', redirect: '/components' },
  { path: '/admin/components/:type', redirect: to => `/components/${to.params.type}` },
  { path: '/admin/components/:type/:id', redirect: to => `/components/${to.params.type}/${to.params.id}` },

  // 管理旧路径（/admin/system/* → /admin/*）
  { path: '/admin/system', redirect: '/admin' },
  { path: '/admin/system/workers', redirect: '/admin/workers' },
  { path: '/admin/system/api-keys', redirect: '/admin/api-keys' },
  { path: '/admin/system/users', redirect: '/admin/users' },
  { path: '/admin/system/groups', redirect: '/admin/groups' },
  { path: '/admin/system/notifications', redirect: '/admin/notifications' },
  { path: '/admin/system/alerts', redirect: '/admin/alerts' },

  // 系统旧路径（/system/* → /admin/*）
  { path: '/system/status', redirect: '/admin' },
  { path: '/system/workers', redirect: '/admin/workers' },
  { path: '/system/api-keys', redirect: '/admin/api-keys' },
  { path: '/system/users', redirect: '/admin/users' },
  { path: '/system/groups', redirect: '/admin/groups' },
  { path: '/system/notifications', redirect: '/admin/notifications' },
  { path: '/system/alerts', redirect: '/admin/alerts' },

  // 404
  { path: '/:pathMatch(.*)*', name: 'NotFound', component: () => import('@/views/NotFound.vue'), meta: { title: '页面未找到' } },
]
```

- [ ] **Step 2: 验证编译通过**

Run: `cd /home/kaoru/Ginkgo/web-ui && npx vue-tsc --noEmit 2>&1 | head -20`
Expected: 无类型错误

- [ ] **Step 3: Commit**

```bash
git add web-ui/src/router/index.ts
git commit -m "refactor(web-ui): promote components to top-level, flatten admin routes"
```

---

### Task 3: 通过远端浏览器验证

**Files:** 无文件变更

- [ ] **Step 1: 确认 dev server 运行**

Run: `curl -s -o /dev/null -w "%{http_code}" http://192.168.50.12:5173/`
Expected: 200

如果未运行，启动 dev server: `cd /home/kaoru/Ginkgo/web-ui && npx vite --host 0.0.0.0 --port 5173 &`

- [ ] **Step 2: 验证 7 个侧边栏导航**

通过远端浏览器（`http://192.168.50.10:9222`）访问 `http://192.168.50.12:5173/dashboard`，截图确认侧边栏显示 7 项：工作台、组合、组件、研究、交易、数据、管理。

- [ ] **Step 3: 逐项点击验证导航**

点击每个菜单项，确认跳转到正确路由：
- 工作台 → `/dashboard`（200）
- 组合 → `/portfolios`（200）
- 组件 → `/components`（200，显示组件库页面）
- 研究 → `/research`（重定向到 `/research/factor`）
- 交易 → `/trading`（重定向到 `/trading/paper`）
- 数据 → `/data`（200）
- 管理 → `/admin`（200，显示系统状态页面）

- [ ] **Step 4: 验证关键旧路由重定向**

直接访问以下 URL 确认重定向：
- `/admin/components` → `/components`
- `/admin/components/strategies` → `/components/strategies`
- `/admin/system` → `/admin`
- `/admin/system/workers` → `/admin/workers`
- `/system/status` → `/admin`
- `/portfolio` → `/portfolios`

- [ ] **Step 5: 最终 commit（如有遗漏修复）**

```bash
git add -A
git commit -m "fix(web-ui): address navigation verification findings"
```

---

## Self-Review

**1. Spec coverage:**
- 7 顶层菜单 ✅ Task 1（App.vue menuItems）
- 组件独立入口 `/components/*` ✅ Task 2（路由）
- Admin 扁平化 `/admin/*` ✅ Task 2（路由）
- 旧路由重定向 ✅ Task 2（全部旧路径 → 新路径）
- 视觉主题不变 ✅ 不涉及
- 0 功能删除 ✅ 只改路径，不改组件

**2. Placeholder scan:** 无 TBD/TODO/填空。

**3. Type consistency:** 路由 name 与组件映射一致。App.vue 中的 key（`'components'`）与 routeToKeyMap 和 getRouteForKey 统一。
