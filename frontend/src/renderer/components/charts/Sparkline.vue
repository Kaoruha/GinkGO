<template>
  <svg v-if="points.length >= 2" :width="width" :height="height" :viewBox="`0 0 ${width} ${height}`"
       preserveAspectRatio="none" class="sparkline">
    <path :d="pathD" fill="none" :stroke="color" stroke-width="1.5" />
    <line v-if="baseline !== null" x1="0" :x2="width" :y1="baseline" :y2="baseline"
          class="spark-baseline" stroke-dasharray="2,3" />
  </svg>
  <span v-else class="spark-empty">-</span>
</template>

<script setup lang="ts">
/**
 * 净值缩略图(纯 SVG,无图表库依赖):回测列表内联展示大致走势。
 * points = 净值序列(降采样 ~40 点);基线=首值(通常 1.0)供上下视觉锚点。
 */
import { computed } from 'vue'

const props = withDefaults(defineProps<{
  points: number[]
  width?: number
  height?: number
}>(), { width: 120, height: 32 })

const color = computed(() => {
  const last = props.points[props.points.length - 1] ?? 1
  return last >= (props.points[0] ?? 1)
    ? 'hsl(var(--success))'
    : 'hsl(var(--error))'
})

const pathD = computed(() => {
  const pts = props.points
  const min = Math.min(...pts), max = Math.max(...pts)
  const span = max - min || 1
  const pad = 2
  const h = props.height - pad * 2
  const step = props.width / (pts.length - 1)
  return pts
    .map((v, i) => `${i === 0 ? 'M' : 'L'}${(i * step).toFixed(1)},${(pad + h - ((v - min) / span) * h).toFixed(1)}`)
    .join(' ')
})

const baseline = computed(() => {
  const pts = props.points
  if (pts.length < 2) return null
  const min = Math.min(...pts), max = Math.max(...pts)
  const span = max - min || 1
  const pad = 2
  const h = props.height - pad * 2
  return pad + h - ((pts[0] - min) / span) * h
})
</script>

<style scoped>
.sparkline { display: block; }
.spark-baseline { stroke: hsl(var(--muted-foreground) / 0.35); stroke-width: 0.75; }
.spark-empty { color: hsl(var(--muted-foreground)); font-size: 12px; }
</style>
