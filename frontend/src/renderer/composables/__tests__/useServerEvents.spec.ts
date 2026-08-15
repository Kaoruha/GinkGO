/**
 * useServerEvents 单元测试（ADR-046 事件层）
 *
 * 策略:mock useWebSocket(可控 isConnected + 手动派发消息),不建真连接;
 * 模块级单例 → vi.resetModules + 动态 import 每测重置。
 */
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { ref, defineComponent, createApp, nextTick } from 'vue'

type ServerEventsMod = typeof import('../useServerEvents')

// 可控的 useWebSocket 替身
let isConnected: ReturnType<typeof ref<boolean>>
let wsHandler: ((data: any) => void) | null = null
let mod: ServerEventsMod
let toastMocks: Record<string, ReturnType<typeof vi.fn>>

async function freshModule() {
  vi.resetModules()
  isConnected = ref(false)
  wsHandler = null
  vi.doMock('@/composables/useWebSocket', () => ({
    useWebSocket: () => ({
      isConnected,
      subscribe: (_t: string, h: (data: any) => void) => {
        wsHandler = h
      },
    }),
  }))
  toastMocks = {
    success: vi.fn(),
    error: vi.fn(),
    info: vi.fn(),
    warning: vi.fn(),
  }
  vi.doMock('@/utils/toast', () => ({ message: toastMocks }))
  mod = await import('../useServerEvents')
}

/** 模拟后端薄事件帧 */
function serverEvent(event: string, extra: Record<string, any> = {}) {
  wsHandler?.({
    type: 'event',
    event,
    entity: 'backtest_task',
    id: 'uuid-1',
    timestamp: new Date().toISOString(),
    ...extra,
  })
}

describe('useServerEvents', () => {
  beforeEach(() => {
    vi.useFakeTimers()
  })

  afterEach(() => {
    vi.useRealTimers()
    vi.doUnmock('@/composables/useWebSocket')
    vi.doUnmock('@/utils/toast')
    vi.restoreAllMocks()
  })

  it('on() 按 event 名分发,取消函数生效', async () => {
    await freshModule()
    const { on } = mod.useServerEvents()
    const h = vi.fn()
    const off = on('backtest.progress', h)

    serverEvent('backtest.progress', { status: 'running' })
    serverEvent('backtest.completed')
    expect(h).toHaveBeenCalledTimes(1)

    off()
    serverEvent('backtest.progress')
    expect(h).toHaveBeenCalledTimes(1)
  })

  it('onReconnect 在 isConnected 翻 true 时触发(含首连),翻 false 不触发', async () => {
    await freshModule()
    const { onReconnect } = mod.useServerEvents()
    const cb = vi.fn()
    onReconnect(cb)

    isConnected.value = true
    await nextTick()
    expect(cb).toHaveBeenCalledTimes(1)

    isConnected.value = false
    await nextTick()
    expect(cb).toHaveBeenCalledTimes(1)

    isConnected.value = true
    await nextTick()
    expect(cb).toHaveBeenCalledTimes(2) // 重连补齐
  })

  it('scheduleRefetch 同 key trailing 合并:静默期内反复 schedule 只执行最后一次', async () => {
    await freshModule()
    const { scheduleRefetch } = mod.useServerEvents()
    const fn1 = vi.fn()
    const fn2 = vi.fn()

    scheduleRefetch('list', fn1)
    await vi.advanceTimersByTimeAsync(500)
    scheduleRefetch('list', fn2) // 重置计时,丢弃 fn1
    await vi.advanceTimersByTimeAsync(999)
    expect(fn1).not.toHaveBeenCalled()
    expect(fn2).not.toHaveBeenCalled()

    await vi.advanceTimersByTimeAsync(1)
    expect(fn2).toHaveBeenCalledTimes(1)
    expect(fn1).not.toHaveBeenCalled()
  })

  it('scheduleRefetch 不同 key 互不干扰,fn 抛错不影响后续调度', async () => {
    await freshModule()
    const { scheduleRefetch } = mod.useServerEvents()
    const a = vi.fn()
    const b = vi.fn()
    const boom = vi.fn(() => {
      throw new Error('x')
    })

    scheduleRefetch('a', a)
    scheduleRefetch('b', boom)
    await vi.advanceTimersByTimeAsync(1000)
    expect(a).toHaveBeenCalledTimes(1)
    expect(boom).toHaveBeenCalledTimes(1) // 执行了但异常被吞

    const c = vi.fn()
    scheduleRefetch('c', c) // 上轮异常不影响继续调度
    await vi.advanceTimersByTimeAsync(1000)
    expect(c).toHaveBeenCalledTimes(1)
    expect(b).not.toHaveBeenCalled()
  })

  it('useNotificationToasts:notification 事件按 level 弹 toast,卸载后停', async () => {
    await freshModule()
    const { useNotificationToasts } = mod.useServerEvents()

    const App = defineComponent({
      setup() {
        useNotificationToasts()
        return () => null
      },
    })
    const el = document.createElement('div')
    const app = createApp(App)
    app.mount(el)

    serverEvent('notification', {
      entity: 'notification',
      data: { title: '回测完成', content: 'bt-1', level: 'success' },
    })
    expect(toastMocks.success).toHaveBeenCalledWith('回测完成 bt-1')

    serverEvent('notification', {
      entity: 'notification',
      data: { level: 'error', title: '失败' },
    })
    expect(toastMocks.error).toHaveBeenCalledWith('失败')

    // level 缺失 → info
    serverEvent('notification', { entity: 'notification', data: { title: '无级别' } })
    expect(toastMocks.info).toHaveBeenCalledWith('无级别')

    app.unmount()
    serverEvent('notification', { data: { title: '卸载后', level: 'info' } })
    expect(toastMocks.info).toHaveBeenCalledTimes(1)
  })
})
