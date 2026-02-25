<<<<<<< HEAD
import { ref, onMounted, onUnmounted } from 'vue'
import { message } from 'ant-design-vue'

export type WebSocketMessage = {
  type: string
  data: unknown
  timestamp: string
}

export function useWebSocket(url: string, autoReconnect = true) {
  const ws = ref<WebSocket | null>(null)
  const connected = ref(false)
  const data = ref<WebSocketMessage | null>(null)
  const error = ref<Event | null>(null)

  let reconnectTimer: ReturnType<typeof setTimeout> | null = null
  let heartbeatTimer: ReturnType<typeof setInterval> | null = null

  const connect = () => {
    const token = localStorage.getItem('access_token')
    if (!token) {
      message.error('未登录，无法建立WebSocket连接')
      return
    }

    const wsUrl = `${url}?token=${token}`
    ws.value = new WebSocket(wsUrl)

    ws.value.onopen = () => {
      connected.value = true
      error.value = null

      // 启动心跳
      heartbeatTimer = setInterval(() => {
        if (ws.value?.readyState === WebSocket.OPEN) {
          ws.value.send(JSON.stringify({ type: 'ping' }))
        }
      }, 30000)
    }

    ws.value.onmessage = (event) => {
      try {
        const message = JSON.parse(event.data) as WebSocketMessage

        // 处理pong响应
        if (message.type === 'pong') {
          return
        }

        data.value = message
      } catch (e) {
        console.error('Failed to parse WebSocket message:', e)
      }
    }

    ws.value.onerror = (event) => {
      error.value = event
    }

    ws.value.onclose = () => {
      connected.value = false
      if (heartbeatTimer) {
        clearInterval(heartbeatTimer)
        heartbeatTimer = null
      }

      // 自动重连
      if (autoReconnect && !reconnectTimer) {
        reconnectTimer = setTimeout(() => {
          reconnectTimer = null
          connect()
        }, 3000)
      }
    }
  }

  const disconnect = () => {
    if (reconnectTimer) {
      clearTimeout(reconnectTimer)
      reconnectTimer = null
    }
    if (heartbeatTimer) {
      clearInterval(heartbeatTimer)
      heartbeatTimer = null
    }
    if (ws.value) {
      ws.value.close()
      ws.value = null
    }
    connected.value = false
  }

  const send = (message: Record<string, unknown>) => {
    if (ws.value?.readyState === WebSocket.OPEN) {
      ws.value.send(JSON.stringify(message))
    } else {
      message.warning('WebSocket未连接')
    }
  }

  onMounted(() => {
    connect()
  })

  onUnmounted(() => {
    disconnect()
  })

  return {
    connected,
    data,
    error,
    send,
    disconnect
=======
/**
 * WebSocket 连接管理
 * 用于接收实时更新通知
 */
import { ref, onMounted, onUnmounted } from 'vue'

type MessageHandler = (data: any) => void

const ws = ref<WebSocket | null>(null)
const isConnected = ref(false)
const handlers = new Map<string, Set<MessageHandler>>()

function getWebSocketUrl(): string {
  // 使用当前页面的 host 构建 WebSocket URL
  const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
  const host = window.location.host
  // 如果是前端开发服务器 (5173)，使用后端端口 8000
  const wsHost = host.includes(':5173') ? host.replace(':5173', ':8000') : host
  return `${protocol}//${wsHost}/ws`
}

function connect(url?: string) {
  if (ws.value?.readyState === WebSocket.OPEN) {
    return
  }

  const wsUrl = url || getWebSocketUrl()
  console.log('[WS] Connecting to', wsUrl)
  ws.value = new WebSocket(wsUrl)

  ws.value.onopen = () => {
    isConnected.value = true
    console.log('[WS] Connected')
  }

  ws.value.onclose = () => {
    isConnected.value = false
    console.log('[WS] Disconnected')
    // 5秒后重连
    setTimeout(() => connect(wsUrl), 5000)
  }

  ws.value.onerror = (error) => {
    console.error('[WS] Error:', error)
  }

  ws.value.onmessage = (event) => {
    try {
      const data = JSON.parse(event.data)
      const type = data.type

      // 调用对应类型的所有处理器
      const typeHandlers = handlers.get(type)
      if (typeHandlers) {
        typeHandlers.forEach(handler => handler(data))
      }

      // 调用通配符处理器
      const wildcardHandlers = handlers.get('*')
      if (wildcardHandlers) {
        wildcardHandlers.forEach(handler => handler(data))
      }
    } catch (e) {
      console.error('[WS] Parse error:', e)
    }
  }
}

function disconnect() {
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

  // 返回取消订阅函数
  return () => {
    handlers.get(eventType)?.delete(handler)
  }
}

export function useWebSocket() {
  onMounted(() => {
    if (!isConnected.value) {
      connect()
    }
  })

  onUnmounted(() => {
    // 组件卸载时不断开连接，保持全局连接
  })

  return {
    isConnected,
    subscribe,
    connect,
    disconnect,
>>>>>>> 011-quant-research
  }
}
