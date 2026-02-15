<template>
  <div class="net-value-chart">
    <AreaChart
      ref="chartRef"
      :data="chartData"
      :height="height"
      :line-color="lineColor"
      :top-color="topColor"
      :bottom-color="bottomColor"
      title="净值"
    />
    <div v-if="benchmarkData.length > 0" class="benchmark-overlay">
      <LineChart
        :data="benchmarkData"
        :height="height"
        :line-width="1"
        color="#999"
        title="基准"
      />
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed } from 'vue'
import { AreaChart, LineChart } from '../common'
import type { AreaData } from 'lightweight-charts'

interface Props {
  netValueData: Array<{ time: number; value: number }>
  benchmarkData?: Array<{ time: number; value: number }>
  height?: string
}

const props = withDefaults(defineProps<Props>(), {
  benchmarkData: () => [],
  height: '400px'
})

const chartRef = ref()

const chartData = computed<AreaData[]>(() => {
  return props.netValueData.map((d, i) => ({
    time: d.time as any,
    value: d.value,
  }))
})

const lineColor = '#2196F3'
const topColor = 'rgba(33, 150, 243, 0.4)'
const bottomColor = 'rgba(33, 150, 243, 0.0)'

defineExpose({
  fitContent: () => chartRef.value?.getInstance()?.timeScale().fitContent(),
})
</script>

<style scoped>
.net-value-chart {
  position: relative;
}
</style>
