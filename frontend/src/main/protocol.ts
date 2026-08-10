// app:// 自定义协议注册
// 必须在 app.ready 之前调用 registerSchemesAsPrivileged,否则 origin 不稳定、fetch/CSP 行为异常
import { protocol } from 'electron'

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
