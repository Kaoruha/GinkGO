/**
 * auth store init() - Electron 形态 onUnauthorized 消费者注册测试 (R1 fix)
 *
 * 验证:
 *  1. init() 在 Electron 形态注册 window.auth.onUnauthorized 消费者(I1 修复)
 *  2. 主进程 push auth:unauthorized → preload 触发回调 → 清空 Pinia 状态
 *     (token/user 翻 null → isLoggedIn 翻 false → UI 一致性)
 *  3. 浏览器形态不注册消费者(no-op init)
 */
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { setActivePinia, createPinia } from 'pinia'

describe('useAuthStore.init() - Electron 形态 onUnauthorized 消费者 (R1 fix)', () => {
  let unauthorizedCb: (() => void) | null = null

  beforeEach(() => {
    vi.resetModules()
    window.localStorage.clear()
    delete (window as any).appConfig
    delete (window as any).auth
    setActivePinia(createPinia())
    unauthorizedCb = null
  })

  afterEach(() => {
    vi.restoreAllMocks()
  })

  it('Electron 形态 init() 注册消费者:回调触发时清空 token/user/user_info', async () => {
    ;(window as any).appConfig = {
      apiBase: 'http://x',
      wsBase: 'ws://x',
      isElectron: true,
    }
    const onUnauthorizedMock = vi.fn((cb: () => void) => {
      unauthorizedCb = cb
      return () => {}
    })
    ;(window as any).auth = {
      login: vi.fn().mockResolvedValue(true),
      logout: vi.fn().mockResolvedValue(true),
      getToken: vi.fn().mockResolvedValue('electron-tok'),
      isAuthenticated: vi.fn().mockResolvedValue(true),
      onUnauthorized: onUnauthorizedMock,
    }

    const { useAuthStore } = await import('../auth')
    const store = useAuthStore()

    // 模拟已登录态(token + user + user_info 都填)
    store.$patch({
      token: 'electron-tok',
      user: { uuid: 'u', username: 'kaoru', display_name: 'Kaoru', is_admin: false },
    })
    window.localStorage.setItem('user_info', JSON.stringify({ uuid: 'u' }))
    expect(store.isLoggedIn).toBe(true)

    // init() 应当:1) 拉 safeStorage token  2) 注册 onUnauthorized 消费者
    await store.init()
    expect(onUnauthorizedMock).toHaveBeenCalledTimes(1)
    expect(unauthorizedCb).not.toBeNull()

    // 模拟主进程 onHeadersReceived 收 401 → setToken(null) → webContents.send('auth:unauthorized')
    //         → preload 触发回调 → 此处清 Pinia 状态
    unauthorizedCb!()

    // 断言:Pinia 状态清空 → isLoggedIn 翻 false(UI 一致性)
    expect(store.token).toBeNull()
    expect(store.user).toBeNull()
    expect(store.isLoggedIn).toBe(false)
    // user_info 也在渲染层 localStorage 清掉(非敏感数据,但 401 即登出语义)
    expect(window.localStorage.getItem('user_info')).toBeNull()
  })

  it('浏览器形态 init() 不注册 onUnauthorized', async () => {
    delete (window as any).appConfig
    const onUnauthorizedSpy = vi.fn()
    ;(window as any).auth = { onUnauthorized: onUnauthorizedSpy }

    const { useAuthStore } = await import('../auth')
    const store = useAuthStore()
    await store.init()
    // 浏览器形态 init() 完全 no-op,不触 IPC 也不注册消费者
    expect(onUnauthorizedSpy).not.toHaveBeenCalled()
  })

  it('Electron 形态:init() 拉到的 safeStorage token 写入 store.token', async () => {
    ;(window as any).appConfig = {
      apiBase: 'http://x',
      wsBase: 'ws://x',
      isElectron: true,
    }
    ;(window as any).auth = {
      login: vi.fn().mockResolvedValue(true),
      logout: vi.fn().mockResolvedValue(true),
      getToken: vi.fn().mockResolvedValue('restored-tok'),
      isAuthenticated: vi.fn().mockResolvedValue(true),
      onUnauthorized: vi.fn(() => () => {}),
    }

    const { useAuthStore } = await import('../auth')
    const store = useAuthStore()
    // Electron 形态 token ref 初始为 null(localStorage 无 token)
    expect(store.token).toBeNull()

    await store.init()
    // init() 后 token 从 safeStorage 恢复至内存 ref
    expect(store.token).toBe('restored-tok')
  })
})
