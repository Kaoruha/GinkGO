/**
 * WebSocket 连接管理
 * 用于接收实时更新通知
 */
import { ref, onMounted, onUnmounted } from 'vue'

type MessageHandler = (data: any) => void

const ws = ref<WebSocket | null>(null)
const isConnected = ref(false)
const handlers = new Map<string, Set<MessageHandler>>()

function connect(url: string = 'ws://localhost:8000/ws') {
  if (ws.value?.readyState === WebSocket.OPEN) {
    return
  }

  ws.value = new WebSocket(url)

  ws.value.onopen = () => {
    isConnected.value = true
    console.log('[WS] Connected')
  }

  ws.value.onclose = () => {
    isConnected.value = false
    console.log('[WS] Disconnected')
    // 5秒后重连
    setTimeout(() => connect(url), 5000)
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
  }
}
