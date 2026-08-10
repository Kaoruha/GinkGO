// useAuth 服务对象(双形态抽象)
// - Electron 形态:走 window.auth(IPC → 主进程 safeStorage,见 src/main/auth.ts)
// - 浏览器形态:走 localStorage
//
// 注意:文件名沿用 useAuth.ts(对齐 brief Step 3),但本导出是单例服务对象,
// 非 Vue composable。供 api/modules/auth.ts、stores/auth.ts、request.ts、
// useWebSocket.ts、errorHandler.ts 共用,作为 token 持久化的唯一收口。
//
// user_info 是非敏感数据,双形态均留 localStorage(由调用方自行处理),
// 本服务只管 token。
import { isElectron } from '@/utils/isElectron'

export const auth = {
  /** 登录成功后保存 token:Electron→IPC safeStorage / 浏览器→localStorage */
  async login(token: string): Promise<void> {
    if (isElectron) {
      await window.auth!.login(token)
      return
    }
    localStorage.setItem('access_token', token)
  },

  /** 登出清 token:Electron→IPC 清 safeStorage / 浏览器→清 localStorage */
  async logout(): Promise<void> {
    if (isElectron) {
      await window.auth!.logout()
      return
    }
    localStorage.removeItem('access_token')
  },

  /** 读 token:Electron→IPC 拉 safeStorage / 浏览器→读 localStorage */
  async getToken(): Promise<string | null> {
    if (isElectron) return window.auth!.getToken()
    return localStorage.getItem('access_token')
  },

  /** 是否已登录:Electron→IPC 查 safeStorage / 浏览器→检查 localStorage */
  async isAuthenticated(): Promise<boolean> {
    if (isElectron) return window.auth!.isAuthenticated()
    return !!localStorage.getItem('access_token')
  },
}
