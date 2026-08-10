/**
 * WebSocket 连接管理
 * 连接后端 /ws/portfolio 端点，token 通过 query param 传递
 *
 * 注:Task 7 主进程 onBeforeSendHeaders 仅对 http(s) 注入 Authorization,
 * 不覆盖 ws(s) 握手。故双形态 ws 鉴权均走 query param(?token=...),
 * 后端(Task 5)支持 query 兜底。
 */
import { ref, onMounted, onUnmounted } from 'vue'
import { auth } from '@/composables/useAuth'

type MessageHandler = (data: any) => void

const ws = ref<WebSocket | null>(null)
const isConnected = ref(false)
const handlers = new Map<string, Set<MessageHandler>>()
const pendingTopics = new Set<string>()

let reconnectTimer: ReturnType<typeof setTimeout> | null = null
let retryCount = 0
const MAX_RETRIES = 3

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

function openSocket(wsUrl: string) {
  ws.value = new WebSocket(wsUrl)

  ws.value.onopen = () => {
    isConnected.value = true
    retryCount = 0
    for (const topic of pendingTopics) {
      sendSubscribe(topic)
    }
    pendingTopics.clear()
  }

  ws.value.onclose = (event) => {
    isConnected.value = false
    // 1008 = auth rejected (policy violation), don't retry
    if (event.code === 1008) return
    if (retryCount < MAX_RETRIES) {
      retryCount++
      // 重连:重新解析 URL(刷新 token,可能已登出或刷新)
      reconnectTimer = setTimeout(() => { void connect() }, 5000)
    }
  }

  ws.value.onerror = () => {}

  ws.value.onmessage = (event) => {
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
  const wsUrl = urlOverride ?? await getWebSocketUrl()
  openSocket(wsUrl)
}

function disconnect() {
  if (reconnectTimer) {
    clearTimeout(reconnectTimer)
    reconnectTimer = null
  }
  if (ws.value) {
    ws.value.close()
    ws.value = null
  }
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
  onMounted(() => {
    if (!isConnected.value) connect()
  })

  onUnmounted(() => {
    // 保持全局连接
  })

  return { isConnected, subscribe, connect, disconnect }
}
