<template>
  <div class="pnl-chart">
    <HistogramChart
      ref="chartRef"
      :data="chartData"
      :height="height"
      :color="color"
      title="收益分布"
    />
    <div class="pnl-stats">
      <div class="stat-item">
        <span class="label">均值:</span>
        <span class="value">{{ meanPnl }}</span>
      </div>
      <div class="stat-item">
        <span class="label">标准差:</span>
        <span class="value">{{ stdPnl }}</span>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed } from 'vue'
import { HistogramChart } from '../common'
import type { HistogramData } from 'lightweight-charts'

interface Props {
  returnData: number[]
  height?: string
}

const props = withDefaults(defineProps<Props>(), {
  height: '250px'
})

const chartRef = ref()

const chartData = computed<HistogramData[]>(() => {
  // 简化的直方图数据转换
  const returns = props.returnData
  if (returns.length === 0) return []

  // 计算分箱
  const min = Math.min(...returns)
  const max = Math.max(...returns)
  const binCount = 20
  const binSize = (max - min) / binCount

  const bins = Array.from({ length: binCount }, (_, i) => {
    const binMin = min + i * binSize
    const binMax = binMin + binSize
    const count = returns.filter(r => r >= binMin && r < binMax).length
    return {
      time: binMin as any,
      value: count,
      color: count > 0 ? (count > returns.length / binCount ? '#ef5350' : '#26a69a') : '#ccc'
    }
  })

  return bins.filter(b => b.value > 0)
})

const meanPnl = computed(() => {
  const returns = props.returnData
  if (returns.length === 0) return 'N/A'
  const mean = returns.reduce((a, b) => a + b, 0) / returns.length
  return (mean * 100).toFixed(2) + '%'
})

const stdPnl = computed(() => {
  const returns = props.returnData
  if (returns.length === 0) return 'N/A'
  const mean = returns.reduce((a, b) => a + b, 0) / returns.length
  const variance = returns.reduce((a, b) => a + Math.pow(b - mean, 2), 0) / returns.length
  return (Math.sqrt(variance) * 100).toFixed(2) + '%'
})

const color = '#26a69a'
</script>

<style scoped>
.pnl-chart {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.pnl-stats {
  display: flex;
  gap: 24px;
}

.stat-item {
  display: flex;
  gap: 8px;
}

.label {
  color: #666;
  font-size: 14px;
}

.value {
  font-weight: 600;
  color: #333;
}
</style>
