<template>
  <span
    class="status-tag"
    :class="tagClass"
  >
    <slot>{{ label }}</slot>
  </span>
</template>

<script setup lang="ts">
import { computed } from 'vue'

const props = defineProps<{
  status: string
  type?: 'backtest' | 'task' | 'system' | 'order' | 'position' | 'worker' | 'infra' | 'execution' | 'enable'
}>()

// 回测状态配置（六态模型）
const backtestConfig: Record<string, { color: string; label: string; badgeStatus: string }> = {
  created: { color: 'gray', label: '待调度', badgeStatus: 'default' },
  pending: { color: 'blue', label: '排队中', badgeStatus: 'processing' },
  running: { color: 'cyan', label: '进行中', badgeStatus: 'processing' },
  completed: { color: 'green', label: '已完成', badgeStatus: 'success' },
  stopped: { color: 'orange', label: '已停止', badgeStatus: 'default' },
  failed: { color: 'red', label: '失败', badgeStatus: 'error' },
}

// 系统状态配置
const systemConfig: Record<string, { color: string; label: string }> = {
  online: { color: 'green', label: '在线' },
  offline: { color: 'red', label: '离线' },
  warning: { color: 'orange', label: '警告' },
  unknown: { color: 'gray', label: '未知' },
  healthy: { color: 'green', label: '健康' },
  degraded: { color: 'orange', label: '降级' },
  unhealthy: { color: 'red', label: '异常' },
}

// Worker/组件运行状态配置（SystemStatus/WorkerManagement 共用）
const workerConfig: Record<string, { color: string; label: string }> = {
  running: { color: 'green', label: '运行中' },
  active: { color: 'green', label: '活跃' },
  healthy: { color: 'green', label: '健康' },
  idle: { color: 'gray', label: '空闲' },
  stopped: { color: 'gray', label: '已停止' },
  stale: { color: 'orange', label: '心跳过期' },
  error: { color: 'red', label: '错误' },
}

// 基础设施连接状态配置（MySQL/Redis/Kafka/ClickHouse）
const infraConfig: Record<string, { color: string; label: string }> = {
  ok: { color: 'green', label: '已连接' },
  connected: { color: 'green', label: '已连接' },
  error: { color: 'red', label: '错误' },
  not_configured: { color: 'gray', label: '未配置' },
  unknown: { color: 'gray', label: '未知' },
}

// 任务执行结果配置（TaskTimerHistory / 通知发送记录共用）
const executionConfig: Record<string, { color: string; label: string }> = {
  pending: { color: 'gray', label: '待执行' },
  triggered: { color: 'blue', label: '执行中' },
  success: { color: 'green', label: '成功' },
  failed: { color: 'red', label: '失败' },
}

// 启用/禁用类配置（用户 / API Key / 通用开关态共用,label 可用 slot 覆盖)
const enableConfig: Record<string, { color: string; label: string }> = {
  active: { color: 'green', label: '启用' },
  disabled: { color: 'gray', label: '禁用' },
  inactive: { color: 'gray', label: '禁用' },
  expired: { color: 'red', label: '已过期' },
}

// 订单状态配置
const orderConfig: Record<string, { color: string; label: string }> = {
  pending: { color: 'cyan', label: '待提交' },
  submitted: { color: 'blue', label: '已提交' },
  filled: { color: 'green', label: '已成交' },
  cancelled: { color: 'gray', label: '已取消' },
  rejected: { color: 'red', label: '已拒绝' },
}

// 持仓方向配置
const positionConfig: Record<string, { color: string; label: string }> = {
  long: { color: 'red', label: '多头' },
  short: { color: 'green', label: '空头' },
  flat: { color: 'gray', label: '空仓' },
}

const configMap = {
  backtest: backtestConfig,
  task: backtestConfig,
  system: systemConfig,
  order: orderConfig,
  position: positionConfig,
  worker: workerConfig,
  infra: infraConfig,
  execution: executionConfig,
  enable: enableConfig,
}

const config = computed(() => {
  const type = props.type || 'backtest'
  return configMap[type][props.status] || { color: 'gray', label: props.status }
})

const tagClass = computed(() => `tag-${config.value.color}`)

const label = computed(() => config.value.label)
</script>

<style scoped>
.status-tag {
  display: inline-block;
  padding: 2px 8px;
  border-radius: var(--radius-sm);
  font-size: 11px;
  font-weight: 500;
}

</style>
