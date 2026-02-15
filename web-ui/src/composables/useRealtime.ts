import { ref, onUnmounted } from 'vue'

/**
 * 实时数据推送 Composable
 * 基于 Server-Sent Events (SSE) 的实时数据更新
 */

interface RealtimeOptions {
  url: string
  onMessage?: (data: any) => void
  onError?: (error: Event) => void
}

export function useRealtime(options: RealtimeOptions) {
  const eventSource = ref<EventSource | null>(null)
  const isConnected = ref(false)
  const data = ref<any>(null)
  const error = ref<string | null>(null)

  // 连接 SSE
  const connect = () => {
    if (eventSource.value) {
      eventSource.value.close()
    }

    try {
      eventSource.value = new EventSource(options.url)

      eventSource.value.onopen = () => {
        isConnected.value = true
        error.value = null
        options.onMessage?.(data.value)
      }

      eventSource.value.onmessage = (event) => {
        try {
          data.value = JSON.parse(event.data)
          options.onMessage?.(data.value)
        } catch {
          data.value = event.data
          options.onMessage?.(data.value)
        }
      }

      eventSource.value.onerror = (event) => {
        error.value = '连接失败'
        options.onError?.(event)
      }
    } catch (err: any) {
      error.value = err.message
    }
  }

  // 断开连接
  const disconnect = () => {
    eventSource.value?.close()
    isConnected.value = false
  }

  onUnmounted(() => {
    disconnect()
  })

  return {
    connect,
    disconnect,
    isConnected,
    data,
    error
  }
}
