<template>
  <div ref="chartContainer" class="tv-chart-container"></div>
</template>

<script setup lang="ts">
import { ref, onMounted, onUnmounted, watch } from 'vue'
import {
  createChart,
  IChartApi,
  ISeriesApi,
  CandlestickData,
  LineData,
  HistogramData,
  ColorType,
  CrosshairMode,
} from 'lightweight-charts'

interface Props {
  data?: CandlestickData[]
  lineData?: LineData[]
  volumeData?: HistogramData[]
  height?: number
  showVolume?: boolean
}

const props = withDefaults(defineProps<Props>(), {
  data: () => [],
  lineData: () => [],
  volumeData: () => [],
  height: 400,
  showVolume: true,
})

const chartContainer = ref<HTMLElement | null>(null)
let chart: IChartApi | null = null
let candlestickSeries: ISeriesApi<'Candlestick'> | null = null
let lineSeries: ISeriesApi<'Line'> | null = null
let volumeSeries: ISeriesApi<'Histogram'> | null = null

const initChart = () => {
  if (!chartContainer.value) return

  chart = createChart(chartContainer.value, {
    width: chartContainer.value.clientWidth,
    height: props.height,
    layout: {
      background: { type: ColorType.Solid, color: '#ffffff' },
      textColor: '#333',
    },
    grid: {
      vertLines: { color: '#f0f0f0' },
      horzLines: { color: '#f0f0f0' },
    },
    crosshair: {
      mode: CrosshairMode.Normal,
    },
    rightPriceScale: {
      borderColor: '#cccccc',
    },
    timeScale: {
      borderColor: '#cccccc',
      timeVisible: true,
      secondsVisible: false,
    },
  })

  // 添加 K 线图
  if (props.data.length > 0) {
    candlestickSeries = chart.addCandlestickSeries({
      upColor: '#ef5350',
      downColor: '#26a69a',
      borderDownColor: '#26a69a',
      borderUpColor: '#ef5350',
      wickDownColor: '#26a69a',
      wickUpColor: '#ef5350',
    })
    candlestickSeries.setData(props.data)
  }

  // 添加折线图
  if (props.lineData.length > 0) {
    lineSeries = chart.addLineSeries({
      color: '#2962FF',
      lineWidth: 2,
    })
    lineSeries.setData(props.lineData)
  }

  // 添加成交量
  if (props.showVolume && props.volumeData.length > 0) {
    volumeSeries = chart.addHistogramSeries({
      color: '#26a69a',
      priceFormat: {
        type: 'volume',
      },
      priceScaleId: '',
    })
    volumeSeries.priceScale().applyOptions({
      scaleMargins: {
        top: 0.8,
        bottom: 0,
      },
    })
    volumeSeries.setData(props.volumeData)
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
  if (candlestickSeries && newData.length > 0) {
    candlestickSeries.setData(newData)
  }
}, { deep: true })

watch(() => props.lineData, (newData) => {
  if (lineSeries && newData.length > 0) {
    lineSeries.setData(newData)
  }
}, { deep: true })

watch(() => props.volumeData, (newData) => {
  if (volumeSeries && newData.length > 0) {
    volumeSeries.setData(newData)
  }
}, { deep: true })

// 暴露方法
defineExpose({
  chart,
  candlestickSeries,
  lineSeries,
  volumeSeries,
})
</script>

<style scoped>
.tv-chart-container {
  width: 100%;
  min-height: 300px;
}
</style>
