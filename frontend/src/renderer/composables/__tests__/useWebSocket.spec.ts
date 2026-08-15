/**
 * useWebSocket 单元测试（ADR-046 健壮性）
 *
 * 策略:模块级单例状态 → vi.resetModules + 动态 import 每测重置;
 * FakeWebSocket 替身可控 readyState/事件派发;fake timers 驱动退避与 watchdog。
 */
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'

class FakeWebSocket {
  static instances: FakeWebSocket[] = []
  static OPEN = 1
  static CONNECTING = 0
  static CLOSING = 2
  static CLOSED = 3

  url: string
  readyState = FakeWebSocket.CONNECTING
  onopen: (() => void) | null = null
  onclose: ((event: { code: number }) => void) | null = null
  onerror: (() => void) | null = null
  onmessage: ((event: { data: string }) => void) | null = null
  sent: string[] = []
  closedWith: number | null = null

  constructor(url: string) {
    this.url = url
    FakeWebSocket.instances.push(this)
  }

  send(data: string) {
    this.sent.push(data)
  }

  // 浏览器语义:onclose 不在 close() 内同步派发,而是作为异步任务投递
  // (真实现依赖这一点:disconnect 先置 ws.value=null 再 close,迟到的
  // onclose 被孤儿守卫拦下,不会误排重连)
  close(code = 1000) {
    this.closedWith = code
    this.readyState = FakeWebSocket.CLOSED
    setTimeout(() => this.onclose?.({ code }), 0)
  }

  // 测试驱动辅助:模拟网络侧断开(onclose 同步派发)
  simulateClose(code = 1006) {
    this.readyState = FakeWebSocket.CLOSED
    this.onclose?.({ code })
  }

  simulateOpen() {
    this.readyState = FakeWebSocket.OPEN
    this.onopen?.()
  }

  simulateMessage(data: unknown) {
    this.onmessage?.({ data: JSON.stringify(data) })
  }
}

let useWebSocketMod: typeof import('../useWebSocket')

async function freshModule() {
  vi.resetModules()
  FakeWebSocket.instances = []
  vi.stubGlobal('WebSocket', FakeWebSocket)
  vi.doMock('@/composables/useAuth', () => ({
    auth: { getToken: async () => 'test-token' },
  }))
  useWebSocketMod = await import('../useWebSocket')
}

describe('useWebSocket', () => {
  beforeEach(() => {
    vi.useFakeTimers()
  })

  afterEach(() => {
    vi.useRealTimers()
    vi.unstubAllGlobals()
    vi.doUnmock('@/composables/useAuth')
    vi.restoreAllMocks()
  })

  it('并发 connect() 只建立一条连接(CONNECTING 竞态)', async () => {
    await freshModule()
    const { connect } = useWebSocketMod.useWebSocket()

    // 两个并发调用,getWebSocketUrl 的 await 窗口内都不让位
    await Promise.all([connect(), connect()])

    expect(FakeWebSocket.instances.length).toBe(1)
  })

  it('断开后指数退避重连,onopen 后退避复位', async () => {
    await freshModule()
    vi.spyOn(Math, 'random').mockReturnValue(0.5) // jitter 固定 1.0,退避精确 2s/4s/2s
    const { connect, isConnected } = useWebSocketMod.useWebSocket()
    await connect()
    const s1 = FakeWebSocket.instances[0]
    s1.simulateOpen()
    expect(isConnected.value).toBe(true)

    // 第一次断开:1000*2^1*jitter = 2s
    s1.simulateClose()
    expect(isConnected.value).toBe(false)
    await vi.advanceTimersByTimeAsync(2000)
    expect(FakeWebSocket.instances.length).toBe(2)

    // 升级路径:重连上了但没 open 就再断(连不上场景),退避升到 4s
    const s2 = FakeWebSocket.instances[1]
    s2.simulateClose()
    await vi.advanceTimersByTimeAsync(2000)
    expect(FakeWebSocket.instances.length).toBe(2) // 2s 时还没到
    await vi.advanceTimersByTimeAsync(2000)
    expect(FakeWebSocket.instances.length).toBe(3)

    // 成功连接后退避复位:open 后再断开,回到 2s 档(而非 8s)
    FakeWebSocket.instances[2].simulateOpen()
    FakeWebSocket.instances[2].simulateClose()
    await vi.advanceTimersByTimeAsync(2000)
    expect(FakeWebSocket.instances.length).toBe(4)
  })

  it('close(1008) 鉴权拒绝不重试', async () => {
    await freshModule()
    const { connect } = useWebSocketMod.useWebSocket()
    await connect()
    FakeWebSocket.instances[0].simulateOpen()
    FakeWebSocket.instances[0].simulateClose(1008)

    await vi.advanceTimersByTimeAsync(60_000)
    expect(FakeWebSocket.instances.length).toBe(1)
  })

  it('65s 无任何帧,watchdog 强制断开触发重连', async () => {
    await freshModule()
    vi.spyOn(Math, 'random').mockReturnValue(0.5)
    const { connect } = useWebSocketMod.useWebSocket()
    await connect()
    const s1 = FakeWebSocket.instances[0]
    s1.simulateOpen()

    // 不喂任何帧,推过 65s(watchdog 每 5s 检查一次,70s tick 触发 close)
    await vi.advanceTimersByTimeAsync(71_000)
    expect(s1.closedWith).not.toBeNull() // 被 watchdog close

    // close 的 onclose 异步派发 → 走重连路径(2s 档)
    await vi.advanceTimersByTimeAsync(2500)
    expect(FakeWebSocket.instances.length).toBe(2)
  })

  it('30s heartbeat 帧持续喂狗,连接保活超过 65s', async () => {
    await freshModule()
    const { connect, isConnected } = useWebSocketMod.useWebSocket()
    await connect()
    const s1 = FakeWebSocket.instances[0]
    s1.simulateOpen()

    // 每 30s 一个 heartbeat,推 3 个周期(90s) > 65s 阈值
    for (let i = 0; i < 3; i++) {
      await vi.advanceTimersByTimeAsync(30_000)
      s1.simulateMessage({ type: 'heartbeat' })
    }
    expect(s1.closedWith).toBeNull()
    expect(isConnected.value).toBe(true)
  })

  it('消息按 type/*/topic: 三通道分发,坏 JSON 静默', async () => {
    await freshModule()
    const { connect, subscribe } = useWebSocketMod.useWebSocket()
    await connect()
    const s1 = FakeWebSocket.instances[0]
    s1.simulateOpen()

    const onEvent = vi.fn()
    const onAny = vi.fn()
    const onTopic = vi.fn()
    subscribe('event', onEvent)
    subscribe('*', onAny)
    subscribe('topic:portfolio:x', onTopic)

    s1.simulateMessage({ type: 'event', event: 'backtest.failed' })
    s1.simulateMessage({ type: 'other', topic: 'portfolio:x' })
    s1.onmessage?.({ data: '{bad json' })

    expect(onEvent).toHaveBeenCalledTimes(1)
    expect(onAny).toHaveBeenCalledTimes(2)
    expect(onTopic).toHaveBeenCalledTimes(1)
  })

  it('孤儿 socket(已被覆盖)的 onclose 不误降状态、不触发重连', async () => {
    await freshModule()
    const { connect, disconnect, isConnected } = useWebSocketMod.useWebSocket()
    await connect()
    const orphan = FakeWebSocket.instances[0]
    orphan.simulateOpen()
    expect(isConnected.value).toBe(true)

    // 主动 disconnect 清空 ws.value 后,迟到的 onclose 是孤儿,须被守卫拦下
    disconnect()
    orphan.simulateClose(1006)

    expect(isConnected.value).toBe(false)
    await vi.advanceTimersByTimeAsync(60_000)
    // 孤儿 close 不得触发重连(连接是主动断开的)
    expect(FakeWebSocket.instances.length).toBe(1)
  })

  it('disconnect 后无残留定时器触发', async () => {
    await freshModule()
    vi.spyOn(Math, 'random').mockReturnValue(0.5)
    const { connect, disconnect, isConnected } = useWebSocketMod.useWebSocket()
    await connect()
    FakeWebSocket.instances[0].simulateOpen()
    FakeWebSocket.instances[0].simulateClose()
    // 此刻已排定一个 2s 重连 timer
    disconnect()

    await vi.advanceTimersByTimeAsync(120_000)
    expect(FakeWebSocket.instances.length).toBe(1)
    expect(isConnected.value).toBe(false)
  })
})
