import { createApp } from 'vue'
import { createPinia } from 'pinia'
import App from './App.vue'
import router from './router'
import { useAuthStore } from './stores/auth'
import { initTheme } from './composables/useTheme'
import './styles/main.css'   // @tailwind base/components/utilities + @import design-tokens.css(修复 token 接线断层,见 ADR-045)
import './styles/fonts.css'  // Inter(正文)+ JetBrains Mono(等宽)@font-face,ADR-045 §3,随 Electron 打包离线可用
import './styles/index.less'

const app = createApp(App)
app.use(createPinia())
app.use(router)

// 主题初始化:必须在 mount 前完成,避免 FOUC(首屏闪烁)
// 默认 dark(Codex 深色优先,ADR-045);localStorage 持久化覆盖
// 顺序:createApp → use(pinia/router) → initTheme → authStore.init → mount
initTheme()

// Electron 形态:启动时从 safeStorage 拉取 token 至 store 的内存 ref
// 浏览器形态:no-op(token ref 已从 localStorage 初始化)
// 必须在 app.mount 前完成,否则首次路由守卫 token=null 误判未登录
const authStore = useAuthStore()
authStore.init().finally(() => {
  app.mount('#app')
})
