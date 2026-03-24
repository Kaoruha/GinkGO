<template>
  <div class="stat-card" :class="{ 'stat-card-clickable': clickable }">
    <div class="stat-title">{{ title }}</div>
    <div class="stat-value" :style="valueStyle">
      <span v-if="$slots.prefix" class="stat-prefix"><slot name="prefix" /></span>
      <span class="stat-number">{{ displayValue }}</span>
      <span v-if="computedSuffix" class="stat-suffix">{{ computedSuffix }}</span>
      <span v-if="suffix" class="stat-suffix"><slot name="suffix" /></span>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'

const props = withDefaults(defineProps<{
  title: string
  value: number | string | null | undefined
  type?: 'number' | 'percent' | 'money' | 'decimal'
  decimals?: number
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
  if (props.suffix) return undefined
  if (props.type === 'percent') return '%'
  return undefined
})

const valueStyle = computed(() => {
  if (props.color !== 'auto') {
    const colors: Record<string, string> = {
      positive: '#cf1322',
      negative: '#3f8600',
      neutral: '#ffffff',
    }
    return { color: colors[props.color] }
  }

  // auto: 根据值判断颜色
  const n = typeof props.value === 'string' ? parseFloat(props.value) : props.value
  if (n === null || n === undefined || isNaN(n)) return {}

  if (n > 0) return { color: '#cf1322' }
  if (n < 0) return { color: '#3f8600' }
  return { color: '#ffffff' }
})
</script>

<style scoped>
.stat-card {
  background: #1a1a2e;
  border-radius: 8px;
  border: 1px solid #2a2a3e;
  padding: 20px;
  height: 100%;
}

.stat-card-clickable {
  cursor: pointer;
  transition: box-shadow 0.2s;
}

.stat-card-clickable:hover {
  box-shadow: 0 2px 8px rgba(24, 144, 255, 0.2);
}

.stat-title {
  font-size: 13px;
  color: #8a8a9a;
  margin-bottom: 12px;
}

.stat-value {
  display: flex;
  align-items: baseline;
  justify-content: center;
  gap: 4px;
}

.stat-prefix {
  font-size: 14px;
}

.stat-number {
  font-size: 28px;
  font-weight: 600;
}

.stat-suffix {
  font-size: 14px;
  color: #8a8a9a;
}
</style>
