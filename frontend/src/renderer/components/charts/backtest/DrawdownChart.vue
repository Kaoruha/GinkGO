<template>
  <AreaChart
    :data="chartData"
    :height="height"
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
</script>
