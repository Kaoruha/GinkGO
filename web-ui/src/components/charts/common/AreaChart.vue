<template>
  <div ref="chartRef" class="area-chart" :style="{ width: width, height: height }"></div>
</template>

<script setup lang="ts">
import { ref, onMounted, onUnmounted, watch } from 'vue'
import { createChart, type IChartApi, type AreaData } from 'lightweight-charts'

interface Props {
  data: AreaData[]
  width?: string
  height?: string
  lineColor?: string
  topColor?: string
  bottomColor?: string
  title?: string
}

const props = withDefaults(defineProps<Props>(), {
  width: '100%',
  height: '400px',
  lineColor: '#2196F3',
  topColor: 'rgba(33, 150, 243, 0.4)',
  bottomColor: 'rgba(33, 150, 243, 0.0)',
  title: ''
})

const chartRef = ref<HTMLDivElement>()
let chart: IChartApi | null = null
let areaSeries: any = null

const initChart = () => {
  if (!chartRef.value) return

  chart = createChart(chartRef.value, {
    width: chartRef.value.clientWidth,
    height: parseInt(props.height),
    layout: {
      background: { color: '#ffffff' },
      textColor: '#333',
    },
    grid: {
      vertLines: { color: '#e1e1e1' },
      horzLines: { color: '#e1e1e1' },
    },
  })

  areaSeries = chart.addAreaSeries({
    lineColor: props.lineColor,
    topColor: props.topColor,
    bottomColor: props.bottomColor,
    title: props.title,
  })

  areaSeries.setData(props.data)
}

const updateChart = () => {
  if (!areaSeries) return
  areaSeries.setData(props.data)
}

onMounted(() => {
  initChart()
})

onUnmounted(() => {
  if (chart) {
    chart.remove()
    chart = null
  }
})

watch(() => props.data, updateChart, { deep: true })

defineExpose({
  getInstance: () => chart,
  getSeries: () => areaSeries,
  update: (newData: AreaData) => areaSeries?.update(newData),
  resize: () => chart?.applyOptions({ width: chartRef.value?.clientWidth }),
})
</script>

<style scoped>
.area-chart {
  min-height: 200px;
}
</style>
