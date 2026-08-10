<template>
  <div ref="chartRef" class="histogram-chart" :style="{ width: width, height: height }"></div>
</template>

<script setup lang="ts">
import { ref, onMounted, onUnmounted, watch } from 'vue'
import { createChart, type IChartApi, type HistogramData } from 'lightweight-charts'
import { useChartTheme, cssColor } from '@/composables/useChartTheme'

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
  color: '',
  title: 'Volume'
})

const { theme } = useChartTheme()
const chartRef = ref<HTMLDivElement>()
let chart: IChartApi | null = null
let histogramSeries: any = null

// 颜色解析:prop 优先,缺省回退 token(ADR-045 中性半透明)。
const resolveColor = () => props.color || cssColor('--muted-foreground', 0.5)

const initChart = () => {
  if (!chartRef.value) return

  chart = createChart(chartRef.value, {
    width: chartRef.value.clientWidth,
    height: parseInt(props.height),
    layout: {
      background: { color: cssColor('--card') },
      textColor: cssColor('--muted-foreground'),
    },
    grid: {
      vertLines: { color: cssColor('--border') },
      horzLines: { color: cssColor('--border') },
    },
    timeScale: {
      timeVisible: true,
      secondsVisible: false,
    },
  } as any)

  histogramSeries = chart.addHistogramSeries({
    color: resolveColor(),
    title: props.title,
    priceFormat: props.priceFormat as any,
  })

  histogramSeries.setData(props.data)
}

// 主题切换重绘:canvas 不认 CSS var,须重读 token 调 applyOptions(ADR-045)。
const applyChartTheme = () => {
  if (!chart) return
  chart.applyOptions({
    layout: {
      background: { color: cssColor('--card') },
      textColor: cssColor('--muted-foreground'),
    },
    grid: {
      vertLines: { color: cssColor('--border') },
      horzLines: { color: cssColor('--border') },
    },
  })
  histogramSeries?.applyOptions({ color: resolveColor() })
}
watch(theme, applyChartTheme)

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
