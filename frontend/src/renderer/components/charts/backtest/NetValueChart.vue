<template>
  <div class="net-value-chart">
    <AreaChart
      ref="chartRef"
      :data="chartData"
      :height="height"
      title="净值"
    />
    <div v-if="benchmarkData.length > 0" class="benchmark-overlay">
      <LineChart
        :data="benchmarkChartData"
        :height="height"
        :line-width="1"
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

const chartData = computed(() => {
  return props.netValueData.map((d) => ({
    time: d.time as any,
    value: d.value,
  })) as AreaData[]
})

const benchmarkChartData = computed(() => {
  return (props.benchmarkData || []).map((d) => ({
    time: d.time as any,
    value: d.value,
  })) as any[]
})

defineExpose({
  fitContent: () => chartRef.value?.getInstance()?.timeScale().fitContent(),
})
</script>

<style scoped>
.net-value-chart {
  position: relative;
}
</style>
