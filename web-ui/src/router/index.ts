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

  // ===== 组件库 =====
  {
    path: '/components',
    component: () => import('@/views/admin/AdminPage.vue'),
    children: [
      { path: '', name: 'Components', component: () => import('@/views/components/ComponentListPage.vue'), meta: { title: '组件库' } },
      { path: ':type', name: 'ComponentList', component: () => import('@/views/components/ComponentListPage.vue'), meta: { title: '组件列表' } },
      { path: ':type/:id', name: 'ComponentDetail', component: () => import('@/views/components/ComponentDetail.vue'), meta: { title: '组件详情' } },
    ],
  },

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

  // ===== 管理（系统级功能）=====
  {
    path: '/admin',
    component: () => import('@/views/admin/AdminLayout.vue'),
    children: [
      { path: '', name: 'Admin', component: () => import('@/views/system/SystemStatus.vue'), meta: { title: '系统状态' } },
      { path: 'workers', name: 'WorkerManagement', component: () => import('@/views/system/WorkerManagement.vue'), meta: { title: 'Worker 管理' } },
      { path: 'api-keys', name: 'ApiKeyManagement', component: () => import('@/views/system/ApiKeyManagement.vue'), meta: { title: 'API Key 管理' } },
      { path: 'users', name: 'UserManagement', component: () => import('@/views/settings/UserManagement.vue'), meta: { title: '用户管理' } },
      { path: 'groups', name: 'UserGroupManagement', component: () => import('@/views/settings/UserGroupManagement.vue'), meta: { title: '用户组管理' } },
      { path: 'notifications', name: 'NotificationManagement', component: () => import('@/views/settings/NotificationManagement.vue'), meta: { title: '通知管理' } },
      { path: 'alerts', name: 'AlertCenter', component: () => import('@/views/system/AlertCenter.vue'), meta: { title: '告警中心' } },
    ],
  },

  // ===== 旧路由兼容重定向 =====
  // 组合 singular → plural
  { path: '/portfolio', redirect: '/portfolios' },
  { path: '/portfolio/create', redirect: '/portfolios/create' },
  { path: '/portfolio/:id', redirect: to => `/portfolios/${to.params.id}` },
  { path: '/portfolio/:id/edit', redirect: to => `/portfolios/${to.params.id}/edit` },
  // 回测 → 组合
  { path: '/backtest', redirect: '/portfolios' },
  { path: '/backtest/create', redirect: '/portfolios' },
  { path: '/backtest/:id', redirect: '/portfolios' },
  { path: '/backtest/compare', redirect: '/portfolios' },
  // 验证 → 组合
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
  // 管理旧组件路径 → 新顶级组件路径
  { path: '/admin/components', redirect: '/components' },
  { path: '/admin/components/:type', redirect: to => `/components/${to.params.type}` },
  { path: '/admin/components/:type/:id', redirect: to => `/components/${to.params.type}/${to.params.id}` },
  // 管理 /admin/system/* → /admin/*
  { path: '/admin/system', redirect: '/admin' },
  { path: '/admin/system/workers', redirect: '/admin/workers' },
  { path: '/admin/system/api-keys', redirect: '/admin/api-keys' },
  { path: '/admin/system/users', redirect: '/admin/users' },
  { path: '/admin/system/groups', redirect: '/admin/groups' },
  { path: '/admin/system/notifications', redirect: '/admin/notifications' },
  { path: '/admin/system/alerts', redirect: '/admin/alerts' },
  // /system/* → /admin/*
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
