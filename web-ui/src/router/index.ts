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

  // ===== 管理 =====
  { path: '/admin', name: 'Admin', redirect: '/admin/components', meta: { title: '管理' } },
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
