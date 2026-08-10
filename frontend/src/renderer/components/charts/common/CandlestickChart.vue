<template>
  <div ref="chartRef" class="candlestick-chart" :style="{ width: width, height: height }"></div>
</template>

<script setup lang="ts">
import { ref, onMounted, onUnmounted, watch } from 'vue'
import { createChart, type IChartApi, type CandlestickData } from 'lightweight-charts'
import { useChartTheme, cssColor, upColor as upClr, downColor as downClr } from '@/composables/useChartTheme'

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
  upColor: '',
  downColor: '',
  title: ''
})

const { theme } = useChartTheme()
const chartRef = ref<HTMLDivElement>()
let chart: IChartApi | null = null
let candlestickSeries: any = null

// 涨跌色:prop 优先,缺省回退 token(ADR-045 西方语义 绿涨红跌)。
const resolveUp = () => props.upColor || upClr()
const resolveDown = () => props.downColor || downClr()

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
  })

  const up = resolveUp(), down = resolveDown()
  candlestickSeries = chart.addCandlestickSeries({
    upColor: up, downColor: down,
    borderVisible: false,
    wickUpColor: up, wickDownColor: down,
    title: props.title,
  })

  candlestickSeries.setData(props.data)
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
  const up = resolveUp(), down = resolveDown()
  candlestickSeries?.applyOptions({
    upColor: up, downColor: down,
    wickUpColor: up, wickDownColor: down,
  })
}
watch(theme, applyChartTheme)

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
