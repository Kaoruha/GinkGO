<template>
  <a-card class="stat-card" :class="{ 'stat-card-clickable': clickable }">
    <a-statistic :title="title" :value="displayValue" :suffix="suffix" :prefix="prefix" :value-style="valueStyle">
      <template v-if="$slots.prefix" #prefix><slot name="prefix" /></template>
      <template v-if="$slots.suffix" #suffix><slot name="suffix" /></template>
    </a-statistic>
  </a-card>
</template>

<script setup lang="ts">
import { computed } from 'vue'

const props = withDefaults(defineProps<{
  title: string
  value: number | string | null | undefined
  type?: 'number' | 'percent' | 'money' | 'decimal'
  decimals?: number
  prefix?: string
  suffix?: string
  color?: 'auto' | 'positive' | 'negative' | 'neutral'
  clickable?: boolean
}>(), {
  type: 'number',
  decimals: 2,
  color: 'neutral',
  clickable: false,
})

const formatValue = (val: number | string | null | undefined): string | number => {
  if (val === null || val === undefined) return '-'

  const n = typeof val === 'string' ? parseFloat(val) : val
  if (isNaN(n)) return '-'

  switch (props.type) {
    case 'percent':
      return n * 100
    case 'money':
      return n.toLocaleString('zh-CN', { minimumFractionDigits: props.decimals, maximumFractionDigits: props.decimals })
    case 'decimal':
      return n.toFixed(props.decimals)
    default:
      return n
  }
}

const displayValue = computed(() => formatValue(props.value))

const computedSuffix = computed(() => {
  if (props.suffix) return props.suffix
  if (props.type === 'percent') return '%'
  return undefined
})

const valueStyle = computed(() => {
  if (props.color !== 'auto') {
    const colors: Record<string, string> = {
      positive: '#cf1322',
      negative: '#3f8600',
      neutral: 'rgba(0, 0, 0, 0.85)',
    }
    return { color: colors[props.color] }
  }

  // auto: 根据值判断颜色
  const n = typeof props.value === 'string' ? parseFloat(props.value) : props.value
  if (n === null || n === undefined || isNaN(n)) return {}

  if (n > 0) return { color: '#cf1322' }
  if (n < 0) return { color: '#3f8600' }
  return {}
})
</script>

<style scoped>
.stat-card {
  height: 100%;
}
.stat-card-clickable {
  cursor: pointer;
  transition: box-shadow 0.2s;
}
.stat-card-clickable:hover {
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
}
</style>
