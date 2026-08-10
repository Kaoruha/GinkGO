// app:// 自定义协议注册 + file handler
//
// 两阶段:
// 1) registerAppProtocol():app.ready **前** 调用,注册 scheme 为特权
//    (registerSchemesAsPrivileged 仅 ready 之前生效,否则 origin 不稳定、fetch/CSP 行为异常)
// 2) registerAppProtocolHandler():app.ready **后** 调用,安装 file-serving handler
//    (protocol.handle 需要 ready;prod 模式下 win.loadURL('app://./index.html') 经此拿 HTML)
import { protocol, net } from 'electron'
import { join, relative, isAbsolute } from 'path'
import { existsSync } from 'fs'
import { pathToFileURL } from 'url'

export function registerAppProtocol(): void {
  // 注册为标准/特权 scheme:有稳定 origin、支持 fetch、localStorage
  protocol.registerSchemesAsPrivileged([
    {
      scheme: 'app',
      privileges: {
        standard: true,
        secure: true,
        supportFetchAPI: true,
        stream: true,
        bypassCSP: false,
      },
    },
  ])
}

// app://./index.html → out/renderer/index.html(及 assets/*)
// host='.', pathname='/index.html' 或 '/assets/xxx.js'
export function registerAppProtocolHandler(): void {
  // out/main/index.js → out/renderer(三段式产物平铺)
  const rendererDist = join(__dirname, '..', 'renderer')
  console.log('[app://] rendererDist =', rendererDist, 'exists =', existsSync(rendererDist))

  protocol.handle('app', (request) => {
    const u = new URL(request.url)
    // 去前导斜杠后 join,避免 path.join 把绝对路径当根
    const safePath = decodeURIComponent(u.pathname).replace(/^[/\\]+/, '')
    const filePath = join(rendererDist, safePath)
    // 防 path traversal:最终路径必须仍在 rendererDist 内
    const rel = relative(rendererDist, filePath)
    if (rel.startsWith('..') || isAbsolute(rel)) {
      return new Response('Forbidden', { status: 403 })
    }
    return net.fetch(pathToFileURL(filePath).href)
  })
}
