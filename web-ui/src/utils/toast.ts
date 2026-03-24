/**
 * Toast notification utilities
 * Simple implementation that can be extended with actual UI notifications
 */

export type ToastType = 'success' | 'error' | 'info' | 'warning'

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
function showToast(message: string, type: ToastType = 'info'): void {
  const id = ++toastId

  // Log to console
  console.log(`[${type.toUpperCase()}] ${message}`)

  // Create toast element
  if (toastContainer) {
    const toast = document.createElement('div')
    toast.id = `toast-${id}`
    toast.className = `toast-notification toast-${type}`

    const bgColor = type === 'success' ? '#52c41a' : type === 'error' ? '#f5222d' : type === 'warning' ? '#faad14' : '#1890ff'

    toast.style.cssText = `
      padding: 12px 16px;
      background: ${bgColor};
      color: white;
      border-radius: 4px;
      box-shadow: 0 4px 12px rgba(0, 0, 0, 0.3);
      font-size: 14px;
      pointer-events: auto;
      animation: toastSlideIn 0.3s ease-out;
      max-width: 300px;
      word-wrap: break-word;
    `
    toast.textContent = message

    toastContainer.appendChild(toast)

    // Auto remove after 3 seconds
    setTimeout(() => {
      toast.style.animation = 'toastSlideOut 0.3s ease-out'
      setTimeout(() => {
        toast.remove()
      }, 300)
    }, 3000)
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
