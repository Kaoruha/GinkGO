<template>
  <div
    class="stat-card m-fade-up"
    :class="{ 'stat-card-clickable': clickable }"
  >
    <div class="stat-title">
      {{ title }}
    </div>
    <div
      class="stat-value"
      :style="valueStyle"
    >
      <span
        v-if="$slots.prefix"
        class="stat-prefix"
      ><slot name="prefix" /></span>
      <span class="stat-number">{{ displayValue }}</span>
      <span
        v-if="computedSuffix"
        class="stat-suffix"
      >{{ computedSuffix }}</span>
      <span
        v-if="suffix"
        class="stat-suffix"
      ><slot name="suffix" /></span>
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
  if (props.suffix) return props.suffix
  if (props.type === 'percent') return '%'
  return undefined
})

const valueStyle = computed(() => {
  if (props.color !== 'auto') {
    const colors: Record<string, string> = {
      positive: 'hsl(var(--success))',
      negative: 'hsl(var(--error))',
      neutral: 'hsl(var(--foreground))',
    }
    return { color: colors[props.color] }
  }

  // auto: 根据值判断颜色(ADR-045 §2 西式涨绿跌红)
  const n = typeof props.value === 'string' ? parseFloat(props.value) : props.value
  if (n === null || n === undefined || isNaN(n)) return {}

  if (n > 0) return { color: 'hsl(var(--success))' }
  if (n < 0) return { color: 'hsl(var(--error))' }
  return { color: 'hsl(var(--foreground))' }
})
</script>

<style scoped>
.stat-card {
  background: hsl(var(--card));
  border-radius: var(--radius-lg);
  border: 1px solid hsl(var(--border));
  padding: 20px;
  height: 100%;
}

.stat-card-clickable {
  cursor: pointer;
  transition: box-shadow 0.2s;
}

.stat-card-clickable:hover {
  box-shadow: 0 2px 8px hsl(var(--primary) / 0.2);
}

.stat-title {
  font-size: 13px;
  color: hsl(var(--muted-foreground));
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
  /* ADR-047:数值 mono + 等宽数字 */
  font-family: var(--font-mono);
  font-variant-numeric: tabular-nums;
}

.stat-suffix {
  font-size: 14px;
  color: hsl(var(--muted-foreground));
}
</style>
