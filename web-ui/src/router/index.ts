import { createRouter, createWebHistory, RouteRecordRaw } from 'vue-router'

// 布局组件
import ComponentLayout from '@/layouts/ComponentLayout.vue'
import EmptyLayout from '@/layouts/EmptyLayout.vue'

// 页面组件（懒加载）
const Dashboard = () => import('@/views/Dashboard/index.vue')
const PortfolioList = () => import('@/views/Portfolio/PortfolioList.vue')
const PortfolioDetail = () => import('@/views/Portfolio/PortfolioDetail.vue')
const BacktestList = () => import('@/views/Backtest/BacktestList.vue')
const BacktestCreate = () => import('@/views/Backtest/BacktestCreate.vue')
const BacktestGraphEditor = () => import('@/views/BacktestGraphEditor.vue')
const ComponentList = () => import('@/views/Components/ComponentList.vue')
const ComponentListHeader = () => import('@/views/Components/ComponentListHeader.vue')
const ComponentDetail = () => import('@/views/Components/ComponentDetail.vue')
const ComponentEditor = () => import('@/views/Components/ComponentEditor.vue')
const ComponentEditorHeader = () => import('@/views/Components/ComponentEditorHeader.vue')
const DataManagement = () => import('@/views/Data/DataManagement.vue')
const AlertCenter = () => import('@/views/Alert/AlertCenter.vue')
const Login = () => import('@/views/Auth/Login.vue')

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
      { path: ':uuid', component: PortfolioDetail, name: 'portfolio-detail' }
    ]
  },
  {
    path: '/backtest',
    component: ComponentLayout,
    children: [
      { path: '', component: BacktestList, name: 'backtest-list' },
      { path: 'create', component: BacktestCreate, name: 'backtest-create' },
      { path: 'graph-editor/:uuid?', component: BacktestGraphEditor, name: 'backtest-graph-editor' }
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
