<template>
  <AreaChart
    :data="chartData"
    :height="height"
    :line-color="lineColor"
    :top-color="topColor"
    :bottom-color="bottomColor"
    title="回撤"
  />
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { AreaChart } from '../common'
import type { AreaData } from 'lightweight-charts'

interface Props {
  drawdownData: Array<{ time: number; value: number }>
  height?: string
}

const props = withDefaults(defineProps<Props>(), {
  height: '200px'
})

const chartData = computed<AreaData[]>(() => {
  return props.drawdownData.map(d => ({
    time: d.time as any,
    value: d.value,
  }))
})

// 回撤图用红色系
const lineColor = '#ef5350'
const topColor = 'rgba(239, 83, 80, 0.4)'
const bottomColor = 'rgba(239, 83, 80, 0.0)'
</script>
