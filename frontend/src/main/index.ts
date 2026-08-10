// Electron 主进程入口占位骨架(Task 2 替换为完整实现)
import { app, BrowserWindow } from 'electron'

const createWindow = (): void => {
  const win = new BrowserWindow({ width: 1280, height: 800 })
  if (process.env['ELECTRON_RENDERER_URL']) {
    win.loadURL(process.env['ELECTRON_RENDERER_URL'])
  } else {
    win.loadFile('out/renderer/index.html')
  }
}

app.whenReady().then(createWindow)

app.on('window-all-closed', () => {
  if (process.platform !== 'darwin') app.quit()
})
