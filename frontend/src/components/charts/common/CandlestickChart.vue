<template>
  <div ref="chartRef" class="candlestick-chart" :style="{ width: width, height: height }"></div>
</template>

<script setup lang="ts">
import { ref, onMounted, onUnmounted, watch } from 'vue'
import { createChart, type IChartApi, type CandlestickData } from 'lightweight-charts'

interface Props {
  data: CandlestickData[]
  width?: string
  height?: string
  upColor?: string
  downColor?: string
  title?: string
}

const props = withDefaults(defineProps<Props>(), {
  width: '100%',
  height: '400px',
  upColor: '#26a69a',
  downColor: '#ef5350',
  title: ''
})

const chartRef = ref<HTMLDivElement>()
let chart: IChartApi | null = null
let candlestickSeries: any = null

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

  candlestickSeries = chart.addCandlestickSeries({
    upColor: props.upColor,
    downColor: props.downColor,
    borderVisible: false,
    wickUpColor: props.upColor,
    wickDownColor: props.downColor,
    title: props.title,
  })

  candlestickSeries.setData(props.data)
}

const updateChart = () => {
  if (!candlestickSeries) return
  candlestickSeries.setData(props.data)
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
  getSeries: () => candlestickSeries,
  update: (newData: CandlestickData) => candlestickSeries?.update(newData),
  resize: () => chart?.applyOptions({ width: chartRef.value?.clientWidth }),
})
</script>

<style scoped>
.candlestick-chart {
  min-height: 200px;
}
</style>
