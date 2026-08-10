// frontend/src/preload/index.ts
// contextBridge 注入两份能力:
//   - window.appConfig:运行时配置(Task 3)
//   - window.auth:认证 IPC 桥(Task 7 主进程 src/main/auth.ts 实现 + Task 8 渲染层消费)
import { contextBridge, ipcRenderer } from 'electron'
import { loadConfig } from '../main/config'

const config = loadConfig()

contextBridge.exposeInMainWorld('appConfig', {
  apiBase: config.apiBase,
  wsBase: config.wsBase,
  isElectron: true as const,
})

// 认证 IPC 桥:渲染层不持 token,所有 token 持久化在主进程 safeStorage
// onUnauthorized 返回 disposer(供 removeListener),避免 hot-reload/重挂载累积监听器
contextBridge.exposeInMainWorld('auth', {
  login: (token: string) => ipcRenderer.invoke('auth:login', token),
  logout: () => ipcRenderer.invoke('auth:logout'),
  getToken: () => ipcRenderer.invoke('auth:getToken'),
  isAuthenticated: () => ipcRenderer.invoke('auth:isAuthenticated'),
  onUnauthorized: (cb: () => void) => {
    const wrapped = () => cb()
    ipcRenderer.on('auth:unauthorized', wrapped)
    return () => ipcRenderer.removeListener('auth:unauthorized', wrapped)
  },
})
