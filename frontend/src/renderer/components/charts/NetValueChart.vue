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
  ColorType,
} from 'lightweight-charts'
import { useChartTheme, cssColor } from '@/composables/useChartTheme'

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

const { theme } = useChartTheme()
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
      background: { type: ColorType.Solid, color: cssColor('--card') },
      textColor: cssColor('--muted-foreground'),
    },
    grid: {
      vertLines: { color: cssColor('--border') },
      horzLines: { color: cssColor('--border') },
    },
    rightPriceScale: {
      borderColor: cssColor('--border'),
    },
    timeScale: {
      borderColor: cssColor('--border'),
      timeVisible: true,
    },
    handleScale: {
      axisPressedMouseMove: true,
    },
  })

  // 主策略净值曲线（面积图）
  if (props.data.length > 0) {
    mainSeries = chart.addAreaSeries({
      topColor: cssColor('--primary', 0.4),
      bottomColor: cssColor('--primary', 0.0),
      lineColor: cssColor('--primary'),
      lineWidth: 2,
    })
    // 去重并排序数据（lightweight-charts 要求时间升序且无重复）
    const uniqueData = [...new Map(props.data.map((item: any) => [item.time, item])).values()]
      .sort((a: any, b: any) => (a.time > b.time ? 1 : -1))
    try {
      mainSeries.setData(uniqueData)
    } catch (e) {
      console.warn('NetValueChart: failed to set main data', e)
    }
  }

  // 基准净值曲线
  if (props.showBenchmark && props.benchmarkData.length > 0) {
    benchmarkSeries = chart.addLineSeries({
      color: cssColor('--muted-foreground'),
      lineWidth: 1,
      lineStyle: 2, // 虚线
    })
    // 去重并排序数据
    const uniqueBenchmark = [...new Map(props.benchmarkData.map((item: any) => [item.time, item])).values()]
      .sort((a: any, b: any) => (a.time > b.time ? 1 : -1))
    try {
      benchmarkSeries.setData(uniqueBenchmark)
    } catch (e) {
      console.warn('NetValueChart: failed to set benchmark data', e)
    }
  }

  chart.timeScale().fitContent()
}

// 主题切换重绘:canvas 不认 CSS var,须重读 token 调 applyOptions(ADR-045)。
const applyChartTheme = () => {
  if (!chart) return
  chart.applyOptions({
    layout: {
      background: { type: ColorType.Solid, color: cssColor('--card') },
      textColor: cssColor('--muted-foreground'),
    },
    grid: {
      vertLines: { color: cssColor('--border') },
      horzLines: { color: cssColor('--border') },
    },
    rightPriceScale: { borderColor: cssColor('--border') },
    timeScale: { borderColor: cssColor('--border') },
  })
  mainSeries?.applyOptions({
    topColor: cssColor('--primary', 0.4),
    bottomColor: cssColor('--primary', 0.0),
    lineColor: cssColor('--primary'),
  })
  benchmarkSeries?.applyOptions({ color: cssColor('--muted-foreground') })
}
watch(theme, applyChartTheme)

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
    const uniqueData = [...new Map(newData.map((item: any) => [item.time, item])).values()]
      .sort((a: any, b: any) => (a.time > b.time ? 1 : -1))
    try { mainSeries.setData(uniqueData) } catch { /* ignore format errors */ }
  }
}, { deep: true })

watch(() => props.benchmarkData, (newData) => {
  if (benchmarkSeries && newData.length > 0) {
    const uniqueData = [...new Map(newData.map((item: any) => [item.time, item])).values()]
      .sort((a: any, b: any) => (a.time > b.time ? 1 : -1))
    try { benchmarkSeries.setData(uniqueData) } catch { /* ignore format errors */ }
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
