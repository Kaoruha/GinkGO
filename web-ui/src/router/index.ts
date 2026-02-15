import { createRouter, createWebHistory, RouteRecordRaw } from 'vue-router'

// 布局组件
import ComponentLayout from '@/layouts/ComponentLayout.vue'
import EmptyLayout from '@/layouts/EmptyLayout.vue'

// 页面组件（懒加载）
const Dashboard = () => import('@/views/Dashboard/index.vue')
const PortfolioList = () => import('@/views/Portfolio/PortfolioList.vue')
const PortfolioDetail = () => import('@/views/Portfolio/PortfolioDetail.vue')
const PortfolioFormEditor = () => import('@/views/Portfolio/PortfolioFormEditor.vue')
const BacktestList = () => import('@/views/Backtest/BacktestList.vue')
const BacktestDetail = () => import('@/views/Backtest/BacktestDetail.vue')
const BacktestCreate = () => import('@/views/Backtest/BacktestCreate.vue')
const BacktestResult = () => import('@/views/Backtest/BacktestResult.vue')
const BacktestCompare = () => import('@/views/Backtest/BacktestCompare.vue')
const BacktestLogs = () => import('@/views/Backtest/BacktestLogs.vue')
const ComponentList = () => import('@/views/Components/ComponentList.vue')
const ComponentListHeader = () => import('@/views/Components/ComponentListHeader.vue')
const ComponentDetail = () => import('@/views/Components/ComponentDetail.vue')
const ComponentEditor = () => import('@/views/Components/ComponentEditor.vue')
const ComponentEditorHeader = () => import('@/views/Components/ComponentEditorHeader.vue')
const DataManagement = () => import('@/views/Data/DataManagement.vue')
const AlertCenter = () => import('@/views/Alert/AlertCenter.vue')
const Login = () => import('@/views/Auth/Login.vue')

// 研究模块页面
const FactorViewer = () => import('@/views/Research/FactorViewer.vue')
const ICAnalysis = () => import('@/views/Research/ICAnalysis.vue')
const LayeringBacktest = () => import('@/views/Research/LayeringBacktest.vue')
const FactorComparison = () => import('@/views/Research/FactorComparison.vue')
const FactorOrthogonalization = () => import('@/views/Research/FactorOrthogonalization.vue')
const FactorDecay = () => import('@/views/Research/FactorDecay.vue')
const FactorTurnover = () => import('@/views/Research/FactorTurnover.vue')
const PortfolioBuilder = () => import('@/views/Research/PortfolioBuilder.vue')

// 交易模块页面
const PaperTrading = () => import('@/views/Trading/PaperTrading.vue')
const PaperTradingConfig = () => import('@/views/Trading/PaperTradingConfig.vue')
const LiveTrading = () => import('@/views/Trading/LiveTrading.vue')
const OrderManagement = () => import('@/views/Trading/OrderManagement.vue')

// 验证模块页面
const ParameterOptimizer = () => import('@/views/Validation/ParameterOptimizer.vue')
const OutOfSampleTest = () => import('@/views/Validation/OutOfSampleTest.vue')
const SensitivityAnalysis = () => import('@/views/Validation/SensitivityAnalysis.vue')
const MonteCarloSim = () => import('@/views/Validation/MonteCarloSim.vue')

// 设置页面组件
const UserManagement = () => import('@/views/Settings/UserManagement.vue')
const UserGroupManagement = () => import('@/views/Settings/UserGroupManagement.vue')
const NotificationManagement = () => import('@/views/Settings/NotificationManagement.vue')
const APIInterfaces = () => import('@/views/Settings/APIInterfaces.vue')

const routes: RouteRecordRaw[] = [
  {
    path: '/login',
    component: EmptyLayout,
    children: [
      { path: '', component: Login }
    ]
  },
  {
    path: '/',
    component: ComponentLayout,
    children: [
      { path: '', component: Dashboard, name: 'dashboard' }
    ]
  },
  {
    path: '/portfolio',
    component: ComponentLayout,
    children: [
      { path: '', component: PortfolioList, name: 'portfolio-list' },
      { path: 'create', component: PortfolioFormEditor, name: 'portfolio-create' },
      { path: ':uuid/edit', component: PortfolioFormEditor, name: 'portfolio-edit' },
      { path: ':uuid', component: PortfolioDetail, name: 'portfolio-detail' }
    ]
  },
  {
    path: '/backtest',
    component: ComponentLayout,
    children: [
      { path: '', component: BacktestList, name: 'backtest-list' },
      { path: ':uuid', component: BacktestDetail, name: 'backtest-detail' },
      { path: 'create', component: BacktestCreate, name: 'backtest-create' },
      { path: 'report/:uuid', component: BacktestResult, name: 'backtest-report' },
      { path: 'compare', component: BacktestCompare, name: 'backtest-compare' },
      { path: 'logs/:uuid', component: BacktestLogs, name: 'backtest-logs' }
    ]
  },
  {
    path: '/components',
    component: ComponentLayout,
    children: [
      {
        path: '',
        components: {
          default: ComponentList,
          header: ComponentListHeader
        },
        name: 'component-list'
      },
      { path: ':uuid', component: ComponentDetail, name: 'component-detail' },
      {
        path: ':uuid/edit',
        components: {
          default: ComponentEditor,
          header: ComponentEditorHeader
        },
        name: 'component-edit'
      }
    ]
  },
  {
    path: '/data',
    component: ComponentLayout,
    children: [
      { path: '', component: DataManagement, name: 'data-management' }
    ]
  },
  {
    path: '/settings',
    component: ComponentLayout,
    children: [
      {
        path: '',
        redirect: '/settings/users',
        name: 'settings'
      },
      {
        path: 'users',
        component: UserManagement,
        name: 'settings-users'
      },
      {
        path: 'user-groups',
        component: UserGroupManagement,
        name: 'settings-user-groups'
      },
      {
        path: 'notifications',
        component: NotificationManagement,
        name: 'settings-notifications'
      },
      {
        path: 'api',
        component: APIInterfaces,
        name: 'settings-api'
      }
    ]
  },
  {
    path: '/alert',
    component: ComponentLayout,
    children: [
      { path: '', component: AlertCenter, name: 'alert-center' }
    ]
  },
  {
    path: '/research',
    component: ComponentLayout,
    children: [
      { path: '', component: FactorViewer, name: 'research-factor' },
      { path: 'ic-analysis', component: ICAnalysis, name: 'research-ic' },
      { path: 'layering', component: LayeringBacktest, name: 'research-layering' },
      { path: 'comparison', component: FactorComparison, name: 'research-compare' },
      { path: 'orthogonalization', component: FactorOrthogonalization, name: 'research-orthogonalization' },
      { path: 'decay', component: FactorDecay, name: 'research-decay' },
      { path: 'turnover', component: FactorTurnover, name: 'research-turnover' },
      { path: 'portfolio-builder', component: PortfolioBuilder, name: 'research-portfolio-builder' }
    ]
  },
  {
    path: '/trading',
    component: ComponentLayout,
    children: [
      { path: '', redirect: '/trading/paper', name: 'trading' },
      { path: 'paper', component: PaperTrading, name: 'trading-paper' },
      { path: 'paper/config', component: PaperTradingConfig, name: 'trading-paper-config' },
      { path: 'live', component: LiveTrading, name: 'trading-live' },
      { path: 'orders', component: OrderManagement, name: 'trading-orders' }
    ]
  },
  {
    path: '/validation',
    component: ComponentLayout,
    children: [
      { path: '', redirect: '/validation/optimizer', name: 'validation' },
      { path: 'optimizer', component: ParameterOptimizer, name: 'validation-optimizer' },
      { path: 'out-of-sample', component: OutOfSampleTest, name: 'validation-oos' },
      { path: 'sensitivity', component: SensitivityAnalysis, name: 'validation-sensitivity' },
      { path: 'monte-carlo', component: MonteCarloSim, name: 'validation-mc' }
    ]
  }
]

const router = createRouter({
  history: createWebHistory(import.meta.env.BASE_URL),
  routes
})

// 路由守卫 - 认证检查
router.beforeEach((to, from, next) => {
  const token = localStorage.getItem('access_token')

  if (to.path !== '/login' && !token) {
    next('/login')
  } else if (to.path === '/login' && token) {
    next('/')
  } else {
    next()
  }
})

export default router
