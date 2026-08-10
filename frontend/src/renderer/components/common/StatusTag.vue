<template>
  <span class="status-tag" :class="tagClass">
    <slot>{{ label }}</slot>
  </span>
</template>

<script setup lang="ts">
import { computed } from 'vue'

const props = defineProps<{
  status: string
  type?: 'backtest' | 'task' | 'system' | 'order' | 'position'
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
  border-radius: 4px;
  font-size: 11px;
  font-weight: 500;
}

</style>
