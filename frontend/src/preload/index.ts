// frontend/src/preload/index.ts
// 注:brief 原文同时导入 ipcRenderer,但当前未使用,tsconfig strict(noUnusedLocals)
// 会报错。Task 7 接 auth API 时按需补回。
import { contextBridge } from 'electron'
import { loadConfig } from '../main/config'

const config = loadConfig()

contextBridge.exposeInMainWorld('appConfig', {
  apiBase: config.apiBase,
  wsBase: config.wsBase,
  isElectron: true as const,
  // auth API 在 Task 7 补
})
