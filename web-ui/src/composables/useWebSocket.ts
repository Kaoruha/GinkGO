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
  }
}
