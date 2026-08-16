/**
 * 低层可重连 WebSocket 工厂
 *
 * 与全局单例 useWebSocket(/ws/portfolio,subscribe 协议)互不相干:
 * 本工厂只管"一条按需创建的 WS 连接 + 断线重连",不管理登录态、
 * 不做消息解析(原始字符串透传给调用方)。MarketData(/ws,
 * {action,symbols,data_types} 协议)自裸写 WS 迁入。
 *
 * 设计要点:
 * - socket 存闭包普通变量(非 ref):无响应式需求,绕开"socket 须
 *   shallowRef"的深响应陷阱
 * - url 每次重连重新解析(端口/协议可能变化,如 https→wss)
 * - enabled() 闸门:返回 false 时不安排重连(服务降级期停止重试)
 * - disconnect() 语义 = 显式关闭 + 不再重连(组件卸载/用户手动断开)
 */

export interface ReconnectingSocketOptions {
  /** 每次连接/重连时重新解析的目标地址 */
  url: () => string
  /** 收到消息(原始字符串);JSON 解析由调用方决定 */
  onMessage: (data: string) => void
  /** 连接状态翻转(true=open,false=close/error) */
  onStatusChange?: (connected: boolean) => void
  /** 重连闸门;缺省恒 true */
  enabled?: () => boolean
  /** 重连延迟(ms);attempt 从 1 起。缺省固定 5000(与既有行为等价) */
  reconnectDelay?: (attempt: number) => number
}

export interface ReconnectingSocket {
  connect: () => void
  /** 显式断开:关连接且不再重连 */
  disconnect: () => void
  /** 发送(未连接时静默丢弃) */
  send: (data: string) => void
}

export function createReconnectingSocket(options: ReconnectingSocketOptions): ReconnectingSocket {
  const { url, onMessage, onStatusChange, enabled = () => true } = options
  const delay = options.reconnectDelay ?? (() => 5000)

  let socket: WebSocket | null = null
  let shouldReconnect = false
  let attempt = 0
  let reconnectTimer: ReturnType<typeof setTimeout> | null = null

  const setStatus = (connected: boolean) => onStatusChange?.(connected)

  const scheduleReconnect = () => {
    if (reconnectTimer !== null) return
    attempt++
    reconnectTimer = setTimeout(() => {
      reconnectTimer = null
      // 闸门关闭(如服务降级)时不再重试;调用方恢复后重新 connect()
      if (shouldReconnect && enabled()) connect()
    }, delay(attempt))
  }

  const connect = () => {
    if (reconnectTimer !== null) {
      clearTimeout(reconnectTimer)
      reconnectTimer = null
    }
    shouldReconnect = true
    attempt = 0
    try {
      socket = new WebSocket(url())
    } catch (e) {
      console.error('[WS] 创建连接失败:', e)
      setStatus(false)
      scheduleReconnect()
      return
    }
    socket.onopen = () => {
      attempt = 0
      setStatus(true)
    }
    socket.onmessage = (event) => onMessage(event.data as string)
    socket.onclose = () => {
      socket = null
      setStatus(false)
      if (shouldReconnect && enabled()) scheduleReconnect()
    }
    socket.onerror = (error) => {
      console.error('[WS] WebSocket 错误:', error)
      setStatus(false)
    }
  }

  const disconnect = () => {
    shouldReconnect = false
    if (reconnectTimer !== null) {
      clearTimeout(reconnectTimer)
      reconnectTimer = null
    }
    if (socket) {
      socket.close()
      socket = null
    }
    setStatus(false)
  }

  const send = (data: string) => {
    if (socket && socket.readyState === WebSocket.OPEN) {
      socket.send(data)
    }
  }

  return { connect, disconnect, send }
}
