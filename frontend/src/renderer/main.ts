import { createApp } from 'vue'
import { createPinia } from 'pinia'
import App from './App.vue'
import router from './router'
import { useAuthStore } from './stores/auth'
import './styles/index.less'

const app = createApp(App)
app.use(createPinia())
app.use(router)

// Electron 形态:启动时从 safeStorage 拉取 token 至 store 的内存 ref
// 浏览器形态:no-op(token ref 已从 localStorage 初始化)
// 必须在 app.mount 前完成,否则首次路由守卫 token=null 误判未登录
const authStore = useAuthStore()
authStore.init().finally(() => {
  app.mount('#app')
})
