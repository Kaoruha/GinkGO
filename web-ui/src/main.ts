// Vue 应用入口（挂载根组件 + 全局插件）
import { createApp } from 'vue'
import { createPinia } from 'pinia'
import App from './App.vue'
import router from './router'
import './styles/index.less'

const app = createApp(App)

app.use(createPinia())
app.use(router)

app.mount('#app')
