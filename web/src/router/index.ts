import { createRouter, createWebHistory } from 'vue-router'
import SummaryView from '../views/SummaryView.vue'
import LiveView from '../views/LiveView.vue'
import BacktestView from '../views/BacktestView.vue'
import DataView2 from '../views/DataView.vue'
import FileView from '../views/FileView.vue'
import JupyterView from '../views/JupyterView.vue'

const router = createRouter({
  history: createWebHistory(import.meta.env.BASE_URL),
  routes: [
    {
      path: '/',
      redirect: '/summary'
    },
    {
      path: '/summary',
      name: 'summary',
      component: SummaryView
    },
    {
      path: '/live',
      name: 'live',
      component: LiveView
    },
    {
      path: '/backtest',
      name: 'backtest',
      component: BacktestView
    },
    {
      path: '/data',
      name: 'data',
      component: DataView2
    },
    {
      path: '/file',
      name: 'file',
      component: FileView
    },
    {
      path: '/playground',
      name: 'playground',
      component: JupyterView
    }
    // {
    //   path: '/about',
    //   name: 'about',
    //   component: () => import('../views/AboutView.vue')
    // }
  ]
})

export default router
