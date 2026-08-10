// Electron 主进程入口
// 职责:创建 BrowserWindow、注册 app:// 协议、根据 ELECTRON_RENDERER_URL 切换 dev/prod loadURL
// preload 注入 window.appConfig(Task 3);auth API 留给 Task 7
import { app, BrowserWindow, shell } from 'electron'
import { join } from 'path'
import { registerAppProtocol, registerAppProtocolHandler } from './protocol'

// app.ready 前 注册特权 scheme(registerSchemesAsPrivileged 仅 app.ready 之前生效)
registerAppProtocol()

// preload 上下文无 electron.app,需经 env 注入 userData 路径(config.ts 读此)
// 必须在 createWindow(fork renderer) 前 set,renderer 才能继承
process.env.GINKGO_USER_DATA = app.getPath('userData')

const isDev = !!process.env['ELECTRON_RENDERER_URL']

function createWindow(): void {
  const win = new BrowserWindow({
    width: 1280,
    height: 800,
    webPreferences: {
      // package.json type:module 下 electron-vite 产物是 .mjs
      preload: join(__dirname, '../preload/index.mjs'),
      contextIsolation: true,
      nodeIntegration: false,
      sandbox: false, // preload 用 Node(safeStorage/config),sandbox 需另配
    },
  })

  // 外链用系统浏览器,不在 Electron 内开新窗
  win.webContents.setWindowOpenHandler(({ url }) => {
    shell.openExternal(url)
    return { action: 'deny' }
  })

  if (isDev) {
    win.loadURL(process.env['ELECTRON_RENDERER_URL']!)
    win.webContents.openDevTools()
  } else {
    win.loadURL('app://./index.html')
  }
}

app.whenReady().then(() => {
  // app.ready 后 安装 file handler(protocol.handle 需要 ready)
  registerAppProtocolHandler()
  createWindow()
})

app.on('window-all-closed', () => {
  if (process.platform !== 'darwin') app.quit()
})

app.on('activate', () => {
  if (BrowserWindow.getAllWindows().length === 0) createWindow()
})
