/**
 * MagicUI 风格动画预设
 * 基于 @vueuse/motion 和 Vue 3 Transition API
 */

// TransitionProps re-exported for external consumers
export type { TransitionProps } from 'vue'

// 基础过渡配置类型
export interface MagicTransition {
  name?: string
  enterActiveClass?: string
  leaveActiveClass?: string
  enterFromClass?: string
  enterToClass?: string
  leaveFromClass?: string
  leaveToClass?: string
}

// ==================== 基础动画 ====================

/**
 * 淡入淡出动画
 */
export const fadeIn: MagicTransition = {
  enterActiveClass: 'transition-opacity duration-300 ease-out',
  leaveActiveClass: 'transition-opacity duration-200 ease-in',
  enterFromClass: 'opacity-0',
  enterToClass: 'opacity-100',
  leaveFromClass: 'opacity-100',
  leaveToClass: 'opacity-0',
}

/**
 * 滑入动画
 */
export const slideIn: MagicTransition = {
  enterActiveClass: 'transition-all duration-300 ease-out',
  leaveActiveClass: 'transition-all duration-200 ease-in',
  enterFromClass: 'opacity-0 translate-y-4',
  enterToClass: 'opacity-100 translate-y-0',
  leaveFromClass: 'opacity-100 translate-y-0',
  leaveToClass: 'opacity-0 translate-y-4',
}

/**
 * 缩放动画
 */
export const scaleIn: MagicTransition = {
  enterActiveClass: 'transition-all duration-300 ease-out',
  leaveActiveClass: 'transition-all duration-200 ease-in',
  enterFromClass: 'opacity-0 scale-95',
  enterToClass: 'opacity-100 scale-100',
  leaveFromClass: 'opacity-100 scale-100',
  leaveToClass: 'opacity-0 scale-95',
}

// ==================== MagicUI 风格动画 ====================

/**
 * Magic Reveal - 魔法揭示效果
 * 类似于 MagicUI 的 reveal 动画
 */
export const magicReveal: MagicTransition = {
  enterActiveClass: 'transition-all duration-500 ease-out',
  leaveActiveClass: 'transition-all duration-200 ease-in',
  enterFromClass: 'opacity-0 scale-95 translate-y-4',
  enterToClass: 'opacity-100 scale-100 translate-y-0',
  leaveFromClass: 'opacity-100 scale-100 translate-y-0',
  leaveToClass: 'opacity-0 scale-95 translate-y-4',
}

/**
 * Border Beam - 边框光束效果
 * 使用 CSS 动画实现流动的边框光效
 */
export const borderBeam = {
  className: 'relative overflow-hidden',
  // 需要配合 CSS 使用，参考下面样式定义
}

/**
 * Marquee - 滚动文字效果
 */
export const marquee = {
  className: 'flex overflow-hidden',
  // 需要配合 CSS 动画使用
}

/**
 * Sparkles - 闪烁效果
 */
export const sparkles: MagicTransition = {
  enterActiveClass: 'transition-all duration-500 ease-out',
  leaveActiveClass: 'transition-all duration-300 ease-in',
  enterFromClass: 'opacity-0 scale-0 rotate-180',
  enterToClass: 'opacity-100 scale-100 rotate-0',
  leaveFromClass: 'opacity-100 scale-100 rotate-0',
  leaveToClass: 'opacity-0 scale-0 rotate-180',
}

/**
 * Shimmer - 微光效果
 */
export const shimmer = {
  className: 'animate-shimmer',
  // 需要配合 CSS @keyframes shimmer 使用
}

// ==================== 列表动画 ====================

/**
 * 列表项逐个显示动画
 * 用于列表渲染时的渐入效果
 */
export const listStagger: MagicTransition = {
  enterActiveClass: 'transition-all duration-300 ease-out',
  leaveActiveClass: 'transition-all duration-200 ease-in',
  enterFromClass: 'opacity-0 translate-x-[-20px]',
  enterToClass: 'opacity-100 translate-x-0',
  leaveFromClass: 'opacity-100 translate-x-0',
  leaveToClass: 'opacity-0 translate-x-[20px]',
}

// ==================== 模态框动画 ====================

/**
 * 模态框淡入
 */
export const modalFadeIn: MagicTransition = {
  enterActiveClass: 'transition-all duration-300 ease-out',
  leaveActiveClass: 'transition-all duration-200 ease-in',
  enterFromClass: 'opacity-0 scale-95',
  enterToClass: 'opacity-100 scale-100',
  leaveFromClass: 'opacity-100 scale-100',
  leaveToClass: 'opacity-0 scale-95',
}

/**
 * 遮罩层淡入
 */
export const overlayFadeIn: MagicTransition = {
  enterActiveClass: 'transition-opacity duration-300 ease-out',
  leaveActiveClass: 'transition-opacity duration-200 ease-in',
  enterFromClass: 'opacity-0',
  enterToClass: 'opacity-100',
  leaveFromClass: 'opacity-100',
  leaveToClass: 'opacity-0',
}

// ==================== 按钮动画 ====================

/**
 * 按钮按下效果
 */
export const buttonPress = {
  className: 'active:scale-95 transition-transform duration-100',
}

/**
 * 按钮悬停效果
 */
export const buttonHover = {
  className: 'hover:scale-105 transition-transform duration-200',
}

// ==================== 页面过渡 ====================

/**
 * 页面滑动过渡
 */
export const pageSlide: MagicTransition = {
  enterActiveClass: 'transition-all duration-300 ease-out',
  leaveActiveClass: 'transition-all duration-200 ease-in',
  enterFromClass: 'opacity-0 translate-x-8',
  enterToClass: 'opacity-100 translate-x-0',
  leaveFromClass: 'opacity-100 translate-x-0',
  leaveToClass: 'opacity-0 -translate-x-8',
}

// ==================== 工具函数 ====================

/**
 * 创建带延迟的列表动画
 * @param index 列表项索引
 * @param baseDelay 基础延迟(ms)
 * @param delayIncrement 每项增加的延迟(ms)
 */
export function createStaggerDelay(
  index: number,
  baseDelay: number = 0,
  delayIncrement: number = 50
): string {
  return `${baseDelay + index * delayIncrement}ms`
}

/**
 * 获取动画样式对象
 * @param transition 动画配置
 * @param delay 可选的延迟时间
 */
export function getAnimationStyle(
  _transition: MagicTransition,
  delay?: string | number
): Record<string, string> {
  const style: Record<string, string> = {}

  if (delay) {
    style.transitionDelay = typeof delay === 'number' ? `${delay}ms` : delay
  }

  return style
}

// ==================== Tailwind 动画扩展 ====================

/**
 * Tailwind 配置中需要添加的自定义动画
 *
 * 在 tailwind.config.js 的 theme.extend 中添加:
 *
 * keyframes: {
 *   shimmer: {
 *     '0%': { backgroundPosition: '-1000px 0' },
 *     '100%': { backgroundPosition: '1000px 0' }
 *   },
 *   marquee: {
 *     '0%': { transform: 'translateX(0%)' },
 *     '100%': { transform: 'translateX(-100%)' }
 *   },
 *   'border-beam': {
 *     '0%': { offsetDistance: '0%' },
 *     '100%': { offsetDistance: '100%' }
 *   }
 * },
 * animation: {
 *   shimmer: 'shimmer 2s linear infinite',
 *   marquee: 'marquee 25s linear infinite',
 *   'border-beam': 'border-beam 2s linear infinite'
 * }
 */
