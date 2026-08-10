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

// 认证 IPC 桥类型(Electron 形态由 preload 注入;浏览器形态下 undefined)
// 与 src/preload/index.ts 中 contextBridge.exposeInMainWorld('auth', {...}) 形状对齐
interface AuthApi {
  login: (token: string) => Promise<boolean>
  logout: () => Promise<boolean>
  getToken: () => Promise<string | null>
  isAuthenticated: () => Promise<boolean>
  onUnauthorized: (cb: () => void) => () => void
}

interface Window {
  appConfig?: AppConfig
  auth?: AuthApi
}
