<template>
  <div ref="chartContainer" class="tv-chart-container"></div>
</template>

<script setup lang="ts">
import { ref, onMounted, onUnmounted, watch } from 'vue'
import {
  createChart,
  IChartApi,
  ISeriesApi,
  LineData,
  AreaData,
  ColorType,
} from 'lightweight-charts'

interface Props {
  data?: LineData[]
  benchmarkData?: LineData[]
  height?: number
  showBenchmark?: boolean
}

const props = withDefaults(defineProps<Props>(), {
  data: () => [],
  benchmarkData: () => [],
  height: 300,
  showBenchmark: true,
})

const chartContainer = ref<HTMLElement | null>(null)
let chart: IChartApi | null = null
let mainSeries: ISeriesApi<'Area'> | null = null
let benchmarkSeries: ISeriesApi<'Line'> | null = null

const initChart = () => {
  if (!chartContainer.value) return

  chart = createChart(chartContainer.value, {
    width: chartContainer.value.clientWidth,
    height: props.height,
    layout: {
      background: { type: ColorType.Solid, color: '#ffffff' },
      textColor: '#666',
    },
    grid: {
      vertLines: { color: '#f5f5f5' },
      horzLines: { color: '#f5f5f5' },
    },
    rightPriceScale: {
      borderColor: '#e8e8e8',
    },
    timeScale: {
      borderColor: '#e8e8e8',
      timeVisible: true,
    },
    handleScale: {
      axisPressedMouseMove: true,
    },
  })

  // 主策略净值曲线（面积图）
  if (props.data.length > 0) {
    mainSeries = chart.addAreaSeries({
      topColor: 'rgba(33, 150, 243, 0.4)',
      bottomColor: 'rgba(33, 150, 243, 0.0)',
      lineColor: '#2196F3',
      lineWidth: 2,
    })
    mainSeries.setData(props.data)
  }

  // 基准净值曲线
  if (props.showBenchmark && props.benchmarkData.length > 0) {
    benchmarkSeries = chart.addLineSeries({
      color: '#9E9E9E',
      lineWidth: 1,
      lineStyle: 2, // 虚线
    })
    benchmarkSeries.setData(props.benchmarkData)
  }

  chart.timeScale().fitContent()
}

const handleResize = () => {
  if (chart && chartContainer.value) {
    chart.applyOptions({ width: chartContainer.value.clientWidth })
  }
}

onMounted(() => {
  initChart()
  window.addEventListener('resize', handleResize)
})

onUnmounted(() => {
  window.removeEventListener('resize', handleResize)
  if (chart) {
    chart.remove()
    chart = null
  }
})

watch(() => props.data, (newData) => {
  if (mainSeries && newData.length > 0) {
    mainSeries.setData(newData)
  }
}, { deep: true })

watch(() => props.benchmarkData, (newData) => {
  if (benchmarkSeries && newData.length > 0) {
    benchmarkSeries.setData(newData)
  }
}, { deep: true })

defineExpose({
  chart,
  mainSeries,
  benchmarkSeries,
})
</script>

<style scoped>
.tv-chart-container {
  width: 100%;
  min-height: 250px;
}
</style>
