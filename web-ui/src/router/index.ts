import { createRouter, createWebHistory, RouteRecordRaw } from 'vue-router'
import { isAuthenticated } from '@/api'

const routes: RouteRecordRaw[] = [
  // 登录页面 (无需认证)
  { path: '/login', name: 'Login', component: () => import('@/views/auth/Login.vue'), meta: { title: '登录', requiresAuth: false } },

  // 重定向
  { path: '/', redirect: '/dashboard' },

  // Dashboard 概览
  { path: '/dashboard', name: 'Dashboard', component: () => import('@/views/dashboard/Dashboard.vue'), meta: { title: '概览', requiresAuth: true } },

  // Portfolio 投资组合
  { path: '/portfolio', name: 'PortfolioList', component: () => import('@/views/portfolio/PortfolioList.vue'), meta: { title: '组合列表' } },
  { path: '/portfolio/create', name: 'PortfolioCreate', component: () => import('@/views/portfolio/PortfolioFormEditor.vue'), meta: { title: '创建组合' } },
  { path: '/portfolio/:id', name: 'PortfolioDetail', component: () => import('@/views/portfolio/PortfolioDetail.vue'), meta: { title: '组合详情' } },
  { path: '/portfolio/:id/edit', name: 'PortfolioEdit', component: () => import('@/views/portfolio/PortfolioFormEditor.vue'), meta: { title: '编辑组合' } },

  // ===== 回测 =====
  { path: '/backtest', name: 'BacktestList', component: () => import('@/views/stage1/BacktestList.vue'), meta: { title: '回测列表' } },
  { path: '/backtest/create', name: 'BacktestCreate', component: () => import('@/views/stage1/BacktestCreate.vue'), meta: { title: '创建回测' } },
  { path: '/backtest/:id', name: 'BacktestDetail', component: () => import('@/views/stage1/BacktestDetail.vue'), meta: { title: '回测详情' } },
  { path: '/backtest/compare', name: 'BacktestCompare', component: () => import('@/views/stage1/BacktestCompare.vue'), meta: { title: '回测对比' } },

  // ===== 验证 =====
  { path: '/validation/walkforward', name: 'WalkForwardValidation', component: () => import('@/views/stage2/WalkForward.vue'), meta: { title: '走步验证' } },
  { path: '/validation/montecarlo', name: 'MonteCarloSimulation', component: () => import('@/views/stage2/MonteCarlo.vue'), meta: { title: '蒙特卡洛模拟' } },
  { path: '/validation/sensitivity', name: 'SensitivityAnalysis', component: () => import('@/views/stage2/Sensitivity.vue'), meta: { title: '敏感性分析' } },

  // ===== 模拟交易 =====
  { path: '/paper', name: 'PaperTrading', component: () => import('@/views/stage3/PaperTrading.vue'), meta: { title: '模拟交易' } },
  { path: '/paper/orders', name: 'PaperTradingOrders', component: () => import('@/views/stage3/PaperTradingOrders.vue'), meta: { title: '订单记录' } },

  // ===== 实盘交易 =====
  { path: '/live', name: 'LiveTrading', component: () => import('@/views/stage4/LiveTrading.vue'), meta: { title: '实盘监控' } },
  { path: '/live/orders', name: 'LiveOrders', component: () => import('@/views/stage4/LiveOrders.vue'), meta: { title: '订单管理' } },
  { path: '/live/positions', name: 'LivePositions', component: () => import('@/views/stage4/LivePositions.vue'), meta: { title: '持仓管理' } },
  { path: '/live/account-config', name: 'LiveAccountConfig', component: () => import('@/views/live/AccountConfig.vue'), meta: { title: '实盘账号配置' } },
  { path: '/live/account-info', name: 'LiveAccountInfo', component: () => import('@/views/live/AccountInfo.vue'), meta: { title: '账户信息' } },
  { path: '/live/broker-management', name: 'BrokerManagement', component: () => import('@/views/live/BrokerManagement.vue'), meta: { title: 'Broker 管理' } },
  { path: '/live/trade-history', name: 'LiveTradeHistory', component: () => import('@/views/live/TradeHistory.vue'), meta: { title: '交易历史' } },
  { path: '/live/trading-control', name: 'TradingControl', component: () => import('@/views/live/TradingControl.vue'), meta: { title: '交易控制' } },
  { path: '/live/market', name: 'MarketData', component: () => import('@/views/stage4/MarketData.vue'), meta: { title: '市场数据', requiresAuth: false } },

  // ===== 因子研究 =====
  { path: '/research/ic', name: 'ICAnalysis', component: () => import('@/views/research/ICAnalysis.vue'), meta: { title: 'IC 分析' } },
  { path: '/research/layering', name: 'FactorLayering', component: () => import('@/views/research/FactorLayering.vue'), meta: { title: '因子分层' } },
  { path: '/research/orthogonal', name: 'FactorOrthogonalization', component: () => import('@/views/research/FactorOrthogonalization.vue'), meta: { title: '因子正交化' } },
  { path: '/research/comparison', name: 'FactorComparison', component: () => import('@/views/research/FactorComparison.vue'), meta: { title: '因子比较' } },
  { path: '/research/decay', name: 'FactorDecay', component: () => import('@/views/research/FactorDecay.vue'), meta: { title: '因子衰减' } },

  // ===== 参数优化 =====
  { path: '/optimization/grid', name: 'GridSearch', component: () => import('@/views/optimization/GridSearch.vue'), meta: { title: '网格搜索' } },
  { path: '/optimization/genetic', name: 'GeneticOptimizer', component: () => import('@/views/optimization/GeneticOptimizer.vue'), meta: { title: '遗传算法' } },
  { path: '/optimization/bayesian', name: 'BayesianOptimizer', component: () => import('@/views/optimization/BayesianOptimizer.vue'), meta: { title: '贝叶斯优化' } },

  // ===== 组件管理 =====
  { path: '/components/strategies', name: 'StrategyList', component: () => import('@/views/components/StrategyList.vue'), meta: { title: '策略组件' } },
  { path: '/components/strategies/:id', name: 'StrategyDetail', component: () => import('@/views/components/ComponentDetail.vue'), meta: { title: '编辑策略' } },
  { path: '/components/risks', name: 'RiskList', component: () => import('@/views/components/RiskList.vue'), meta: { title: '风控组件' } },
  { path: '/components/risks/:id', name: 'RiskDetail', component: () => import('@/views/components/ComponentDetail.vue'), meta: { title: '编辑风控' } },
  { path: '/components/sizers', name: 'SizerList', component: () => import('@/views/components/SizerList.vue'), meta: { title: '仓位组件' } },
  { path: '/components/sizers/:id', name: 'SizerDetail', component: () => import('@/views/components/ComponentDetail.vue'), meta: { title: '编辑仓位' } },
  { path: '/components/selectors', name: 'SelectorList', component: () => import('@/views/components/SelectorList.vue'), meta: { title: '选股器' } },
  { path: '/components/selectors/:id', name: 'SelectorDetail', component: () => import('@/views/components/ComponentDetail.vue'), meta: { title: '编辑选股器' } },
  { path: '/components/analyzers', name: 'AnalyzerList', component: () => import('@/views/components/AnalyzerList.vue'), meta: { title: '分析器' } },
  { path: '/components/analyzers/:id', name: 'AnalyzerDetail', component: () => import('@/views/components/ComponentDetail.vue'), meta: { title: '编辑分析器' } },
  { path: '/components/handlers', name: 'HandlerList', component: () => import('@/views/components/HandlerList.vue'), meta: { title: '事件处理器' } },
  { path: '/components/handlers/:id', name: 'HandlerDetail', component: () => import('@/views/components/ComponentDetail.vue'), meta: { title: '编辑处理器' } },

  // ===== 数据管理 =====
  { path: '/data', name: 'DataOverview', component: () => import('@/views/data/DataOverview.vue'), meta: { title: '数据概览' } },
  { path: '/data/stocks', name: 'StockList', component: () => import('@/views/data/StockList.vue'), meta: { title: '股票信息' } },
  { path: '/data/bars', name: 'BarData', component: () => import('@/views/data/BarData.vue'), meta: { title: 'K线数据' } },
  { path: '/data/sync', name: 'DataSync', component: () => import('@/views/data/DataSync.vue'), meta: { title: '数据同步' } },

  // ===== 系统管理 =====
  { path: '/system/status', name: 'SystemStatus', component: () => import('@/views/system/SystemStatus.vue'), meta: { title: '系统状态' } },
  { path: '/system/workers', name: 'WorkerManagement', component: () => import('@/views/system/WorkerManagement.vue'), meta: { title: 'Worker 管理' } },
  { path: '/system/api-keys', name: 'ApiKeyManagement', component: () => import('@/views/system/ApiKeyManagement.vue'), meta: { title: 'API Key 管理' } },
  { path: '/system/users', name: 'UserManagement', component: () => import('@/views/settings/UserManagement.vue'), meta: { title: '用户管理' } },
  { path: '/system/groups', name: 'UserGroupManagement', component: () => import('@/views/settings/UserGroupManagement.vue'), meta: { title: '用户组管理' } },
  { path: '/system/notifications', name: 'NotificationManagement', component: () => import('@/views/settings/NotificationManagement.vue'), meta: { title: '通知管理' } },
  { path: '/system/alerts', name: 'AlertCenter', component: () => import('@/views/system/AlertCenter.vue'), meta: { title: '告警中心' } },

  // 404
  { path: '/:pathMatch(.*)*', name: 'NotFound', component: () => import('@/views/NotFound.vue'), meta: { title: '页面未找到' } },
]

const router = createRouter({
  history: createWebHistory(),
  routes,
})

// 路由守卫 - 认证检查
router.beforeEach((to, from, next) => {
  // 设置页面标题
  document.title = `${to.meta?.title || 'Ginkgo'} - 量化交易平台`

  // 检查是否需要认证
  const requiresAuth = to.meta?.requiresAuth !== false // 默认需要认证

  if (requiresAuth && !isAuthenticated()) {
    // 需要认证但未登录，跳转登录页
    next({ path: '/login', query: { redirect: to.fullPath } })
  } else if (to.path === '/login' && isAuthenticated()) {
    // 已登录访问登录页，跳转首页
    next({ path: '/' })
  } else {
    next()
  }
})

export default router
