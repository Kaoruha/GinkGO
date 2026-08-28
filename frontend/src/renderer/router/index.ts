import { createRouter, createWebHashHistory, RouteRecordRaw } from 'vue-router'
import { isAuthenticated, getStoredUser } from '@/api'

const routes: RouteRecordRaw[] = [
  // ===== 登录 =====
  { path: '/login', name: 'Login', component: () => import('@/views/auth/Login.vue'), meta: { title: '登录', requiresAuth: false } },

  // ===== 根重定向 =====
  { path: '/', redirect: '/dashboard' },

  // ===== 概览 =====
  { path: '/dashboard', name: 'Dashboard', component: () => import('@/views/dashboard/Dashboard.vue'), meta: { title: '概览' } },

  // ===== 组合 =====
  { path: '/portfolios', name: 'PortfolioList', component: () => import('@/views/portfolio/PortfolioList.vue'), meta: { title: '组合列表' } },
  { path: '/portfolios/create', name: 'PortfolioCreate', component: () => import('@/views/portfolio/PortfolioFormEditor.vue'), meta: { title: '创建组合' } },
  {
    path: '/portfolios/:id',
    component: () => import('@/views/portfolio/PortfolioDetail.vue'),
    children: [
      { path: '', name: 'PortfolioDetail', component: () => import('@/views/portfolio/tabs/OverviewTab.vue'), meta: { title: '组合详情' } },
      { path: 'paper', name: 'PortfolioPaper', component: () => import('@/views/portfolio/tabs/PaperTab.vue'), meta: { title: '模拟盘' } },
      { path: 'live', name: 'PortfolioLive', component: () => import('@/views/portfolio/tabs/LiveTab.vue'), meta: { title: '实盘' } },
      { path: 'backtests', name: 'PortfolioBacktests', component: () => import('@/views/portfolio/tabs/BacktestTab.vue'), meta: { title: '回测' } },
      // 回测详情已提为顶级路由 /backtests/:uuid(BacktestDetailPage),旧嵌套路径 redirect 兼容
      { path: 'backtests/:backtestId', redirect: to => `/backtests/${to.params.backtestId}` },
      { path: 'validation', name: 'PortfolioValidation', component: () => import('@/views/portfolio/tabs/ValidationTab.vue'), meta: { title: '验证' } },
      { path: 'components', name: 'PortfolioComponents', component: () => import('@/views/portfolio/tabs/ComponentsTab.vue'), meta: { title: '组件' } },
    ],
  },
  { path: '/portfolios/:id/edit', name: 'PortfolioEdit', component: () => import('@/views/portfolio/PortfolioFormEditor.vue'), meta: { title: '编辑组合' } },

  // ===== 组件库（二级菜单已并入 AppSider,叶子路由直达;无 type 时空态,直达默认类型） =====
  { path: '/components', name: 'Components', redirect: '/components/strategies' },
  { path: '/components/:type', name: 'ComponentList', component: () => import('@/views/components/ComponentListPage.vue'), meta: { title: '组件列表' } },
  { path: '/components/:type/:id', name: 'ComponentDetail', component: () => import('@/views/components/ComponentDetail.vue'), meta: { title: '组件详情' } },

  // ===== 研究 =====
  { path: '/research', name: 'Research', redirect: '/research/factor/ic', meta: { title: '研究' } },
  { path: '/research/factor', redirect: '/research/factor/ic' },
  { path: '/research/factor/ic', name: 'ICAnalysis', component: () => import('@/views/research/ICAnalysis.vue'), meta: { title: 'IC 分析' } },
  { path: '/research/factor/layering', name: 'FactorLayering', component: () => import('@/views/research/FactorLayering.vue'), meta: { title: '因子分层' } },
  { path: '/research/factor/orthogonal', name: 'FactorOrthogonalization', component: () => import('@/views/research/FactorOrthogonalization.vue'), meta: { title: '因子正交化' } },
  { path: '/research/factor/comparison', name: 'FactorComparison', component: () => import('@/views/research/FactorComparison.vue'), meta: { title: '因子比较' } },
  { path: '/research/factor/decay', name: 'FactorDecay', component: () => import('@/views/research/FactorDecay.vue'), meta: { title: '因子衰减' } },
  { path: '/research/optimization', name: 'Optimization', redirect: '/research/optimization/grid' },
  { path: '/research/optimization/grid', name: 'GridSearch', component: () => import('@/views/optimization/GridSearch.vue'), meta: { title: '网格搜索' } },
  { path: '/research/optimization/genetic', name: 'GeneticOptimizer', component: () => import('@/views/optimization/GeneticOptimizer.vue'), meta: { title: '遗传算法' } },
  { path: '/research/optimization/bayesian', name: 'BayesianOptimizer', component: () => import('@/views/optimization/BayesianOptimizer.vue'), meta: { title: '贝叶斯优化' } },

  // ===== 回测中心 =====
  { path: '/backtests', name: 'BacktestCenter', component: () => import('@/views/backtest/BacktestListPage.vue'), meta: { title: '回测中心' } },
  // 评估: 必须注册在 /backtests/:uuid 之前, 否则 "evaluation" 被当作 uuid 解析
  { path: '/backtests/evaluation', name: 'EvaluationWorkbench', component: () => import('@/views/backtest/EvaluationWorkbench.vue'), meta: { title: '评估' } },
  { path: '/backtests/:uuid', name: 'BacktestDetail', component: () => import('@/views/backtest/BacktestDetailPage.vue'), meta: { title: '回测详情' } },

  // ===== 交易 =====
  { path: '/trading', redirect: '/trading/paper' },
  { path: '/trading/paper', name: 'TradingPaper', component: () => import('@/views/trading/PaperTrading.vue'), meta: { title: '模拟盘监控' } },
  { path: '/trading/live', name: 'TradingLive', component: () => import('@/views/live/LiveTrading.vue'), meta: { title: '实盘监控' } },
  { path: '/trading/live/accounts', name: 'LiveAccountConfig', component: () => import('@/views/live/AccountConfig.vue'), meta: { title: '账号配置' } },
  { path: '/trading/live/monitor', name: 'LiveAccountInfo', component: () => import('@/views/live/AccountInfo.vue'), meta: { title: '账户监控' } },
  { path: '/trading/live/brokers', name: 'LiveBrokers', component: () => import('@/views/live/BrokerManagement.vue'), meta: { title: 'Broker 管理' } },
  { path: '/trading/live/market', name: 'MarketData', component: () => import('@/views/live/MarketData.vue'), meta: { title: '市场数据', requiresAuth: false } },
  { path: '/trading/live/history', name: 'TradeHistory', component: () => import('@/views/live/TradeHistory.vue'), meta: { title: '交易历史' } },

  // ===== 数据(2026-08-18 重构:浏览 4 页合一为 DataBrowser,旧路由 redirect 保深链) =====
  { path: '/data', name: 'DataOverview', component: () => import('@/views/data/DataOverview.vue'), meta: { title: '数据概览' } },
  { path: '/data/browser', name: 'DataBrowser', component: () => import('@/views/data/DataBrowser.vue'), meta: { title: '数据浏览' } },
  { path: '/data/stocks', redirect: { path: '/data/browser', query: { type: 'stocks' } } },
  { path: '/data/bars', redirect: { path: '/data/browser', query: { type: 'bars' } } },
  { path: '/data/ticks', redirect: { path: '/data/browser', query: { type: 'ticks' } } },
  { path: '/data/adjustfactors', redirect: { path: '/data/browser', query: { type: 'adjust' } } },
  { path: '/data/sync', name: 'DataSync', component: () => import('@/views/data/DataSync.vue'), meta: { title: '数据同步' } },

  // ===== 管理（系统级功能,叶子路由直达） =====
  { path: '/admin', name: 'Admin', component: () => import('@/views/admin/SystemStatus.vue'), meta: { title: '系统状态' } },
  // 2026-08-19 Worker 管理页并入系统状态(数据同源+同表,无独占操作),redirect 保深链
  { path: '/admin/workers', redirect: '/admin' },
  { path: '/admin/api-keys', name: 'ApiKeyManagement', component: () => import('@/views/admin/ApiKeyManagement.vue'), meta: { title: 'API Key 管理' } },
  { path: '/admin/users', name: 'UserManagement', component: () => import('@/views/admin/UserManagement.vue'), meta: { title: '用户管理' } },
  { path: '/admin/groups', name: 'UserGroupManagement', component: () => import('@/views/admin/UserGroupManagement.vue'), meta: { title: '用户组管理' } },
  { path: '/admin/notifications', name: 'NotificationManagement', component: () => import('@/views/admin/NotificationManagement.vue'), meta: { title: '通知管理' } },
  { path: '/admin/alerts', name: 'AlertCenter', component: () => import('@/views/admin/AlertCenter.vue'), meta: { title: '告警中心' } },
  { path: '/admin/task-timer', name: 'TaskTimerHistory', component: () => import('@/views/admin/TaskTimerHistory.vue'), meta: { title: '定时任务' } },
  { path: '/admin/maintenance', name: 'DataMaintenance', component: () => import('@/views/admin/DataMaintenance.vue'), meta: { title: '数据清理' } },

  // ===== 旧路由兼容重定向 =====
  // 组合 singular → plural
  { path: '/portfolio', redirect: '/portfolios' },
  { path: '/portfolio/create', redirect: '/portfolios/create' },
  { path: '/portfolio/:id', redirect: to => `/portfolios/${to.params.id}` },
  { path: '/portfolio/:id/edit', redirect: to => `/portfolios/${to.params.id}/edit` },
  // 回测 → 回测中心
  { path: '/backtest', redirect: '/backtests' },
  { path: '/backtest/create', redirect: '/backtests' },
  { path: '/backtest/:id', redirect: to => `/backtests/${to.params.id}` },
  { path: '/backtest/compare', redirect: '/backtests' },
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
  { path: '/live/account-config', redirect: '/trading/live/accounts' },
  { path: '/live/account-info', redirect: '/trading/live/monitor' },
  { path: '/live/broker-management', redirect: '/trading/live/brokers' },
  { path: '/live/trade-history', redirect: '/trading/live/history' },
  { path: '/live/trading-control', redirect: '/trading/live/brokers' },
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
  { path: '/:pathMatch(.*)*', name: 'NotFound', component: () => import('@/views/NotFound.vue'), meta: { title: '页面未找到', fullPage: true } },
]

const router = createRouter({
  // hash 模式:Electron 下 file://app:// 直接刷新不 404;浏览器形态兼容
  history: createWebHashHistory(),
  routes,
})

// 路由守卫 - 认证检查
// isAuthenticated 已异步化(Electron 形态走 IPC),守卫须 await
router.beforeEach(async (to, _from, next) => {
  document.title = `${to.meta?.title || 'Ginkgo'} - 量化交易平台`
  const requiresAuth = to.meta?.requiresAuth !== false
  // 判定与 App.vue 布局分支同源(2026-08-19):token && user 双要素。
  // 只查 token 存在时,过期 token 残留 + user_info 已被清理的中间态会
  // 被放行进主路由,而布局层 isLoggedIn=false 落入裸 router-view——
  // 页面有内容但无侧边栏无报错(实测用户"登录后不见侧边导航"根因)。
  const authed = (await isAuthenticated()) && !!getStoredUser()
  if (requiresAuth && !authed) {
    next({ path: '/login', query: { redirect: to.fullPath } })
  } else if (to.path === '/login' && authed) {
    next({ path: '/' })
  } else {
    next()
  }
})

export default router
