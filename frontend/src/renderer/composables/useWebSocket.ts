/**
 * WebSocket 连接管理（全局单例，ADR-046 通知通道）
 * 连接后端 /ws/portfolio 端点，token 通过 query param 传递
 *
 * 注:Task 7 主进程 onBeforeSendHeaders 仅对 http(s) 注入 Authorization,
 * 不覆盖 ws(s) 握手。故双形态 ws 鉴权均走 query param(?token=...),
 * 后端(Task 5)支持 query 兜底。
 *
 * 连接生命周期归登录态(App.vue watch isLoggedIn 连/断),非组件 onMounted。
 */
import { ref, shallowRef } from 'vue'
import { auth } from '@/composables/useAuth'

type MessageHandler = (data: any) => void

// shallowRef:socket 实例不做深响应代理。深 ref 会把 ws.value 包成 reactive
// 代理,ws.value !== socket 恒真,身份守卫(孤儿拦截)全部失效
const ws = shallowRef<WebSocket | null>(null)
const isConnected = ref(false)
const handlers = new Map<string, Set<MessageHandler>>()
const pendingTopics = new Set<string>()

let reconnectTimer: ReturnType<typeof setTimeout> | null = null
let retryCount = 0
const BASE_BACKOFF = 1000
const MAX_BACKOFF = 30000

// 心跳 watchdog:服务端每 30s 发 heartbeat,任意帧都喂狗;
// 65s 无帧视为半开连接(TCP 未断但对端已死),主动 close 触发重连
let lastMessageAt = 0
let watchdogTimer: ReturnType<typeof setInterval> | null = null
const WATCHDOG_MS = 65_000

// 异步获取 ws URL:token 经 useAuth 收口
// - Electron 形态:auth.getToken() 走 IPC 拉 safeStorage
// - 浏览器形态:auth.getToken() 读 localStorage
async function getWebSocketUrl(): Promise<string> {
  const cfg = window.appConfig
  const token = await auth.getToken()
  if (cfg?.wsBase) {
    // Electron 形态:用配置的 wsBase
    let url = `${cfg.wsBase}/ws/portfolio`
    if (token) url += `?token=${encodeURIComponent(token)}`
    return url
  }
  // 浏览器形态:原逻辑
  const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
  let url = `${protocol}//${window.location.host}/ws/portfolio`
  if (token) url += `?token=${encodeURIComponent(token)}`
  return url
}

function sendSubscribe(topic: string) {
  if (ws.value?.readyState === WebSocket.OPEN) {
    ws.value.send(JSON.stringify({ type: 'subscribe', topic }))
  } else {
    pendingTopics.add(topic)
  }
}

function armWatchdog() {
  lastMessageAt = Date.now()
  if (!watchdogTimer) {
    watchdogTimer = setInterval(() => {
      if (Date.now() - lastMessageAt > WATCHDOG_MS) ws.value?.close()
    }, 5000)
  }
}

function stopWatchdog() {
  if (watchdogTimer) {
    clearInterval(watchdogTimer)
    watchdogTimer = null
  }
}

function openSocket(wsUrl: string) {
  // 并发 connect 会多次 openSocket 覆盖 ws.value,被覆盖的旧 socket 成孤儿:
  // 孤儿被浏览器回收断开时,其 onclose 误降 isConnected 并叠加多余重连
  // (后端日志表现为连接 3~6 秒后断一条的抖动)。故每个回调先验身份。
  const socket = new WebSocket(wsUrl)
  ws.value = socket

  socket.onopen = () => {
    if (ws.value !== socket) return // 迟到的旧连接 open,已被覆盖,不拉高状态
    isConnected.value = true
    retryCount = 0
    for (const topic of pendingTopics) {
      sendSubscribe(topic)
    }
    pendingTopics.clear()
    armWatchdog()
  }

  socket.onclose = (event) => {
    if (ws.value !== socket) return // 孤儿连接关闭,不影响全局状态
    isConnected.value = false
    stopWatchdog()
    // 1008 = auth rejected (policy violation), don't retry
    // (恢复路径:下次登录态翻转时 App.vue 重连)
    if (event.code === 1008) return
    retryCount++
    if (reconnectTimer) clearTimeout(reconnectTimer) // 防重连定时器叠加
    // 无限重连:指数退避 + 抖动(防同刻风暴);重新解析 URL 刷新 token
    const backoff = Math.min(BASE_BACKOFF * 2 ** retryCount, MAX_BACKOFF)
    const delay = backoff * (0.75 + Math.random() * 0.5)
    reconnectTimer = setTimeout(() => { void connect() }, delay)
  }

  socket.onerror = () => {}

  socket.onmessage = (event) => {
    if (ws.value !== socket) return // 孤儿连接的消息不再分发
    lastMessageAt = Date.now() // 任意帧(含 heartbeat)喂狗
    try {
      const data = JSON.parse(event.data)
      const type = data.type

      const typeHandlers = handlers.get(type)
      if (typeHandlers) typeHandlers.forEach(h => h(data))

      const wildcardHandlers = handlers.get('*')
      if (wildcardHandlers) wildcardHandlers.forEach(h => h(data))

      if (data.topic) {
        const topicHandlers = handlers.get(`topic:${data.topic}`)
        if (topicHandlers) topicHandlers.forEach(h => h(data))
      }
    } catch {}
  }
}

// connect 异步化:需先 await getWebSocketUrl()(token 异步)
// urlOverride 保留兼容;无参时重新解析(覆盖重连场景)
async function connect(urlOverride?: string): Promise<void> {
  if (ws.value?.readyState === WebSocket.OPEN) return
  // CONNECTING 也拦截:await getWebSocketUrl() 的窗口期内并发调用会各自
  // new WebSocket 产生孤儿连接(多组件 onMounted 同时触发 connect 的竞态)
  if (ws.value?.readyState === WebSocket.CONNECTING) return
  const wsUrl = urlOverride ?? await getWebSocketUrl()
  if (ws.value?.readyState === WebSocket.OPEN || ws.value?.readyState === WebSocket.CONNECTING) {
    return // await 期间已有并发调用建连,让位
  }
  if (!wsUrl.includes('token=')) return // 已登出:放弃连接
  openSocket(wsUrl)
}

function disconnect() {
  if (reconnectTimer) {
    clearTimeout(reconnectTimer)
    reconnectTimer = null
  }
  stopWatchdog()
  retryCount = 0
  if (ws.value) {
    ws.value.close()
    ws.value = null
  }
  isConnected.value = false
}

function subscribe(eventType: string, handler: MessageHandler) {
  if (!handlers.has(eventType)) {
    handlers.set(eventType, new Set())
  }
  handlers.get(eventType)!.add(handler)

  if (eventType.startsWith('topic:')) {
    sendSubscribe(eventType.slice(6))
  }

  return () => {
    handlers.get(eventType)?.delete(handler)
  }
}

export function useWebSocket() {
  // 连接生命周期由 App.vue 按登录态管理,这里仅暴露访问器
  return { isConnected, subscribe, connect, disconnect }
}
