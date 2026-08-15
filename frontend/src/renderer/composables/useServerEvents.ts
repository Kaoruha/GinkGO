/**
 * 服务端事件层（ADR-046 全局通知通道前端半边）
 *
 * 职责:消费 /ws/portfolio 上的薄事件信封(type:'event'),按 event 名分发;
 * 连接每次建立(含首连)触发 catchup(幂等 REST 重拉,替代全局 seq);
 * scheduleRefetch 按 key trailing 合并——同一页面 N 个事件塌缩成一次列表刷新。
 *
 * 依赖 useWebSocket 的连接生命周期(App.vue 按登录态连/断),本模块不建连。
 */
import { watch, onUnmounted } from 'vue'
import { useWebSocket } from '@/composables/useWebSocket'
import { message } from '@/utils/toast'

/** 后端薄事件信封(见 api/websocket/events.py build_event) */
export interface ServerEvent {
  type: 'event'
  event: string
  entity: 'backtest_task' | 'deployment' | 'worker' | 'notification' | string
  id: string
  status?: string
  data?: Record<string, any>
  timestamp: string
}

type EventHandler = (e: ServerEvent) => void
type Unsubscribe = () => void

const eventHandlers = new Map<string, Set<EventHandler>>()
const reconnectCallbacks = new Set<() => void>()

// per-key trailing throttle:同 key 反复 schedule,只有最后一次的 fn 会在
// 静默 delay 后执行(事件风暴 → 一次 REST 刷新)
const refetchTimers = new Map<string, ReturnType<typeof setTimeout>>()
const DEFAULT_REFETCH_DELAY = 1000

let booted = false

function dispatch(e: ServerEvent) {
  const handlers = eventHandlers.get(e.event)
  if (handlers) handlers.forEach(h => h(e))

  const wildcard = eventHandlers.get('*')
  if (wildcard) wildcard.forEach(h => h(e))
}

function bootstrap() {
  if (booted) return
  booted = true

  const { isConnected, subscribe } = useWebSocket()

  subscribe('event', (data: ServerEvent) => {
    if (data?.event) dispatch(data)
  })

  // 重连补齐(替代全局 seq):每次连上——含首连——触发 catchup 回调,
  // 由页面做幂等全量刷新,补齐断线窗口内丢失的事件
  watch(isConnected, (now) => {
    if (!now) return
    reconnectCallbacks.forEach(cb => {
      try {
        cb()
      } catch {}
    })
  })
}

/** 订阅指定事件名;返回取消函数 */
function on(eventName: string, handler: EventHandler): Unsubscribe {
  if (!eventHandlers.has(eventName)) {
    eventHandlers.set(eventName, new Set())
  }
  eventHandlers.get(eventName)!.add(handler)
  bootstrap()
  return () => {
    eventHandlers.get(eventName)?.delete(handler)
  }
}

/** 注册 catchup 回调:连接每次建立(含首连)触发 */
function onReconnect(cb: () => void): Unsubscribe {
  reconnectCallbacks.add(cb)
  bootstrap()
  return () => {
    reconnectCallbacks.delete(cb)
  }
}

/**
 * 按 key trailing 合并刷新:同 key 在 delay 静默期内再次 schedule 会重置计时,
 * 只执行最后注册的 fn。页面级 key 让 N 个任务事件塌缩成一次列表刷新。
 */
function scheduleRefetch(key: string, fn: () => void, delay = DEFAULT_REFETCH_DELAY) {
  const existing = refetchTimers.get(key)
  if (existing) clearTimeout(existing)
  refetchTimers.set(key, setTimeout(() => {
    refetchTimers.delete(key)
    try {
      fn()
    } catch {}
  }, delay))
}

/** 通知事件 → toast(级别映射后端 data.level) */
export function useNotificationToasts() {
  const off = on('notification', (e) => {
    const level = (e.data?.level as 'success' | 'error' | 'info' | 'warning') || 'info'
    const title = e.data?.title || '通知'
    const content = e.data?.content ? ` ${e.data.content}` : ''
    const show = message[level] ?? message.info
    show(`${title}${content}`)
  })
  onUnmounted(off)
}

export function useServerEvents() {
  return { on, onReconnect, scheduleRefetch, useNotificationToasts }
}
