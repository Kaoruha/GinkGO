/**
 * 统一的回测WebSocket处理composable
 * 用于减少各组件中重复的WebSocket订阅和实时更新逻辑
 */
import { ref, watch, onUnmounted, Ref, CallableFunction } from 'vue'

/**
 * WebSocket消息数据接口
 */
interface WebSocketMessage {
  task_id?: string
  task_uuid?: string
  event_type?: string
  [key: string]: any
}

/**
 * 回测WebSocket处理选项
 */
interface BacktestWebSocketOptions {
  // 任务ID获取函数（支持动态任务ID）
  getTaskId: () => string | null
  // 消息处理回调
  onMessage: (data: WebSocketMessage) => void
  // 是否启用断线轮询
  enablePolling?: boolean
  // 轮询间隔（毫秒）
  pollingInterval?: number
  // 轮询数据获取函数
  pollingFetch?: () => Promise<void>
}

/**
 * 统一的回测WebSocket处理composable
 * @param options 配置选项
 * @returns WebSocket状态和控制方法
 */
export function useBacktestWebSocket(options: BacktestWebSocketOptions) {
  const isConnected = ref(false)
  const isPolling = ref(false)
  let unsubscribe: CallableFunction | null = null
  let pollTimer: number | null = null

  /**
   * 处理WebSocket消息
   * @param data 接收到的消息数据
   */
  const handleMessage = (data: WebSocketMessage) => {
    const currentTaskId = options.getTaskId()
    const msgTaskId = data.task_id || data.task_uuid

    // 如果没有当前任务ID或消息任务ID，忽略消息
    if (!currentTaskId || !msgTaskId) return

    // 只处理属于当前任务的消息
    if (currentTaskId === msgTaskId) {
      options.onMessage(data)
    }
  }

  /**
   * 设置WebSocket订阅
   * @param subscribeFn WebSocket订阅函数
   */
  const setupSubscription = (subscribeFn: (channel: string, callback: (data: any) => void) => CallableFunction) => {
    // 清理之前的订阅
    if (unsubscribe) {
      unsubscribe()
      unsubscribe = null
    }

    // 创建新订阅
    unsubscribe = subscribeFn('*', handleMessage)
  }

  /**
   * 设置断线轮询
   */
  const setupPolling = () => {
    if (!options.enablePolling || !options.pollingFetch) return

    // 清理之前的轮询
    if (pollTimer) {
      clearInterval(pollTimer)
      pollTimer = null
    }

    // 监听连接状态，断线时启动轮询
    watch(isConnected, (connected) => {
      if (pollTimer) {
        clearInterval(pollTimer)
        pollTimer = null
      }
      isPolling.value = false

      if (!connected && options.pollingFetch) {
        isPolling.value = true
        pollTimer = window.setInterval(() => {
          options.pollingFetch?.()
        }, options.pollingInterval || 5000)
      }
    }, { immediate: true })
  }

  /**
   * 手动启动轮询
   */
  const startPolling = () => {
    if (!options.pollingFetch) return

    isPolling.value = true
    if (pollTimer) clearInterval(pollTimer)

    pollTimer = window.setInterval(() => {
      options.pollingFetch?.()
    }, options.pollingInterval || 5000)
  }

  /**
   * 停止轮询
   */
  const stopPolling = () => {
    if (pollTimer) {
      clearInterval(pollTimer)
      pollTimer = null
    }
    isPolling.value = false
  }

  /**
   * 清理资源
   */
  const cleanup = () => {
    if (unsubscribe) {
      unsubscribe()
      unsubscribe = null
    }
    stopPolling()
  }

  // 组件卸载时自动清理
  onUnmounted(cleanup)

  return {
    isConnected,
    isPolling,
    setupSubscription,
    setupPolling,
    startPolling,
    stopPolling,
    cleanup
  }
}

/**
 * 简化版的WebSocket订阅hook
 * 用于只需要基本订阅功能的场景
 */
export function useWebSocketSubscription(
  getTaskId: () => string | null,
  onMessage: (data: any) => void
) {
  const { setupSubscription, cleanup } = useBacktestWebSocket({
    getTaskId,
    onMessage
  })

  return {
    setupSubscription,
    cleanup
  }
}