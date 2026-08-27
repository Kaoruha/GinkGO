/**
 * 类型/类别 → 展示配置(纯数据)。
 *
 * 与 useStatusFormat 的分工:那边管"状态"枚举(运行状态,StatusTag 按域消费);
 * 这里管"类型/类别"枚举(worker 类型、同步类型、通知渠道、账户状态、broker 生命周期)。
 * 条目形状与 useStatusFormat.StatusConfig 一致({tagClass, label}),
 * 可直接传给 useStatusFormat(config) 或 StatusTag 消费。
 */

export interface TypeEntry {
  /** tag CSS 类名,如 'tag-blue' */
  tagClass: string
  /** 中文展示名 */
  label: string
}

// ===== Worker 类型(SystemStatus 类型筛选用;countsKey 对应 system status 接口 counts 字段) =====
export interface WorkerTypeConfig extends TypeEntry {
  key: string
  /** system status 接口 counts 字段名 */
  countsKey: string
}

export const WORKER_TYPES: WorkerTypeConfig[] = [
  { key: 'data_worker', label: '数据Worker', tagClass: 'tag-purple', countsKey: 'data_workers' },
  { key: 'backtest_worker', label: '回测Worker', tagClass: 'tag-blue', countsKey: 'backtest_workers' },
  { key: 'execution_node', label: '执行节点', tagClass: 'tag-green', countsKey: 'execution_nodes' },
  { key: 'scheduler', label: '调度器', tagClass: 'tag-orange', countsKey: 'schedulers' },
  { key: 'task_timer', label: '定时器', tagClass: 'tag-magenta', countsKey: 'task_timers' },
]

const WORKER_TYPE_MAP = new Map(WORKER_TYPES.map(t => [t.key, t]))

export function workerTypeLabel(type: string): string {
  return WORKER_TYPE_MAP.get(type)?.label ?? type
}

export function workerTypeTagClass(type: string): string {
  return WORKER_TYPE_MAP.get(type)?.tagClass ?? 'tag-gray'
}

// ===== 账户状态(live/AccountConfig) =====
export const ACCOUNT_STATUS_CONFIG: Record<string, TypeEntry> = {
  enabled: { tagClass: 'tag-green', label: '已启用' },
  disabled: { tagClass: 'tag-gray', label: '已禁用' },
  connecting: { tagClass: 'tag-blue', label: '连接中' },
  disconnected: { tagClass: 'tag-orange', label: '已断开' },
  error: { tagClass: 'tag-red', label: '错误' },
}

// ===== Broker 生命周期(live/BrokerManagement,ui/Badge variant 消费) =====
export interface BadgeEntry {
  label: string
  variant: 'success' | 'secondary' | 'destructive' | 'outline'
}

export const BROKER_STATE_CONFIG: Record<string, BadgeEntry> = {
  uninitialized: { label: '未初始化', variant: 'secondary' },
  initializing: { label: '初始化中', variant: 'outline' },
  running: { label: '运行中', variant: 'success' },
  paused: { label: '已暂停', variant: 'secondary' },
  stopped: { label: '已停止', variant: 'secondary' },
  recovering: { label: '恢复中', variant: 'outline' },
  error: { label: '错误', variant: 'destructive' },
}

// ===== 数据同步类型(DataOverview / DataSync) =====
export const SYNC_TYPE_CONFIG: Record<string, TypeEntry> = {
  stockinfo: { tagClass: 'tag-green', label: '股票信息' },
  bars: { tagClass: 'tag-blue', label: 'K线数据' },
  ticks: { tagClass: 'tag-cyan', label: 'Tick数据' },
  adjustfactor: { tagClass: 'tag-purple', label: '复权因子' },
}

export const SYNC_STATUS_CONFIG: Record<string, TypeEntry> = {
  success: { tagClass: 'tag-green', label: '成功' },
  partial: { tagClass: 'tag-orange', label: '部分' },
  failed: { tagClass: 'tag-red', label: '失败' },
  running: { tagClass: 'tag-blue', label: '同步中' },
  // queued/lost(2026-08-18):派发即落库的生命周期两端——排队可见/消息丢失标记
  queued: { tagClass: 'tag-gray', label: '排队中' },
  lost: { tagClass: 'tag-gray', label: '已丢失' },
}

// ===== 通知渠道类型(NotificationManagement) =====
export const NOTIFICATION_TYPE_CONFIG: Record<string, TypeEntry> = {
  email: { tagClass: 'tag-blue', label: '邮件' },
  discord: { tagClass: 'tag-green', label: 'Discord' },
  system: { tagClass: 'tag-orange', label: '系统' },
  webhook: { tagClass: 'tag-gray', label: 'Webhook' },
}
