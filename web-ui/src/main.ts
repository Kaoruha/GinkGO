import { createApp } from 'vue'
import { createPinia } from 'pinia'
<<<<<<< HEAD
import piniaPluginPersistedstate from 'pinia-plugin-persistedstate'
import Antd from 'ant-design-vue'
import App from './App.vue'
import router from './router'
import GlobalLoading from './components/common/GlobalLoading.vue'
import './styles/main.css'

// Vue Flow 样式
import '@vue-flow/core/dist/style.css'
import '@vue-flow/core/dist/theme-default.css'
import '@vue-flow/controls/dist/style.css'
import '@vue-flow/minimap/dist/style.css'

const app = createApp(App)
const pinia = createPinia()

// 添加状态持久化插件
pinia.use(piniaPluginPersistedstate)

app.use(pinia)
app.use(router)
app.use(Antd)

// 注册全局组件
app.component('GlobalLoading', GlobalLoading)

=======
import Antd from 'ant-design-vue'
import App from './App.vue'
import router from './router'
import 'ant-design-vue/dist/reset.css'
import './styles/index.less'

const app = createApp(App)

app.use(createPinia())
app.use(router)
app.use(Antd)

>>>>>>> 011-quant-research
app.mount('#app')
