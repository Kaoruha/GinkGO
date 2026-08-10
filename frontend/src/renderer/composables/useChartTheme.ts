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
export function cssColor(varName: string, alpha?: number): string {
  const v = getComputedStyle(document.documentElement).getPropertyValue(varName).trim()
  if (!v) return '' // token 缺失,调用方回退
  return alpha != null ? `hsl(${v} / ${alpha})` : `hsl(${v})`
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
