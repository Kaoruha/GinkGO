/**
 * 图表主题适配 (ADR-045 Codex 视觉语言)
 *
 * 根因:lightweight-charts / ECharts 画在 canvas 上,CSS 变量不生效,
 * 须 JS 用 getComputedStyle 解析 token 为实际颜色串。旧代码硬编码 hex
 * 且固定单主题(浅色图深色看不见 / 深色图浅色刺眼),完全不接主题系统。
 *
 * 用法:
 *   import { useChartTheme, cssColor, upColor, downColor } from '@/composables/useChartTheme'
 *   const { theme } = useChartTheme()
 *   // createChart / setOption 时:color: cssColor('--card')
 *   // K 线涨跌:upColor() 绿涨 / downColor() 红跌 (ADR-045 西方语义)
 *   // 主题切换重绘:
 *   watch(theme, () => chart.applyOptions({ layout: { textColor: cssColor('--muted-foreground') }, ... }))
 *
 * token 存 "H S% L%" 三元组(design-tokens.css),cssColor 拼成 hsl()/hsl(/ alpha)。
 */

import { useTheme } from './useTheme'

/**
 * 读 CSS token 拼成合法颜色串。
 * @param varName  token 名,如 '--card' / '--success-fg'
 * @param alpha    0~1 透明度,给出则拼 hsl(H S% L% / alpha)
 */
const _colorCache = new Map<string, string>()

export function cssColor(varName: string, alpha?: number): string {
  const v = getComputedStyle(document.documentElement).getPropertyValue(varName).trim()
  if (!v) return '' // token 缺失,调用方回退
  // canvas 图表库(lightweight-charts/ECharts)的颜色解析器只认 rgb()/hex,
  // 不认 hsl 的任何语法(空格/逗号都抛 "Cannot parse color")。
  // 借浏览器原生 hsl→rgb 转换最可靠;按主题 attr 缓存,切换主题自动失效重算。
  const themeAttr = document.documentElement.getAttribute('data-theme') || ''
  const key = `${themeAttr}|${varName}|${alpha ?? ''}`
  const cached = _colorCache.get(key)
  if (cached) return cached
  const el = document.createElement('div')
  el.style.color = `hsl(${v})`
  el.style.display = 'none'
  document.body.appendChild(el)
  const rgb = getComputedStyle(el).color // "rgb(r, g, b)"
  el.remove()
  let out = rgb
  if (alpha != null && rgb.startsWith('rgb(')) {
    out = rgb.replace('rgb(', 'rgba(').replace(')', `, ${alpha})`)
  }
  _colorCache.set(key, out)
  return out
}

/** 涨色:ADR-045 西方语义 绿涨 */
export const upColor = (alpha?: number): string => cssColor('--success-fg', alpha)

/** 跌色:ADR-045 西方语义 红跌 */
export const downColor = (alpha?: number): string => cssColor('--error-fg', alpha)

/**
 * 图表通用色(每次调用读当前主题,主题切换后重算):
 *  - 背景 → --card(图表区与卡片底一致)
 *  - 文字 → --muted-foreground(轴标签/图例,非主文字避免抢焦)
 *  - 网格/轴线/边框 → --border
 *  - 主线 → --primary
 */
export const chartColors = {
  background: () => cssColor('--card'),
  text: () => cssColor('--muted-foreground'),
  border: () => cssColor('--border'),
  grid: () => cssColor('--border'),
  primary: () => cssColor('--primary'),
}

/** 组件内用:取响应式 theme,watch 它触发 chart.applyOptions / setOption 重绘 */
export function useChartTheme() {
  const { theme } = useTheme()
  return { theme, cssColor, upColor, downColor, chartColors }
}
