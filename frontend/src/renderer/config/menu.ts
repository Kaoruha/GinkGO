import type { Component } from 'vue'
import {
  LayoutDashboard, Wallet, TrendingUp,
  Wrench, Database, FileSearch, Puzzle,
} from 'lucide-vue-next'

/**
 * 菜单单一配置源。
 * 原先 menuItems / routeToKeyMap / getRouteForKey 三份冗余配置合并于此。
 * menuConfigs 既描述菜单项(供 AppSider 渲染),又派生路径↔key 映射。
 * 两级导航:有 children 的模块在最左栏就地展开(宽态手风琴)/ hover 弹出(折叠态 flyout),
 * 内层不再有二级菜单壳。
 */

/** 可点的二级菜单项 */
export interface MenuChild {
  label: string
  route: string
  /** 精确高亮(模块根路由,如 /admin、/trading/live,避免在所有子页都亮) */
  exact?: boolean
}

export interface MenuConfig {
  key: string
  label: string
  icon: Component
  /** 主路由路径(精确匹配 + 菜单跳转目标) */
  route: string
  /** 额外的高亮匹配前缀(子路由高亮,如 /portfolios/:id) */
  matchPrefixes?: string[]
  /** 二级菜单项;有 children 的模块走两级导航,无则一级直达 */
  children?: MenuChild[]
}

export const menuConfigs: MenuConfig[] = [
  { key: 'dashboard', label: '概览', icon: LayoutDashboard, route: '/dashboard' },
  { key: 'portfolios', label: '组合', icon: Wallet, route: '/portfolios', matchPrefixes: ['/portfolios/'] },
  {
    key: 'backtests', label: '回测', icon: TrendingUp, route: '/backtests', matchPrefixes: ['/backtests/'],
    children: [
      { label: '回测列表', route: '/backtests', exact: true },
      { label: '评估', route: '/backtests/evaluation' },
    ],
  },
  {
    key: 'components', label: '组件', icon: Puzzle, route: '/components', matchPrefixes: ['/components/'],
    children: [
      { label: '策略组件', route: '/components/strategies' },
      { label: '风控组件', route: '/components/risks' },
      { label: '仓位组件', route: '/components/sizers' },
      { label: '选股器', route: '/components/selectors' },
      { label: '分析器', route: '/components/analyzers' },
    ],
  },
  {
    key: 'research', label: '研究', icon: FileSearch, route: '/research', matchPrefixes: ['/research/'],
    children: [
      { label: '因子分析', route: '/research/factor' },
      { label: '参数优化', route: '/research/optimization' },
    ],
  },
  {
    key: 'trading', label: '交易', icon: TrendingUp, route: '/trading', matchPrefixes: ['/trading/'],
    children: [
      { label: '模拟盘', route: '/trading/paper' },
      { label: '概览', route: '/trading/live', exact: true },
      { label: '账号配置', route: '/trading/live/accounts' },
      { label: '账户监控', route: '/trading/live/monitor' },
      { label: 'Broker', route: '/trading/live/brokers' },
      { label: '行情', route: '/trading/live/market' },
      { label: '交易历史', route: '/trading/live/history' },
    ],
  },
  {
    key: 'data', label: '数据', icon: Database, route: '/data', matchPrefixes: ['/data/'],
    children: [
      { label: '数据概览', route: '/data', exact: true },
      { label: '数据浏览', route: '/data/browser' },
      { label: '数据同步', route: '/data/sync' },
    ],
  },
  {
    key: 'admin', label: '管理', icon: Wrench, route: '/admin', matchPrefixes: ['/admin/'],
    children: [
      { label: '系统状态', route: '/admin', exact: true },
      { label: 'API Key', route: '/admin/api-keys' },
      { label: '用户管理', route: '/admin/users' },
      { label: '用户组', route: '/admin/groups' },
      { label: '通知管理', route: '/admin/notifications' },
      { label: '告警中心', route: '/admin/alerts' },
      { label: '定时任务', route: '/admin/task-timer' },
      { label: '数据清理', route: '/admin/maintenance' },
    ],
  },
]

/** key → 路由(菜单点击跳转) */
const routeByKey = Object.fromEntries(menuConfigs.map(c => [c.key, c.route]))

/**
 * 路径 → 菜单 key(路由变化时高亮)。
 * 先精确匹配主路由,再前缀匹配子路由;均未命中返回 undefined。
 */
export function keyForPath(path: string): string | undefined {
  for (const c of menuConfigs) {
    if (path === c.route) return c.key
  }
  for (const c of menuConfigs) {
    if (c.matchPrefixes?.some(p => path.startsWith(p))) return c.key
  }
  return undefined
}

export function routeForKey(key: string): string {
  return routeByKey[key] || '/'
}
