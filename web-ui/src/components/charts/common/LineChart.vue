<template>
  <div ref="chartRef" class="line-chart" :style="{ width: width, height: height }"></div>
</template>

<script setup lang="ts">
import { ref, onMounted, onUnmounted, watch, type PropType } from 'vue'
import { createChart, type IChartApi, type LineData, type Time } from 'lightweight-charts'

interface Props {
  data: LineData[]
  width?: string
  height?: string
  color?: string
  lineWidth?: number
  title?: string
}

const props = withDefaults(defineProps<Props>(), {
  width: '100%',
  height: '400px',
  color: '#2196F3',
  lineWidth: 2,
  title: ''
})

const chartRef = ref<HTMLDivElement>()
let chart: IChartApi | null = null
let lineSeries: any = null

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
    timeScale: {
      timeVisible: true,
      secondsVisible: false,
    },
  })

  lineSeries = chart.addLineSeries({
    color: props.color,
    lineWidth: props.lineWidth,
    title: props.title,
  })

  lineSeries.setData(props.data)
}

const updateChart = () => {
  if (!lineSeries) return
  lineSeries.setData(props.data)
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
  getSeries: () => lineSeries,
  update: (newData: LineData) => lineSeries?.update(newData),
  resize: () => chart?.applyOptions({ width: chartRef.value?.clientWidth }),
})
</script>

<style scoped>
.line-chart {
  min-height: 200px;
}
</style>
