/**
 * useAuth 服务对象(双形态抽象)单元测试
 *
 * 测试策略:isElectron 在模块加载时被捕获(见 utils/isElectron.ts),
 * 因此每个 describe 块在 beforeEach 中先 resetModules + 设置 window.appConfig,
 * 再动态 import useAuth,以触发对应形态的模块求值。
 */
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'

describe('useAuth service (双形态抽象)', () => {
  beforeEach(() => {
    vi.resetModules()
    // 清理状态:happy-dom 提供 window.localStorage
    // (注:不依赖其他 test file 的 global.localStorage 污染,本测试自带兜底)
    if (typeof window !== 'undefined' && window.localStorage) {
      window.localStorage.clear()
    }
    delete (window as any).appConfig
    delete (window as any).auth
  })

  afterEach(() => {
    vi.restoreAllMocks()
  })

  describe('浏览器形态 (isElectron=false)', () => {
    beforeEach(() => {
      // window.appConfig 缺失 → isElectron=false
      delete (window as any).appConfig
    })

    it('login 写入 localStorage access_token', async () => {
      const { auth } = await import('../useAuth')
      await auth.login('tok-browser')
      expect(window.localStorage.getItem('access_token')).toBe('tok-browser')
    })

    it('logout 清除 localStorage access_token', async () => {
      window.localStorage.setItem('access_token', 'pre')
      const { auth } = await import('../useAuth')
      await auth.logout()
      expect(window.localStorage.getItem('access_token')).toBeNull()
    })

    it('getToken 读 localStorage access_token', async () => {
      window.localStorage.setItem('access_token', 'xxx')
      const { auth } = await import('../useAuth')
      const t = await auth.getToken()
      expect(t).toBe('xxx')
    })

    it('getToken 无 token 时返回 null', async () => {
      const { auth } = await import('../useAuth')
      const t = await auth.getToken()
      expect(t).toBeNull()
    })

    it('isAuthenticated 反映 localStorage 状态', async () => {
      const { auth } = await import('../useAuth')
      expect(await auth.isAuthenticated()).toBe(false)
      window.localStorage.setItem('access_token', 'y')
      expect(await auth.isAuthenticated()).toBe(true)
    })

    it('不调用 window.auth(浏览器形态无 IPC)', async () => {
      const fakeAuth = {
        login: vi.fn(),
        logout: vi.fn(),
        getToken: vi.fn(),
        isAuthenticated: vi.fn(),
      }
      ;(window as any).auth = fakeAuth
      const { auth } = await import('../useAuth')
      await auth.login('t')
      await auth.logout()
      await auth.getToken()
      await auth.isAuthenticated()
      // 浏览器形态即使 window.auth 存在也不应调用
      expect(fakeAuth.login).not.toHaveBeenCalled()
      expect(fakeAuth.logout).not.toHaveBeenCalled()
      expect(fakeAuth.getToken).not.toHaveBeenCalled()
      expect(fakeAuth.isAuthenticated).not.toHaveBeenCalled()
    })
  })

  describe('Electron 形态 (isElectron=true)', () => {
    beforeEach(() => {
      // 必须在 import useAuth 之前设置 appConfig(isElectron 模块加载时捕获)
      ;(window as any).appConfig = {
        apiBase: 'http://localhost:8000',
        wsBase: 'ws://localhost:8000',
        isElectron: true,
      }
      ;(window as any).auth = {
        login: vi.fn().mockResolvedValue(true),
        logout: vi.fn().mockResolvedValue(true),
        getToken: vi.fn().mockResolvedValue('electron-tok'),
        isAuthenticated: vi.fn().mockResolvedValue(true),
        onUnauthorized: vi.fn().mockImplementation((_cb: () => void) => {
          return () => {}
        }),
      }
    })

    it('login 调用 window.auth.login (IPC→safeStorage)', async () => {
      const { auth } = await import('../useAuth')
      await auth.login('electron-tok')
      expect((window as any).auth.login).toHaveBeenCalledWith('electron-tok')
    })

    it('login 不写 localStorage(Electron 不在渲染层持 token)', async () => {
      const { auth } = await import('../useAuth')
      await auth.login('electron-tok')
      expect(window.localStorage.getItem('access_token')).toBeNull()
    })

    it('logout 调用 window.auth.logout (IPC→清 safeStorage)', async () => {
      const { auth } = await import('../useAuth')
      await auth.logout()
      expect((window as any).auth.logout).toHaveBeenCalled()
    })

    it('getToken 走 IPC,返回主进程 safeStorage 内 token', async () => {
      const { auth } = await import('../useAuth')
      const t = await auth.getToken()
      expect(t).toBe('electron-tok')
      expect((window as any).auth.getToken).toHaveBeenCalled()
    })

    it('isAuthenticated 走 IPC', async () => {
      const { auth } = await import('../useAuth')
      const ok = await auth.isAuthenticated()
      expect(ok).toBe(true)
      expect((window as any).auth.isAuthenticated).toHaveBeenCalled()
    })

    it('不读写 localStorage access_token(Electron 形态 token 不在渲染层)', async () => {
      const setSpy = vi.spyOn(Storage.prototype, 'setItem')
      const getSpy = vi.spyOn(Storage.prototype, 'getItem')
      const { auth } = await import('../useAuth')
      await auth.login('e-1')
      await auth.getToken()
      await auth.isAuthenticated()
      await auth.logout()
      // Electron 形态:setItem/getItem 不应被以 'access_token' 调用
      for (const call of setSpy.mock.calls) {
        expect(call[0]).not.toBe('access_token')
      }
      for (const call of getSpy.mock.calls) {
        expect(call[0]).not.toBe('access_token')
      }
    })
  })

  describe('双形态对称性', () => {
    it('两形态 API 表面一致(login/logout/getToken/isAuthenticated 均 async)', async () => {
      // 浏览器形态
      delete (window as any).appConfig
      const browserMod = await import('../useAuth')
      expect(typeof browserMod.auth.login).toBe('function')
      expect(typeof browserMod.auth.logout).toBe('function')
      expect(typeof browserMod.auth.getToken).toBe('function')
      expect(typeof browserMod.auth.isAuthenticated).toBe('function')

      vi.resetModules()
      // Electron 形态
      ;(window as any).appConfig = {
        apiBase: 'http://x',
        wsBase: 'ws://x',
        isElectron: true,
      }
      ;(window as any).auth = {
        login: vi.fn().mockResolvedValue(true),
        logout: vi.fn().mockResolvedValue(true),
        getToken: vi.fn().mockResolvedValue(null),
        isAuthenticated: vi.fn().mockResolvedValue(false),
      }
      const electronMod = await import('../useAuth')
      expect(typeof electronMod.auth.login).toBe('function')
      expect(typeof electronMod.auth.logout).toBe('function')
      expect(typeof electronMod.auth.getToken).toBe('function')
      expect(typeof electronMod.auth.isAuthenticated).toBe('function')

      // 两形态所有方法均返回 Promise
      expect(browserMod.auth.login('t')).toBeInstanceOf(Promise)
      expect(electronMod.auth.login('t')).toBeInstanceOf(Promise)
    })
  })
})
