import type { Component } from 'vue'
import {
  LayoutDashboard, Wallet, TrendingUp,
  Wrench, Database, FileSearch, Puzzle,
} from 'lucide-vue-next'

/**
 * 菜单单一配置源。
 * 原先 menuItems / routeToKeyMap / getRouteForKey 三份冗余配置合并于此。
 * menuConfigs 既描述菜单项(供 AppSider 渲染),又派生路径↔key 映射。
 */
export interface MenuConfig {
  key: string
  label: string
  icon: Component
  /** 主路由路径(精确匹配 + 菜单跳转目标) */
  route: string
  /** 额外的高亮匹配前缀(子路由高亮,如 /portfolios/:id) */
  matchPrefixes?: string[]
}

export const menuConfigs: MenuConfig[] = [
  { key: 'dashboard', label: '工作台', icon: LayoutDashboard, route: '/dashboard' },
  { key: 'portfolios', label: '组合', icon: Wallet, route: '/portfolios', matchPrefixes: ['/portfolios/'] },
  { key: 'backtests', label: '回测', icon: TrendingUp, route: '/backtests' },
  { key: 'components', label: '组件', icon: Puzzle, route: '/components', matchPrefixes: ['/components/'] },
  { key: 'research', label: '研究', icon: FileSearch, route: '/research', matchPrefixes: ['/research/'] },
  { key: 'trading', label: '交易', icon: TrendingUp, route: '/trading', matchPrefixes: ['/trading/'] },
  { key: 'data', label: '数据', icon: Database, route: '/data' },
  { key: 'admin', label: '管理', icon: Wrench, route: '/admin', matchPrefixes: ['/admin/'] },
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
