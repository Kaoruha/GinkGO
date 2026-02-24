<template>
  <a-tag :color="color">
    <slot>{{ label }}</slot>
  </a-tag>
</template>

<script setup lang="ts">
import { computed } from 'vue'

const props = defineProps<{
  status: string
  type?: 'backtest' | 'task' | 'system' | 'order' | 'position'
}>()

// 回测状态配置
const backtestConfig: Record<string, { color: string; label: string }> = {
  created: { color: 'default', label: '待启动' },
  pending: { color: 'processing', label: '等待中' },
  running: { color: 'blue', label: '运行中' },
  completed: { color: 'success', label: '已完成' },
  failed: { color: 'error', label: '失败' },
  cancelled: { color: 'warning', label: '已取消' },
}

// 系统状态配置
const systemConfig: Record<string, { color: string; label: string }> = {
  online: { color: 'success', label: '在线' },
  offline: { color: 'error', label: '离线' },
  warning: { color: 'warning', label: '警告' },
  unknown: { color: 'default', label: '未知' },
}

// 订单状态配置
const orderConfig: Record<string, { color: string; label: string }> = {
  pending: { color: 'processing', label: '待提交' },
  submitted: { color: 'blue', label: '已提交' },
  filled: { color: 'success', label: '已成交' },
  cancelled: { color: 'default', label: '已取消' },
  rejected: { color: 'error', label: '已拒绝' },
}

// 持仓方向配置
const positionConfig: Record<string, { color: string; label: string }> = {
  long: { color: 'red', label: '多头' },
  short: { color: 'green', label: '空头' },
  flat: { color: 'default', label: '空仓' },
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
  return configMap[type][props.status] || { color: 'default', label: props.status }
})

const color = computed(() => config.value.color)
const label = computed(() => config.value.label)
</script>
