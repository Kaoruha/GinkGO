/**
 * WebSocket 连接管理
 * 连接后端 /ws/portfolio 端点，token 通过 query param 传递
 */
import { ref, onMounted, onUnmounted } from 'vue'

type MessageHandler = (data: any) => void

const ws = ref<WebSocket | null>(null)
const isConnected = ref(false)
const handlers = new Map<string, Set<MessageHandler>>()
const pendingTopics = new Set<string>()

let reconnectTimer: ReturnType<typeof setTimeout> | null = null
let retryCount = 0
const MAX_RETRIES = 3

function getWebSocketUrl(): string {
  const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
  const token = localStorage.getItem('access_token')
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

function connect(url?: string) {
  if (ws.value?.readyState === WebSocket.OPEN) return

  const wsUrl = url || getWebSocketUrl()
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
      reconnectTimer = setTimeout(() => connect(wsUrl), 5000)
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
