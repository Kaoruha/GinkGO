import { createRouter, createWebHistory } from 'vue-router'
import HomeView from '../views/HomeView.vue'
import SummaryView from '../views/SummaryView.vue'
import LiveView from '../views/LiveView.vue'
import BacktestView from '../views/BacktestView.vue'
import DataView2 from '../views/DataView.vue'
import FileView from '../views/FileView.vue'
import TestView from '../views/TestView.vue'

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
      component: TestView
    },
    {
      path: '/about',
      name: 'about',
      // route level code-splitting
      // this generates a separate chunk (About.[hash].js) for this route
      // which is lazy-loaded when the route is visited.
      component: () => import('../views/AboutView.vue')
    }
  ]
})

export default router
