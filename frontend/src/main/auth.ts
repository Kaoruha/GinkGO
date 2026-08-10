// 主进程 auth: safeStorage 持 token + onBeforeSendHeaders 透明注入 Authorization
// 渲染层不持 token,经 IPC 与本模块交互(Task 8 接 preload/renderer)
// Linux 无 libsecret 时 safeStorage.isEncryptionAvailable()=false → 退明文(ADR-044 自用可接受)
import { app, ipcMain, safeStorage, session, BrowserWindow } from 'electron'
import { readFileSync, writeFileSync, existsSync, unlinkSync } from 'fs'
import { join } from 'path'

const TOKEN_FILE = () => join(app.getPath('userData'), 'token.enc')

function canUseSafeStorage() {
  return safeStorage.isEncryptionAvailable()
}

export function getToken(): string | null {
  const p = TOKEN_FILE()
  if (!existsSync(p)) return null
  try {
    const buf = readFileSync(p)
    // safeStorage 加密可用则解密,否则(Linux 无 libsecret)退化为明文读取
    return canUseSafeStorage() ? safeStorage.decryptString(buf) : buf.toString('utf-8')
  } catch {
    return null
  }
}

export function setToken(token: string | null) {
  const p = TOKEN_FILE()
  if (!token) {
    if (existsSync(p)) unlinkSync(p)
    return
  }
  const buf = canUseSafeStorage() ? safeStorage.encryptString(token) : Buffer.from(token, 'utf-8')
  writeFileSync(p, buf)
}

/** 透明注入:渲染进程所有出站请求自动带 Authorization */
export function installAuthInterceptor() {
  session.defaultSession.webRequest.onBeforeSendHeaders((details, cb) => {
    const token = getToken()
    if (token && details.url.startsWith('http')) {
      details.requestHeaders['Authorization'] = `Bearer ${token}`
    }
    cb({ requestHeaders: details.requestHeaders })
  })
  // 401 响应:清 token + 通知渲染层
  session.defaultSession.webRequest.onHeadersReceived((details, cb) => {
    if (details.statusCode === 401) {
      setToken(null)
      // 通知所有窗口重定向登录(渲染层监听)
      for (const win of BrowserWindow.getAllWindows()) {
        win.webContents.send('auth:unauthorized')
      }
    }
    cb({ responseHeaders: details.responseHeaders })
  })
}

export function registerAuthIpc() {
  ipcMain.handle('auth:login', (_e, token: string) => {
    if (!token || typeof token !== 'string' || !token.trim()) return false
    setToken(token.trim())
    return true
  })
  ipcMain.handle('auth:logout', () => {
    setToken(null)
    return true
  })
  ipcMain.handle('auth:getToken', () => getToken())
  ipcMain.handle('auth:isAuthenticated', () => getToken() !== null)
}
