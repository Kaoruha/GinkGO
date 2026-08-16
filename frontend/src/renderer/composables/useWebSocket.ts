/**
 * WebSocket 连接管理（全局单例，ADR-046 通知通道）
 * 连接后端 /ws/portfolio 端点，token 通过 query param 传递
 *
 * 注:Task 7 主进程 onBeforeSendHeaders 仅对 http(s) 注入 Authorization,
 * 不覆盖 ws(s) 握手。故双形态 ws 鉴权均走 query param(?token=...),
 * 后端(Task 5)支持 query 兜底。
 *
 * 连接生命周期模块自管理(ADR-046 修订):首个消费者调用 useWebSocket() 时
 * 绑定登录态 watch,登录即连/登出即断。connect/disconnect 不导出——
 * 曾因多组件并发调用 connect 产生孤儿连接竞态(后端 3~6s 断连抖动),
 * 唯一调用方由"接口不存在"结构性保证。
 */
import { ref, shallowRef, watch } from 'vue'
import { auth } from '@/composables/useAuth'
import { useAuthStore } from '@/stores/auth'

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

// 异步获取 ws URL:token 优先取内存 store(login() 第一行即赋值,零时序依赖),
// 回退 auth.getToken()(Electron IPC / localStorage)。
// 不直接读持久层:登录翻转瞬间生命周期 watch 触发 connect,而 saveAuth 的
// localStorage 写入在 await 链上晚于 watch flush——getToken 会读到旧值/null,
// 导致 connect 静默放弃或带过期 token 握手被 1008 拒(两出口均不自愈)
async function getWebSocketUrl(): Promise<string> {
  const cfg = window.appConfig
  const authStore = useAuthStore()
  const token = authStore.token || await auth.getToken()
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
    // (恢复路径:下次登录态翻转时生命周期 watch 重连)
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
    } catch {
      // 单个 handler 异常不影响其余 handler
    }
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

// —— 生命周期绑定:登录即连、登出即断(幂等,首个消费者触发) ——
let lifecycleBound = false
function bindLifecycle() {
  if (lifecycleBound) return
  lifecycleBound = true
  // useAuthStore 须在 pinia 就绪后调用:bindLifecycle 只随 useWebSocket()
  // 在组件 setup 内首次触发,时序上必然满足
  const authStore = useAuthStore()
  watch(
    () => authStore.isLoggedIn,
    (loggedIn) => {
      if (loggedIn) void connect()
      else disconnect()
    },
    { immediate: true },
  )
}

export function useWebSocket() {
  bindLifecycle()
  // 仅暴露订阅权;connect/disconnect 为模块私有(见文件头注释)
  return { isConnected, subscribe }
}
