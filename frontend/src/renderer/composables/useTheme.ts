/**
 * 主题切换 composable (ADR-045 Codex 中性灰视觉语言)
 *
 * 设计要点:
 *  - class-based dark mode (`darkMode: ['class']`),Tailwind 配置已就绪
 *  - 默认 dark:深色优先 (Codex 视觉语言)
 *  - localStorage 持久化,键名 `ginkgo-theme`
 *  - initTheme() 必须在 app.mount 前调用,避免首屏闪烁 (FOUC)
 *
 * 用法:
 *   main.ts:
 *     import { initTheme } from '@/composables/useTheme'
 *     initTheme()                  // createApp 之后、mount 之前
 *     app.mount('#app')
 *
 *   组件内:
 *     const { theme, setTheme, toggleTheme } = useTheme()
 */

export type Theme = 'light' | 'dark'

const STORAGE_KEY = 'ginkgo-theme'
const DEFAULT_THEME: Theme = 'dark'

let currentTheme: Theme = DEFAULT_THEME

/**
 * 应用主题到 <html> 根节点(class-based dark mode)
 */
function applyTheme(theme: Theme): void {
  const root = document.documentElement
  if (theme === 'dark') {
    root.classList.add('dark')
  } else {
    root.classList.remove('dark')
  }
}

/**
 * 从 localStorage 读取主题,缺省返回 DEFAULT_THEME
 */
function readStoredTheme(): Theme {
  try {
    const stored = localStorage.getItem(STORAGE_KEY)
    if (stored === 'light' || stored === 'dark') {
      return stored
    }
  } catch {
    // localStorage 不可用(Electron 沙箱异常等),静默回退
  }
  return DEFAULT_THEME
}

/**
 * 启动时初始化主题 (避免 FOUC)
 *
 * 必须在 createApp 之后、app.mount 之前调用:
 *   - createApp 前无法访问 document,不安全
 *   - mount 后调用会触发首屏闪烁
 *
 * 顺序契约:在 `app.use(pinia)` / `app.use(router)` 之后,
 * `authStore.init().finally(() => app.mount('#app'))` 之前。
 */
export function initTheme(): void {
  currentTheme = readStoredTheme()
  applyTheme(currentTheme)
}

/**
 * 设置主题并持久化
 */
export function setTheme(theme: Theme): void {
  currentTheme = theme
  applyTheme(theme)
  try {
    localStorage.setItem(STORAGE_KEY, theme)
  } catch {
    // 写入失败不阻塞,内存态已生效
  }
}

/**
 * 切换主题(light ↔ dark)
 */
export function toggleTheme(): void {
  setTheme(currentTheme === 'dark' ? 'light' : 'dark')
}

/**
 * 获取当前主题(响应式 ref,组件内使用)
 *
 * 注意:返回的 ref 与模块内 currentTheme 同步,
 * setTheme/toggleTheme 会自动更新所有 useTheme() 返回的 ref。
 */
import { ref, type Ref } from 'vue'

const themeRef: Ref<Theme> = ref(currentTheme)

// 包装 setTheme/toggleTheme 同步更新 ref
const setThemeReactive = (theme: Theme) => {
  setTheme(theme)
  themeRef.value = theme
}
const toggleThemeReactive = () => {
  toggleTheme()
  themeRef.value = currentTheme
}

export function useTheme() {
  return {
    theme: themeRef,
    setTheme: setThemeReactive,
    toggleTheme: toggleThemeReactive,
  }
}
