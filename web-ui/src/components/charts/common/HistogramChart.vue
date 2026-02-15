<template>
  <div ref="chartRef" class="histogram-chart" :style="{ width: width, height: height }"></div>
</template>

<script setup lang="ts">
import { ref, onMounted, onUnmounted, watch } from 'vue'
import { createChart, type IChartApi, type HistogramData } from 'lightweight-charts'

interface Props {
  data: HistogramData[]
  width?: string
  height?: string
  color?: string
  title?: string
  priceFormat?: (price: number) => string
}

const props = withDefaults(defineProps<Props>(), {
  width: '100%',
  height: '200px',
  color: '#26a69a',
  title: 'Volume'
})

const chartRef = ref<HTMLDivElement>()
let chart: IChartApi | null = null
let histogramSeries: any = null

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
    priceScale: {
      scaleMargins: {
        top: 0.8,
        bottom: 0,
      },
    },
  })

  histogramSeries = chart.addHistogramSeries({
    color: props.color,
    title: props.title,
    priceFormat: props.priceFormat,
  })

  histogramSeries.setData(props.data)
}

const updateChart = () => {
  if (!histogramSeries) return
  histogramSeries.setData(props.data)
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
  getSeries: () => histogramSeries,
  update: (newData: HistogramData) => histogramSeries?.update(newData),
  resize: () => chart?.applyOptions({ width: chartRef.value?.clientWidth }),
})
</script>

<style scoped>
.histogram-chart {
  min-height: 150px;
}
</style>
