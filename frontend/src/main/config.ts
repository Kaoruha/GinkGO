// frontend/src/main/config.ts
//
// 被 main 与 preload 同时引用:
// - main 进程:electron.app 可用,直接 getPath
// - preload 进程:electron 不导出 app(contextBridge/ipcRenderer 才是 preload-side export),
//   命名空间导入 + 兜底到 process.env.GINKGO_USER_DATA(由 main 在 fork renderer 前注入)
//
// 不能用 `import { app } from 'electron'`:preload 上下文会在 link 期抛
// "The requested module 'electron' does not provide an export named 'app'"
import * as electron from 'electron'
import { join } from 'path'
import { readFileSync, writeFileSync, existsSync } from 'fs'

export interface AppConfig {
  apiBase: string // 例 'http://localhost:8000'
  wsBase: string // 例 'ws://localhost:8000'
}

const DEFAULT: AppConfig = {
  apiBase: 'http://localhost:8000',
  wsBase: 'ws://localhost:8000',
}

function getUserDataDir(): string {
  const e = electron as unknown as { app?: { getPath: (name: string) => string } }
  if (e.app?.getPath) return e.app.getPath('userData')
  if (process.env.GINKGO_USER_DATA) return process.env.GINKGO_USER_DATA
  throw new Error('userData unavailable: main 须在 fork renderer 前 set GINKGO_USER_DATA')
}

export function getConfigPath() {
  return join(getUserDataDir(), 'config.json')
}

export function loadConfig(): AppConfig {
  const p = getConfigPath()
  if (!existsSync(p)) return DEFAULT
  try {
    return { ...DEFAULT, ...JSON.parse(readFileSync(p, 'utf-8')) }
  } catch {
    return DEFAULT
  }
}

export function saveConfig(cfg: Partial<AppConfig>) {
  const merged = { ...loadConfig(), ...cfg }
  writeFileSync(getConfigPath(), JSON.stringify(merged, null, 2))
  // 重启生效(ADR-043 §6):不热重载
}
