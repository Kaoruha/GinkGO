/**
 * Toast notification utilities
 * Simple implementation that can be extended with actual UI notifications
 *
 * 交互(2026-08):鼠标悬停暂停自动消失(移出后按剩余时间恢复,方便阅读长消息);
 * 右侧一键复制消息全文(走 utils/clipboard 降级链,非安全上下文可用)。
 */

import { copyText } from './clipboard'

export type ToastType = 'success' | 'error' | 'info' | 'warning'

const DURATION = 3000
const EXIT_MS = 300

let toastContainer: HTMLDivElement | null = null
let toastId = 0

// Initialize toast container
function initToastContainer() {
  if (toastContainer) return

  // Check if container exists
  let container = document.getElementById('toast-container')
  if (!container) {
    container = document.createElement('div')
    container.id = 'toast-container'
    container.style.cssText = `
      position: fixed;
      top: 20px;
      right: 20px;
      z-index: 9999;
      display: flex;
      flex-direction: column;
      gap: 10px;
      pointer-events: none;
    `
    document.body.appendChild(container)
  }
  toastContainer = container as HTMLDivElement
}

// Add animations
function initAnimations() {
  const styleId = 'toast-animations'
  if (document.getElementById(styleId)) return

  const style = document.createElement('style')
  style.id = styleId
  style.textContent = `
    @keyframes toastSlideIn {
      from {
        transform: translateX(100%);
        opacity: 0;
      }
      to {
        transform: translateX(0);
        opacity: 1;
      }
    }
    @keyframes toastSlideOut {
      from {
        transform: translateX(0);
        opacity: 1;
      }
      to {
        transform: translateX(100%);
        opacity: 0;
      }
    }
    .toast-copy-btn {
      flex-shrink: 0;
      align-self: flex-start;
      margin-left: 10px;
      padding: 2px 8px;
      background: rgba(255, 255, 255, 0.2);
      border: 1px solid rgba(255, 255, 255, 0.4);
      border-radius: 3px;
      color: white;
      font-size: 11px;
      line-height: 1.4;
      cursor: pointer;
    }
    .toast-copy-btn:hover { background: rgba(255, 255, 255, 0.35); }
  `
  document.head.appendChild(style)
}

// Initialize on module load
if (typeof window !== 'undefined') {
  initToastContainer()
  initAnimations()
}

/**
 * Show a toast notification
 */
function showToast(msg: string, type: ToastType = 'info'): void {
  const id = ++toastId

  // Log to console
  console.log(`[${type.toUpperCase()}] ${msg}`)

  // Create toast element
  if (toastContainer) {
    const toast = document.createElement('div')
    toast.id = `toast-${id}`
    toast.className = `toast-notification toast-${type}`

    const bgColor = type === 'success' ? 'hsl(var(--success))' : type === 'error' ? 'hsl(var(--error))' : type === 'warning' ? 'hsl(var(--warning))' : 'hsl(var(--primary))'

    toast.style.cssText = `
      display: flex;
      align-items: flex-start;
      padding: 12px 16px;
      background: ${bgColor};
      color: white;
      border-radius: 4px;
      box-shadow: 0 4px 12px rgba(0, 0, 0, 0.3);
      font-size: 14px;
      pointer-events: auto;
      animation: toastSlideIn 0.3s ease-out;
      max-width: 360px;
      word-wrap: break-word;
    `

    const text = document.createElement('span')
    text.textContent = msg
    text.style.cssText = 'flex: 1; min-width: 0;'
    toast.appendChild(text)

    // 一键复制:复制消息全文;成功后按钮文案翻转反馈,不另弹 toast(避免叠加)
    const copyBtn = document.createElement('button')
    copyBtn.type = 'button'
    copyBtn.className = 'toast-copy-btn'
    copyBtn.textContent = '复制'
    copyBtn.addEventListener('click', async e => {
      e.stopPropagation()
      if (await copyText(msg)) {
        copyBtn.textContent = '已复制'
        setTimeout(() => { copyBtn.textContent = '复制' }, 1000)
      }
    })
    toast.appendChild(copyBtn)

    toastContainer.appendChild(toast)

    // 自动消失:hover 暂停(momentum 计时);移出后按剩余时长恢复(至少 1s 便于接力操作)
    let closeTimer: ReturnType<typeof setTimeout> | null = null
    let shownAt = Date.now()
    let closing = false
    const close = () => {
      if (closing) return
      closing = true
      toast.style.animation = 'toastSlideOut 0.3s ease-out'
      setTimeout(() => toast.remove(), EXIT_MS)
    }
    const arm = (ms: number) => {
      if (closeTimer) clearTimeout(closeTimer)
      shownAt = Date.now()
      closeTimer = setTimeout(close, ms)
    }
    arm(DURATION)

    toast.addEventListener('mouseenter', () => {
      if (closeTimer) { clearTimeout(closeTimer); closeTimer = null }
      // 恰逢退出动画进行中:撤销动画救回,继续悬停阅读
      if (closing) {
        closing = false
        toast.style.animation = ''
      }
    })
    toast.addEventListener('mouseleave', () => {
      // 已复制反馈窗口(1s)内移出也给足阅读时间
      arm(Math.max(DURATION - (Date.now() - shownAt), 1000))
    })
  }
}

/**
 * Message API for toast notifications
 */
export const message = {
  success: (msg: string) => showToast(msg, 'success'),
  error: (msg: string) => showToast(msg, 'error'),
  info: (msg: string) => showToast(msg, 'info'),
  warning: (msg: string) => showToast(msg, 'warning'),
  /**
   * @deprecated Use warning() instead
   */
  warn: (msg: string) => showToast(msg, 'warning'),
}

// Also export individual functions for convenience
export const toast = {
  success: message.success,
  error: message.error,
  info: message.info,
  warning: message.warning,
}

export default message
