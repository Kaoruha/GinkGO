/// <reference types="vite/client" />

declare module '*.vue' {
  import type { DefineComponent } from 'vue'
  const component: DefineComponent<{}, {}, any>
  export default component
}

// Electron 形态:preload contextBridge 注入(window.appConfig)
// 浏览器形态下 undefined;渲染层用 window.appConfig?.apiBase 安全读取
interface AppConfig {
  apiBase: string
  wsBase: string
  isElectron: true
}
interface Window {
  appConfig?: AppConfig
}
